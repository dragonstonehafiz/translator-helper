# Translator Helper

A Streamlit-powered assistant for transcribing, translating, and grading Japanese Drama CDs.

## Features

| Page | Tab / Section | Purpose |
|------|---------------|---------|
| **Settings** | — (single tab) | Adjust input/output language codes, pick the Whisper size + device from `get_device_map`, choose the OpenAI chat model, supply OpenAI/Tavily API keys, set temperature, and persist the configuration to `config.json`. |
| **Translate** | **Context Inputs** | Author or paste Web Context, Character List, and High Level Summary in expandable editors, toggling each block on/off to control what gets injected into translations. |
| | **Translate Line** | Submit ad-hoc source text to `translate_multi_response`, which uses the active context payload plus the session’s language pair for GPT translations. |
| | **Translate File** | Upload `.ass`/`.srt`, review line/character stats and a preview, pick a context window, and run `translate_subs`; translated `.ass` files are saved under `output/` for download. |
| **Transcribe** | **Transcribe Soundbite** | Record audio in-browser, visualize the waveform, and send the clip through `transcribe_line` with the loaded Whisper model. |
| | **Transcribe File** | Upload longer audio, preview the waveform, and run `transcribe_file` to generate subtitle events; name the output and download the `.ass` produced in `output/`. |
| **Context** | **Generate from Subtitle** | Provide series metadata, upload `.ass`/`.srt`, and run automated helpers (Tavily web search, character list extraction, synopsis generation) in dependency order. |
| | **Load / Save Context** | Save the current context bundle to `/context/*.json` or reload an existing snapshot to rehydrate the UI fields. |
| | **Context Editors** | Persistent Web Context, Character List, and High Level Summary text areas for manual editing on any page visit. |


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
