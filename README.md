# Translator Helper

A full-stack web application for transcribing, translating, and managing subtitle files. Built with Angular 17 (frontend) and FastAPI (backend), featuring Whisper transcription and OpenAI translation.

## Features

### Settings Page
- **Status**: Monitor API readiness (OpenAI, Whisper)
- **Whisper Settings**: Select Whisper model size and compute device (CPU/CUDA), load model into memory
- **OpenAI Settings**: Configure OpenAI model, set temperature, input API key

### Context Page
- **File Download/Upload**: Import/export context as JSON files, upload subtitle files for processing
- **Character List**: Auto-generate character names and descriptions from subtitle files
- **Synopsis**: Generate episode or scene synopsis (optional: include character list)
- **Summary**: Generate high-level summary (optional: include character list)
- **Recap**: Generate comprehensive recap from multiple context JSON files for multi-episode continuity

### Transcribe Page
- **Transcribe Line**: Record audio from microphone with waveform visualization, transcribe to text using Whisper

### Translate Page
- **Context**: View and edit saved context (character list, synopsis, summary, recap)
- **Translate Line**: Translate single lines with selectable context sources (character list, synopsis, summary)
- **Translate File**: Upload subtitle files (.ass/.srt) with batch size support; translated files are saved in `backend/outputs/sub-files/` for download


## Dependencies

### Backend
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for fast Python package management
- [FastAPI](https://fastapi.tiangolo.com/) for REST API server
- [LangChain](https://www.langchain.com/) for LLM orchestration (OpenAI integrations)
- [PyTorch](https://pytorch.org/get-started/locally/) for GPU acceleration (I used CUDA 12.8)
- [Whisper](https://github.com/openai/whisper) for audio transcription
- [OpenAI API (Chat Models)](https://platform.openai.com/docs) for translation and context generation
- `pysubs2` for subtitle file parsing (.ass/.srt);;

### Frontend
- [Node.js](https://nodejs.org/) 18+ and npm
- [Angular](https://angular.io/) 17.3.12 standalone components

## Setting Up the Backend and Frontend

### 1. Clone the Repository

```bash
git clone https://github.com/dragonstonehafiz/translator-helper.git
cd translator-helper
```

### 2. Creating A Virtual Environment

```bash
cd backend
uv venv
.venv\scripts\activate
uv pip install -r requirements.txt
```

### 3. Installing PyTorch with CUDA (Optional/For Hardware Acceleration)

You can skip this section if you have no intention of using **hardware acceleration during transcription**. Translation uses online APIs, so translation speed will be unaffected. Before doing anything, you will need to install the [CUDA toolkit](https://developer.nvidia.com/cuda-downloads). If you are on windows, you will need to install [Microsoft Visual Studio 2022](https://aka.ms/vs/17/release/vs_community.exe) before doing that.

If you intend on using hardware acceleration please take note of which PyTorch versions works with your GPU. For example, 50 Series GPUs do not work with older PyTorch versions. 

All commands that you need to run to install PyTorch with CUDA can be found [here](https://pytorch.org/get-started/locally/). If you need to install older PyTorch versions, check [here](https://pytorch.org/get-started/previous-versions/). Below will be the command I personally used. 

```bash
uv pip uninstall torch torchvision
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

### 4. Configuration

Settings (API keys, model names, temperatures, etc.) are stored as JSON files in `backend/data/`. These files are created automatically with default values the first time the backend starts up. You can set your API keys and preferences through the **Settings page** in the app — changes are saved immediately to the corresponding JSON file.

| File | Provider |
|---|---|
| `backend/data/llm_chatgpt.json` | OpenAI ChatGPT |
| `backend/data/llm_claude.json` | Anthropic Claude |
| `backend/data/llm_llamacpp.json` | llama.cpp (local GGUF) |
| `backend/data/audio_whisper.json` | Whisper |

### 5. Using llama.cpp (Local LLM)

If you want to use a local GGUF model instead of an API-based LLM, you need to install the llama.cpp dependency and place your model file:

1. **Install llama.cpp dependency**
   ```bash
   uv pip install llama-cpp-python
   ```

2. **Place your GGUF model file**
   - Put the model in `backend/model-files/`

3. **Update the model manager**
   - In `backend/utils/model_manager.py`, swap the import and the instantiation line inside `load_llm_model`:

```python
# Change the import at the top of the file:
from models.llm_llamacpp import LLMLlamaCpp  # instead of LLMChatGPT / LLMClaude

# Change the instantiation inside load_llm_model:
if self.llm_client is None:
    self.llm_client = LLMLlamaCpp()  # instead of LLMChatGPT() / LLMClaude()
```

Once started, configure the model file and other settings through the **Settings page** in the app.

### 6. Setting up the Frontend

```bash
cd ..
cd frontend
npm install
```

## Using the App

### 1. Start the Backend Server

From the root directory of this project.

```bash
cd backend
.venv\scripts\activate
python server.py
```

If you have set the whisper model to something like turbo/large, startup may take a bit longer. If there are no issues, you should see this:

```bash
INFO:     Started server process [24084]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

This means the server has started up successfully.

### 2. Start the Frontend

```bash
cd ..
cd frontend
npm run start
```

If the frontend starts successfully, you should see this:

```bash
Watch mode enabled. Watching for file changes...
  ➜  Local:   http://localhost:4200/
  ➜  press h + enter to show help
```

### 3. Access the App

Once the two previous steps are completed, you can access the app by going to http://localhost:4200/.

## Project Structure

```plaintext
translator-helper/
├── backend/                    # FastAPI backend server
│   ├── server.py              # Main FastAPI application entry point
│   ├── routes.py              # API route definitions
│   ├── requirements.txt       # Python dependencies
│   ├── interface/             # Interfaces for model backends
│   ├── models/                # Concrete model implementations
│   ├── data/                  # JSON config files (auto-created on first run)
│   ├── utils/                 # Utility modules
│   │   ├── logger.py          # Logging setup
│   │   ├── utils.py           # General utilities
│   │   └── translate_subs.py  # Translation helpers for subtitles
│   └── outputs/               # Generated subtitle files (.ass)
├── frontend/                  # Angular 17 frontend application
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/    # Reusable components
│   │   │   │   ├── navbar/    # Navigation bar with subsection links
│   │   │   │   ├── subsection/ # Collapsible section container
│   │   │   │   ├── file-upload/ # File upload with drag-and-drop
│   │   │   │   └── text-field/ # Text area with read/write modes
│   │   │   ├── pages/         # Page components
│   │   │   │   ├── settings/  # API and model configuration
│   │   │   │   ├── context/   # Context generation and management
│   │   │   │   ├── transcribe/ # Audio transcription
│   │   │   │   └── translate/ # Text and file translation
│   │   │   └── services/      # Angular services
│   │   │       ├── api.service.ts    # Backend API client
│   │   │       └── state.service.ts  # Context state management
│   │   └── assets/            # Static assets
│   ├── angular.json
│   └── package.json
└── data/                      # Sample subtitle files for testing
```
