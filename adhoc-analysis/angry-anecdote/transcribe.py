import whisper
import os

DIR = os.path.dirname(os.path.abspath(__file__))

FILES = [
    ("irfan_contractor.opus", "Irfan (Contractor)"),
    ("merchant_feedback.opus", "Merchant"),
]

model = whisper.load_model("medium")

for filename, label in FILES:
    path = os.path.join(DIR, filename)
    print(f"\n{'='*60}")
    print(f"Transcribing: {label} ({filename})")
    print("="*60)
    result = model.transcribe(path)
    text = result["text"].strip()
    lang = result.get("language", "unknown")
    print(f"Detected language: {lang}")
    print(f"\n{text}\n")
    out_path = path.replace(".opus", ".txt")
    with open(out_path, "w") as f:
        f.write(f"Speaker: {label}\n")
        f.write(f"Language: {lang}\n")
        f.write(f"File: {filename}\n")
        f.write("="*60 + "\n\n")
        f.write(text)
    print(f"Saved → {os.path.basename(out_path)}")
