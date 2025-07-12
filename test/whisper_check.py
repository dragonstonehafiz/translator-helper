# smoke_test_whisper.py
from pathlib import Path
import torch
import whisper

device   = "cuda" if torch.cuda.is_available() else "cpu"
model    = whisper.load_model("base", device=device)

wav_path = Path("sample/sample_audio_en_1.wav")
result   = model.transcribe(str(wav_path), language="en")

print(result["text"][:120])