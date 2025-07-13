# Translator Helper

A Streamlit-powered assistant for transcribing, translating, and grading Japanese Drama CDs.

[![Watch the demo](https://img.youtube.com/vi/Zi3OjbpptQk/maxresdefault.jpg)](https://youtu.be/Zi3OjbpptQk?si=Pb9BCGCWDZM_1RJU)

## Features

| Page | Tab | Purpose |
|------|-----|---------|
| **Settings** | — (single tab) | Select Whisper and GPT models, pick GPU/CPU, enter & validate API keys, set temperature, and choose input/output language. |
| **Automation** | **Context Gathering** | Perform a web search, extract the character list, and write a scene synopsis. |
| | **File Transcribe** | Run Whisper on an entire audio file and export a `.ass` subtitle file. |
| | **File Translation** | Upload a `.ass` file, and sequentially translate it line by line. |
| **Assistant** | **Line Transcribe** | Transcribe a single audio clip. |
| | **Line Translate** | Input a single line for translation. |
| | **Line Grade** | Score your translation for Accuracy, Fluency, and Cultural Fit, with brief comments. |


## Dependencies

- Python 3.10+
- [Streamlit](https://streamlit.io/) for UI
- [LangChain](https://www.langchain.com/) for prompt orchestration
- [PyTorch](https://pytorch.org/get-started/locally/). I used CUDA 11.8 and have not tested other CUDA versions.
- [OpenAI API (Chat Models)](https://platform.openai.com/docs)
- [Whisper](https://github.com/openai/whisper) for audio transcription
- [Tavily](https://app.tavily.com/) for web search context
- `pysubs2` for subtitle file parsing and generation

## Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/dragonstonehafiz/translator-helper.git
cd translator-helper
```

### 2. Installing PyTorch (For Hardware Acceleration)

If you are going to use hardware acceleration for transcribing, you will need to install PyTorch with CUDA [here](https://pytorch.org/get-started/locally/). The line provided below is the one I used.

```bash
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 3. Installing Other Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up API Keys
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
├── requirements.txt
├── src/
│   ├── logic/
│   │   ├── config.py
│   │   ├── context.py
│   │   ├── grade.py
│   │   ├── load_models.py
│   │   ├── transcribe.py
│   │   ├── translate.py
│   │   ├── utils.py
│   │   └── validate_api_keys.py
│   └── ui/
│       ├── config_ui.py
│       ├── context_ui.py
│       ├── grade_ui.py
│       ├── init_ui.py
│       ├── load_models_ui.py
│       ├── shared_ui.py
│       ├── transcribe_ui.py
│       └── translate_ui.py
└── README.md
```