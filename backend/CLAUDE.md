# Backend — Agent Guidelines

This file covers backend-specific conventions. For project-wide guidelines and frontend docs see the root `CLAUDE.md`.

## Directory Layout

```
backend/
  server.py                  — FastAPI app entry point, CORS, lifespan
  interface/                 — Abstract base classes (LLMInterface, AudioModelInterface, BaseTask)
  models/                    — Concrete model implementations (LLMDeepSeek, LLMClaude, AudioWhisperX, SearchTavily, ...)
  models/model_manager.py    — Singleton that owns LLM/audio/search client lifecycle and exposes infer/transcribe helpers
  orchestrator/
    task_orchestrator.py     — Singleton that runs one chain at a time; pass-through dict between tasks
    result_handler.py        — Singleton; stores latest result per task_type (processing / complete / error)
    progress_handler.py      — Singleton; stores progress per task_type (current, total, status, eta_seconds)
    library/                 — Library update chain tasks
    translate_file/          — File translation chain tasks
    review_file/             — Translated file review chain tasks
    tasks/                   — Single standalone tasks (transcribe line/file, translate line)
  routes/
    shared.py                — Singleton accessors, task type sets, build_task_response, save_upload_to_temp
    library.py               — Series/character/glossary CRUD + library update chain route
    translate.py             — translate-line, translate-file, review-translated-file routes
    transcribe.py            — transcribe-line, transcribe-file routes
    task_results.py          — GET /task-results/{task_type} polling endpoint
    file_management.py       — List/download/delete files under backend/outputs/
    utils.py                 — Settings schema, server variables, model load, subtitle file info
  prompts/                   — Prompt-generation functions (one file per domain)
  utils/
    api_response.py          — Shared response envelope helpers and exception handlers
    config.py                — BACKEND_DIR and OUTPUTS_DIR Path constants
    library.py               — load_series / save_series / slugify / find_character / find_glossary_term
    logger.py                — setup_logger()
    utils.py                 — load_sub_data() and other shared helpers
  outputs/                   — All generated files and logs (gitignored)
    library/<series_id>/     — series.json, characters.json, glossary.json
    sub-files/
      translated/            — File translation chain outputs
      reviewed/              — Translated file review chain outputs (corrected files)
    transcribe-sub-files/    — Transcribed subtitle outputs
    translate-file-logs/     — Per-run batch planning logs for file translation
    review-file-logs/        — Per-run review logs for translated file review
    library-update-logs/     — Per-run library update chain logs
    translator-helper.log    — Shared backend log (task timing, fallback events, model lifecycle)
```

## API Response Envelope

Every JSON endpoint returns:
```json
{ "status": "success | processing | complete | idle | error | loading", "message": null, "data": {} }
```
Use the helpers in `utils/api_response.py` — never construct raw dicts in routes.  
Put payload fields under `data`. Never add root-level fields like `files` or `result`.  
File download endpoints return file blobs directly.

## File Management

`routes/file_management.py` exposes generic list/download/delete endpoints over any directory under `OUTPUTS_DIR`:
```
GET    /file-management/list?folder=<folder>
GET    /file-management/download?folder=<folder>&filename=<filename>
DELETE /file-management?folder=<folder>&filename=<filename>
```
`folder` and `filename` are always **query parameters**, never URL path segments. `folder` may be a nested path (e.g. `sub-files/translated`) — `get_files_dir()` in `shared.py` validates each `/`-separated segment individually (alphanumeric/`-_` only, no `..`) and resolves it under `OUTPUTS_DIR`.

Do not switch these routes back to path-segment params (e.g. `/{folder}/{filename}`) — once `folder` can be more than one segment, a bare `{folder:path}` list route and a `{folder:path}/{filename}` download route become ambiguous (the router can't tell where `folder` ends and `filename` begins), and whichever route is registered first silently swallows requests meant for the other.

## Singletons

Four singletons are shared across the whole backend — always get them via `.get_instance()`:
- `ModelManager` — LLM/audio/search client lifecycle
- `TaskOrchestrator` — task queue and execution
- `ResultHandler` — task result storage
- `ProgressHandler` — task progress storage

`shared.py` holds the pre-resolved references used by all route modules:
```python
model_manager = ModelManager.get_instance()
task_orchestrator = TaskOrchestrator.get_instance()
result_handler = ResultHandler.get_instance()
progress_handler = ProgressHandler.get_instance()
```
Do not call `.get_instance()` again in routes — import from `shared.py` instead.  
Tasks call `.get_instance()` directly since they don't import from routes.

## Task Pattern

Every task extends `BaseTask` (`interface/base_task.py`):
- `TASK_TYPE` — class-level string constant used as the registry key everywhere
- `task_type` property — returns `self.TASK_TYPE`
- `run_task()` — reads `self.get_data()`, does work, returns a dict

**The pass-through rule**: every `run_task()` must return `{**data, ...new_keys}`. Never return a bare dict with only new keys — upstream data (`file_path`, `series`, `log_dir`, etc.) will be silently dropped and all downstream tasks will break.

**Standard task body**:
```python
def run_task(self) -> dict:
    model_manager = ModelManager.get_instance()
    result_handler = ResultHandler.get_instance()
    progress_handler = ProgressHandler.get_instance()
    llm_client = model_manager.get_llm_client()
    if llm_client is None:
        result_handler.set_error(self.task_type, "LLM model not initialized")
        raise RuntimeError("LLM model not initialized")

    data = self.get_data()
    # ... read inputs from data ...

    result_handler.set_processing(self.task_type)
    try:
        llm_client.set_running(True)
        # ... do work ...
        result_handler.set_complete(self.task_type)        # pass result dict only for final chain task
        return {**data, "new_key": value}
    except Exception as exc:
        result_handler.set_error(self.task_type, str(exc))
        raise
    finally:
        llm_client.set_running(False)
```

Only the **final task** in a chain calls `result_handler.set_complete(task_type, payload)` with a result dict. Intermediate tasks call `set_complete(task_type)` with no payload.

## Registering a New Task

When adding any new task to a chain:
1. Add `TASK_TYPE` to the appropriate set in `shared.py` (`LLM_TASK_TYPES`, `AUDIO_TASK_TYPES`, or `LIBRARY_TASK_TYPES`) — if omitted, `/task-results/{task_type}` returns 400 and the frontend silently fails
2. Follow the pass-through rule above
3. Call `result_handler.clear(FinalTask.TASK_TYPE)` in the route before starting the chain so a stale result from a previous run is not immediately returned
4. Write a numbered log JSON to `log_dir` matching the slot order

## Task Type Sets (shared.py)

```python
LIBRARY_TASK_TYPES   # library update chain tasks
LLM_TASK_TYPES       # any task that uses the LLM client
AUDIO_TASK_TYPES     # transcription tasks
```
A task can appear in more than one set (e.g. `TaskScanSubtitleFile` is in both `LIBRARY_TASK_TYPES` and `LLM_TASK_TYPES`).

## Chain Routing

Chains are started in background tasks from route handlers. The route:
1. Validates preconditions (`is_llm_ready()`, `is_running()`)
2. Saves uploaded files to temp paths via `save_upload_to_temp()`
3. Loads any needed data (e.g. `load_series(series_id)`)
4. Calls `result_handler.clear(FinalTask.TASK_TYPE)` to wipe any stale result
5. Adds a background task that calls the chain runner function
6. Returns `processing_response(...)`

Chain runner functions (e.g. `run_translation_file_chain`) live in `translate.py`, not in the orchestrator. They set up `log_dir`, call `task_orchestrator.clear_tasks()`, add tasks, then call `run_tasks(initial_data=data)`.

## Polling

The frontend polls `GET /task-results/{task_type}` — always the **final task** in the chain.  
`build_task_response()` in `shared.py` handles all chains with one rule: if the orchestrator is running and the polled task has no result yet, return processing with the active task's progress. No chain-specific if-blocks needed.

## Library Storage

Series data is split across three JSON files per series:
```
backend/outputs/library/<series_id>/
  series.json      — id, name, input_lang, output_lang, notes
  characters.json  — list of {id, name, aliases[], personality[], relationships{}, history[]}
  glossary.json    — list of {id, term, translation, notes}
```
Always use `load_series(series_id)` and `save_series(series)` from `utils/library.py` — never read/write these files directly. `save_series` splits and writes all three files atomically, then restores the lists on the caller's dict. Series IDs are kebab-case slugs derived from the name.

## Translation Chain Log Numbering

File translation (`translate-file-logs/`):
- `01-plan-translation-batches.json`
- `02-split-oversized-batches.json`
- `03-select-library-context.json`
- `04-translate-file-batch-failures.json` (only written when batch failures occur)

Review chain (`review-file-logs/`):
- `01-plan-translation-batches.json`
- `02-select-library-context.json`
- `03-review-translated-batches.json` (+ `03-review-translated-batch-failures.json` on failure)
- `04-retranslate-reviewed-lines.json`

Library update chain (`library-update-logs/`):
- `01-scan-subtitle-file.json`
- `02-check-against-library.json`
- `03-generate-search-queries.json`
- `04-web-search.json`
- `05-generate-library-proposals.json`
- `06-deduplicate-proposals.json`

## Prompts

Prompt functions live in `backend/prompts/` — one file per domain. Import and call directly; there is no wrapper class. All prompt functions return a string used as a `system_prompt`. The user message (subtitle lines, etc.) is built separately and passed as `prompt` to `model_manager.llm_infer(...)`.

## Code Style

- **Docstrings required** on all Python functions, classes, and methods — one concise line minimum
- No backward-compat shims during refactors — update call sites directly
- `OUTPUTS_DIR` is the canonical path constant for all output directories — import from `utils/config.py`
- Do not add route-specific root payload fields; everything goes under `data`
- Never swallow errors silently — every exception path must call `result_handler.set_error(...)` and re-raise
