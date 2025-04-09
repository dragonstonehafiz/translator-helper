# Translator Helper

**Translator Helper** is a Streamlit-based application designed to assist in the transcription and translation of Japanese Drama CDs. It uses OpenAI's GPT models for translation and grading, and Whisper for speech-to-text transcription.

## Features

### 1. Transcription
- Upload `.mp3` or `.wav` audio files.
- Transcribe audio using OpenAI Whisper.
- Selectable Whisper model and input language.
- Optional GPU acceleration (CUDA).

### 2. Translation
- Translate Japanese text into English (or other languages).
- Uses GPT models (`gpt-4`, `gpt-4o`, `gpt-4o-mini`) for rich, multi-perspective translations:
  - Naturalized translation
  - Literal translation
  - Annotated translation
- **Context-aware translation**:
  - Integrates character relationships, scene background, and tone to guide output.

### 3. Grading
- Evaluates translations based on:
  - **Accuracy**
  - **Fluency**
  - **Cultural Appropriateness**
- Provides an average score and detailed suggestions for improvement.
- Uses the same context input as translation for consistency.

### 4. Context
- Upload `.srt` or `.ass` subtitle files.
- Automatically extract contextual details:
  - Scene summary (events and dialogue content)
  - Characters and relationships
  - Speech level and tone
- Fields are auto-filled and remain editable before use in translation or grading.

### 5. Configuration
- Manage and save API keys and model preferences.
- Set translation temperature and top-p.
- Save/load configuration from `config.json`.

## Setup

### Prerequisites

- Python 3.8+
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### Whisper (Optional: GPU Support)

Ensure you have enough VRAM for the selected Whisper model. CUDA can be enabled in settings if supported.

## Usage

```bash
streamlit run TranslatorHelper.py
```

## Notes

- The app assumes familiarity with Japanese language and Drama CD content.
- GPT models provide support and interpretation; human judgment is still key.