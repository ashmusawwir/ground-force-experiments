"""Batch transcribe voice recordings using OpenAI Whisper (medium model).

Scans all subdirectories of University survey Voice Recordings/ for .m4a and .aac files.
Skips any audio file that already has a .txt sidecar (preserves existing transcripts).
Writes .txt sidecar next to each audio file.

After transcription, stitches each recording to its form submission row from survey_responses.csv
by matching the recording filename → Interviewee First Name column.

Outputs transcripts.md organized by university (subfolder name), with form metadata headers.
"""

import csv
import os
import re
import glob
import whisper

BASE_DIR = os.path.dirname(__file__)
RECORDINGS_DIR = os.path.join(BASE_DIR, "University survey Voice Recordings")
SURVEY_CSV = os.path.join(BASE_DIR, "survey_responses.csv")
COMBINED_OUTPUT = os.path.join(BASE_DIR, "transcripts.md")

# Maps subfolder name → list of aliases that match "University / Campus" column values
UNIVERSITY_MAP = {
    "Habib": ["Habib University", "HU"],
    "Ilma University": ["Ilma University"],
    "SSUIT": ["Sir Syed University of Engineering and Technology", "Sir Syed University", "SSUIT"],
    "IBA": ["IBA Karachi", "IBA"],
    "KU": ["Karachi University", "KU", "Quaid e Azam University"],
    "Szabist": ["SZABIST", "Szabist"],
}


# ---------------------------------------------------------------------------
# Form stitch helpers
# ---------------------------------------------------------------------------

def load_form_data():
    with open(SURVEY_CSV, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _norm(s):
    """Lowercase letters only — used for fuzzy name matching."""
    return re.sub(r"[^a-z]", "", s.lower())


def match_form_row(recording_name, form_rows, university_hint=None):
    """Match a recording filename stem to the best form row, or None.

    university_hint: subfolder name (e.g. "Habib", "SSUIT"). If provided and
    present in UNIVERSITY_MAP, narrows the search to rows from that university
    before falling back to the full list.
    """
    def _find_best(candidate_rows):
        rec_norm = _norm(recording_name)
        tokens = recording_name.split()
        rec_first = _norm(tokens[0]) if tokens else rec_norm

        best = None
        for row in candidate_rows:
            first_name = row.get("Interviewee First Name", "").strip()
            fn_norm = _norm(first_name)
            fn_tokens = first_name.split()
            fn_first = _norm(fn_tokens[0]) if fn_tokens else fn_norm

            # Exact full match
            if rec_norm == fn_norm:
                return row
            # Normalized recording starts with normalized form name (handles "AhmedHassaan" vs "Ahmed")
            if fn_norm and rec_norm.startswith(fn_norm):
                best = row; continue
            # First-word exact match
            if rec_first and fn_first and rec_first == fn_first:
                if best is None:
                    best = row; continue
            # 4-char prefix match (catches "fizza" vs "fiza", "michael" vs "mickyle")
            if len(rec_first) >= 4 and len(fn_first) >= 4 and rec_first[:4] == fn_first[:4]:
                if best is None:
                    best = row
        return best

    # University-filtered search first
    if university_hint and university_hint in UNIVERSITY_MAP:
        aliases = UNIVERSITY_MAP[university_hint]
        filtered = [r for r in form_rows if r.get("University / Campus", "").strip() in aliases]
        if filtered:
            result = _find_best(filtered)
            if result is not None:
                return result

    # Fallback to full list
    return _find_best(form_rows)


def form_metadata_line(row):
    """Format compact one-line form metadata from a CSV row."""
    fields = [
        ("University", row.get("University / Campus", "").strip()),
        ("Interest",   row.get("Interest Level", "").strip()),
        ("Gender",     row.get("Gender", "").strip()),
        ("Major",      row.get("Major / Program", "").strip()),
        ("Comfort",    row.get("Comfort with Shop Visits", "").strip()),
        ("Follow-up",  row.get("Follow-up Likelihood", "").strip()),
    ]
    parts = [f"{k}={v}" for k, v in fields if v]
    return "**Form:** " + ", ".join(parts) if parts else "**Form:** (no data)"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    model = whisper.load_model("medium")
    form_rows = load_form_data()

    # Collect all audio files grouped by university subfolder
    universities = {}
    for root, dirs, files in os.walk(RECORDINGS_DIR):
        dirs.sort()
        audio_files = sorted(
            f for f in files
            if not f.startswith(".")
            and (f.lower().endswith((".m4a", ".aac", ".mp4", ".mp3"))
                 or os.path.splitext(f)[1] == "")
        )
        if not audio_files:
            continue
        university = os.path.relpath(root, RECORDINGS_DIR)
        universities[university] = (root, audio_files)

    total = sum(len(files) for _, (_, files) in universities.items())
    print(f"Found {total} recordings across {len(universities)} universities.")

    all_transcripts = {}  # university -> list of (name, text, form_row_or_None)

    global_i = 0
    for university in sorted(universities):
        root, audio_files = universities[university]
        all_transcripts[university] = []

        for filename in audio_files:
            global_i += 1
            path = os.path.join(root, filename)
            name = os.path.splitext(filename)[0].strip()
            txt_path = os.path.splitext(path)[0] + ".txt"

            if os.path.exists(txt_path):
                print(f"[{global_i}/{total}] Skipping (already transcribed): {university}/{name}")
                with open(txt_path, encoding="utf-8") as f:
                    text = f.read().strip()
            else:
                print(f"[{global_i}/{total}] Transcribing: {university}/{name}...")
                result = model.transcribe(path, language="en")
                text = result["text"].strip()
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"  Done. Length: {len(text)} chars")

            row = match_form_row(name, form_rows, university_hint=university)
            all_transcripts[university].append((name, text, row))

    # Write combined markdown organized by university, with form stitch
    total_written = sum(len(v) for v in all_transcripts.values())
    matched = sum(1 for entries in all_transcripts.values() for _, _, r in entries if r)

    with open(COMBINED_OUTPUT, "w", encoding="utf-8") as f:
        f.write("# EXP-012 Voice Recording Transcripts\n\n")
        f.write(
            f"Transcribed {total_written} recordings using Whisper `medium` model "
            f"(language=en for Roman Urdu + English output). "
            f"Form match: {matched}/{total_written}.\n\n"
        )
        f.write("---\n\n")
        for university in sorted(all_transcripts):
            entries = all_transcripts[university]
            f.write(f"# {university}\n\n")
            for name, text, row in entries:
                f.write(f"## {name}\n\n")
                if row:
                    f.write(form_metadata_line(row) + "\n\n")
                else:
                    f.write("**Form:** not found\n\n")
                f.write(f"{text}\n\n---\n\n")

    print(f"\nAll done. {total_written} transcripts, {matched} matched to form rows.")
    print(f"Saved to: {COMBINED_OUTPUT}")


if __name__ == "__main__":
    main()
