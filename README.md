# Translator Helper

A Streamlit-powered assistant for transcribing, translating, and grading Japanese Drama CDs.

[![Watch the demo](https://img.youtube.com/vi/Zi3OjbpptQk/maxresdefault.jpg)](https://youtu.be/Zi3OjbpptQk?si=Pb9BCGCWDZM_1RJU)

## Features

- **Transcribe Audio**  
  Upload `.wav` or `.mp3` files or record from microphone using OpenAI Whisper.

- **Import Subtitle Files**  
  Analyze `.srt` or `.ass` files to extract scene structure, characters, tone, and synopsis.

- **Web Context Search**  
  Enrich translations using background information retrieved via Tavily + LangChain.

- **Context-Aware Translation**  
  Translate Japanese text into natural and literal English, with optional annotated form.

- **Grading and Evaluation**  
  Evaluate translation quality based on accuracy, fluency, and cultural appropriateness.

## Tech Stack

- Python 3.10+
- [Streamlit](https://streamlit.io/) for UI
- [LangChain](https://www.langchain.com/) for prompt orchestration
- [OpenAI GPT (Chat Models)](https://platform.openai.com/docs)
- [Whisper](https://github.com/openai/whisper) for audio transcription
- [Tavily](https://app.tavily.com/) for web search context
- `pysubs2` for subtitle file parsing

## Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/dragonstonehafiz/translator-helper.git
cd translator-helper
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up API Keys
Create a `config.json` file in the root directory (or use the Configuration tab in the UI):

```json
{
  "input_lang": "ja",
  "output_lang": "en",
  "whisper_model": "medium",
  "openai_model": "gpt-4o",
  "openai_api_key": "YOUR_OPENAI_KEY",
  "tavily_api_key": "YOUR_TAVILY_KEY",
  "temperature": 0.7
}
```

### 4. Run the App
```bash
streamlit run app.py
```

## Project Structure

```plaintext
translator-helper/
├── app.py
├── config.json
├── requirements.txt
├── src/
│   ├── logic/
│   │   ├── config.py
│   │   ├── context.py
│   │   ├── grade.py
│   │   ├── load_models.py
│   │   ├── transcribe.py
│   │   ├── translate.py
│   │   └── validate_api_keys.py
│   │
│   ├── ui/
│   │   ├── config.py
│   │   ├── context.py
│   │   ├── grade.py
│   │   ├── init.py
│   │   ├── load_models.py
│   │   ├── shared.py
│   │   ├── transcribe.py
│   │   └── translate.py
│   │
```