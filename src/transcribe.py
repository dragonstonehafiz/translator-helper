import whisper
import os

def transcribe(model: whisper.model.Whisper, filepath: str, language: str):
    """
    Args:
        model (whisper.model.Whisper): generated using whisper.load_model()
        filepath (str): relative path to file
        language (str): language code (e.g. Japanese = ja, English = en)
    """
    fileExists = os.path.isfile(filepath)
    if fileExists:
        result = model.transcribe(filepath, language=language)
        return result['text']
    else:
        return "File not detected. Did you put the right path?"
        