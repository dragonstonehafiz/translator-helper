# Architecture

## Purpose

System shape, repository layout, runtime boundaries, model backends, and on-disk storage. Task-chain mechanics live in [`tasks.md`](tasks.md), endpoint contracts in [`api.md`](api.md), and frontend detail in [`frontend.md`](frontend.md).

## Contents

- [System overview](#system-overview)
- [Repository layout](#repository-layout)
- [Backend layout](#backend-layout)
- [Runtime model](#runtime-model)
- [Singletons](#singletons)
- [Model backends](#model-backends)
- [Storage](#storage)
- [Current limitations](#current-limitations)

## System overview

- **Frontend**: Angular 17.3 standalone app in `frontend/`, served by `ng serve` on `http://localhost:4200`. It talks to the backend over HTTP at the hardcoded base URL `http://localhost:8000` (`ApiService.baseUrl`).
- **Backend**: FastAPI app in `backend/`, started with `python server.py` (uvicorn on `0.0.0.0:8000`, `reload=True`). CORS allows only `http://localhost:4200`.
- **External services**: LLM provider APIs (DeepSeek, Anthropic, OpenAI) or a local llama.cpp GGUF model, WhisperX for transcription, and Tavily for web search during library updates.
- **No database.** Persistent data is JSON and subtitle files on disk (see [Storage](#storage)); task state and results live in memory and are lost on restart.

## Repository layout

```
backend/        FastAPI server (see Backend layout)
frontend/       Angular app (see frontend.md)
data/sample/    Sample audio (.wav) and subtitle (.ass) files for manual testing
screenshots/    Images used by the root README
docs/           Agent-facing documentation (this tree)
AGENTS.md       Agent entry point
README.md       User setup and usage
```

## Backend layout

```
backend/
  server.py                  FastAPI app, CORS, lifespan (starts background model loading)
  models/
    manager.py               ModelManager singleton — owns the three clients, loading and in-use tracking
    state.py                 ModelState enum (NOT_LOADED, LOADED, ERROR)
    config.py                ModelConfig base, ConfigField, option types (text, number, integer, boolean, dropdown)
  llm/                       LLMInterface (interface.py) + LLMDeepSeek, LLMClaude, LLMChatGPT, LLMLlamaCpp
  audio/                     AudioModelInterface (interface.py) + AudioWhisperX, AudioWhisper;
                             devices.py — torch device discovery
  search/tavily.py           SearchTavily
  library/repository.py      Series load/save, slugs, character/glossary lookup; domain errors
  orchestrator/
    base_task.py             BaseTask abstract base
    task_orchestrator.py     TaskOrchestrator singleton — runs one task chain at a time
    result_handler.py        ResultHandler singleton — latest result per task type
    progress_handler.py      ProgressHandler singleton — progress per task type
    library/                 Library update chain tasks
    translate_file/          File translation chain tasks
    review_file/             Translated-file review chain tasks
    tasks/                   Standalone tasks (transcribe line/file, translate line)
  routes/
    __init__.py              Aggregates routers
    shared.py                Singleton references, task-type sets, polling/upload/file helpers
    library.py               Series/character/glossary CRUD + library update chain
    translate.py             translate-line, translate-file, review-translated-file + chain runners
    transcribe.py            transcribe-line, transcribe-file
    task_results.py          GET /task-results/{task_type}
    file_management.py       List/download/delete files under files/outputs/
    utils.py                 Status, settings schema, model loading, subtitle file info
  prompts/                   System-prompt builders, one module per domain
  utils/
    api_response.py          Response envelope helpers and global exception handlers
    config.py                BACKEND_DIR, FILES_DIR, CONFIG_DIR, LIBRARY_DIR, OUTPUTS_DIR, LOGS_DIR
    logger.py                setup_logger() — shared log file
    subtitles.py             load_sub_data(), analyze_subtitle_file()
  tests/                     Standalone CLI harnesses (not an automated test suite)
  model-files/               Local GGUF models for llama.cpp
  files/                     Runtime data (gitignored): config/, library/, outputs/, logs/
```

Importing `utils` does not import torch; only `audio/` does.

## Runtime model

- On startup, the `server.py` lifespan loads the LLM, audio, and search clients on three daemon threads, so the server accepts requests before models are ready. On shutdown it waits for those loads to finish, then calls `ModelManager.shutdown()` to release the clients. It does not yet wait for a running task chain.
- Long-running work is started from a route via FastAPI `BackgroundTasks`; the route returns `processing` immediately and the frontend polls `GET /task-results/{task_type}`. See [`tasks.md`](tasks.md).
- `TaskOrchestrator` holds a single chain and refuses to start another while one is running — the app supports one transcription/translation/library job at a time across all users.

## Singletons

Four singletons are shared across the backend, always obtained with `.get_instance()`:

| Singleton | Owns |
|---|---|
| `ModelManager` | The LLM, audio and search clients; loading flags and errors; in-use flags |
| `TaskOrchestrator` | The queued task list, running flag, active task type |
| `ResultHandler` | Latest `{status, result, error}` record per task type |
| `ProgressHandler` | Progress dict per task type (`current`, `total`, `status`, `eta_seconds`) |

`routes/shared.py` resolves all four once; route modules import them from there and do not call `.get_instance()` themselves. Tasks call `.get_instance()` directly because they don't import from `routes`.

## Model backends

- `models/manager.py` picks one provider class per slot: `LLM_PROVIDER = LLMDeepSeek`, `AUDIO_PROVIDER = AudioWhisperX`, `SEARCH_PROVIDER = SearchTavily`. `LLMClaude`, `LLMChatGPT`, `LLMLlamaCpp` and `AudioWhisper` implement the same interfaces; to use one, change the constant. The `provider` field on load requests is accepted but unused.
- A provider exposes only `provider_id`, `config`, `state`, `configure(config)`, `initialize()`, `shutdown()` and its operation: `infer()`, `transcribe_line()` / `transcribe_file()`, or `search()`. `state` is a `ModelState`; readiness is `state == ModelState.LOADED`. A failed operation does not change the state. `transcribe_file()` returns a `pysubs2.SSAFile` and does not save it.
- Settings are declared once per provider as a `ModelConfig` dataclass next to the provider (`DeepSeekConfig`, `WhisperXConfig`, `TavilyConfig`, …), one `setting(label, option, default)` per field. The base class loads and saves `backend/files/config/<CONFIG_FILE>` and builds the Settings-page schema (`to_frontend()`). A missing file is created with defaults; unknown keys are ignored; malformed JSON is reported as a loading error and left untouched. Submitted values are validated by their option type; a saved dropdown value that is no longer listed is kept and stays selectable. Password fields are never sent to the browser — the schema reports only `is_set`.
- `ModelManager.load_*_model(settings)` is the only way to (re)load a model: it rejects the call if that model is loading or in use, otherwise creates the client if needed, applies and saves the submitted settings, configures and initializes it. It raises on failure and records the message in `*_loading_error`; saved settings are kept. A rejected or invalid request changes nothing.
- Tasks mark a model busy with `model_manager.acquire_llm()` / `acquire_audio()` / `acquire_search()` inside their `try`, and call the matching `release_*()` in `finally`. Acquire raises if the model is not loaded, loading or already in use; release only clears the flag for the thread that set it. `GET /utils/running` reports these flags.

## Storage

All paths are under `backend/` and defined once in `utils/config.py`; build paths from those constants, never by hand.

| Path | Contents | Written by |
|---|---|---|
| `files/config/*.json` | Model settings and API keys per provider | Model clients |
| `files/library/<series_id>/series.json` | `id`, `name`, `input_lang`, `output_lang`, `notes` | `library/repository.save_series` |
| `files/library/<series_id>/characters.json` | List of `{id, name, aliases[], personality[], relationships{}, history[]}` | `library/repository.save_series` |
| `files/library/<series_id>/glossary.json` | List of `{id, term, translation, notes}` | `library/repository.save_series` |
| `files/outputs/translated/` | File translation chain output | `TaskTranslateFile` |
| `files/outputs/reviewed/` | Review chain output (corrected file) | `TaskRetranslateReviewedLines` |
| `files/outputs/transcribed/` | Transcribed `.ass` files | `TaskTranscribeFile` |
| `files/outputs/context/` | Saved context files (no active writer) | — |
| `files/logs/translate_file/`, `review_file/`, `update_library/` | One timestamped folder of numbered JSON logs per run | Chain tasks (see [`tasks.md`](tasks.md#run-logs)) |
| `files/logs/translator-helper.log` | Shared backend log: task start/finish timing, model lifecycle, unhandled exceptions | `utils/logger` |

Library rules:

- Always use `load_series(series_id)` and `save_series(series)` from `library/repository.py` — never read or write the three files directly. `load_series` merges them into one dict and raises `SeriesNotFoundError` if the series is missing; an invalid ID raises `InvalidSeriesIdError`. The repository does not import FastAPI: `utils/api_response.register_exception_handlers` maps these errors to 404 and 400. Translate/review treat only `SeriesNotFoundError` as "no series context". `save_series` splits the dict, writes all three files, and restores the lists on the caller's dict.
- Series, character, and glossary IDs are kebab-case slugs of the name/term, made unique with `unique_slug`.

## Current limitations

- No authentication.
- No database; task results, progress, and frontend task state do not survive a backend restart or browser refresh.
- One job at a time across the whole server.
- Desktop-only UI.
