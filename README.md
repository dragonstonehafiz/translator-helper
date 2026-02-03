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
- **Translate File**: Upload subtitle files (.ass/.srt) with context window support, download translated output


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

### 4. Getting API Keys and setting up the .env file

In the backend directory, you should see a file called `.env.example`. Make a copy of that file in the same directory and rename to .env. Then generate an API key for [OpenAI](https://platform.openai.com/). Open the `.env` file you just created and copy it over.

```bash
OPENAI_API_KEY="API_KEY"
```

You may notice other lines on the `.env` file like **WHISPER_MODEL** and **WHISPER_DEVICE**. You can update these too if you would like the backend to start with certain settings when you start the backend server.

If you are using a local LLM backend (e.g., llama.cpp), the `.env` can also include model-specific variables such as **LLAMA_MODEL_FILE**, **LLAMA_N_CTX**, **LLAMA_N_GPU_LAYERS**, **LLAMA_N_THREADS**, and **LLAMA_TEMPERATURE**.

You can comment out variables for providers you are not using (and uncomment the ones you are). Leaving all variables uncommented should not cause errors.

Once this is done, the backend should be ready for use.

### 5. Setting up the Frontend

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
│   ├── .env.example           # Example environment variables
│   ├── interface/             # Interfaces for model backends
│   ├── models/                # Concrete model implementations
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
