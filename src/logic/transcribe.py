import whisper
import os
import pysubs2

def transcribe_line(model: whisper.model.Whisper, filepath: str, language: str) -> str:
    """
    Transcribes a single line of text.
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


def transcribe_file(model: whisper.model.Whisper, filepath: str, language: str) -> pysubs2.SSAFile:
    """
    Transcribes an audio file and creates a .ass file from it. 
    Args:
        model (whisper.model.Whisper): generated using whisper.load_model()
        filepath (str): relative path to file
        language (str): language code (e.g. Japanese = ja, English = en)
    """
    
    fileExists = os.path.isfile(filepath)
    if fileExists:
        # Transcribe the audio file
        result = model.transcribe(filepath, language=language)
        # Get the segments from the transcription result
        segments = result["segments"]
        
        # Go through each segment and add it to a newly generated ass file
        subs = pysubs2.SSAFile()
        for seg in segments:
            line = pysubs2.SSAEvent(
                start=seg["start"] * 1000,
                end=seg["end"] * 1000,
                text=seg["text"]
            )
            subs.events.append(line)
        return subs
    else:
        return "File not detected. Did you put the right path?"