# Tasks and Chains

## Purpose

How long-running backend work is structured: the `BaseTask` pattern, `TaskOrchestrator`, result and progress handlers, the task chains and how routes start them, task-type registration, run logs, and prompts. Endpoint contracts live in [`api.md`](api.md); the frontend side of polling lives in [`frontend.md`](frontend.md#polling-pattern).

## Contents

- [Task pattern](#task-pattern)
- [Orchestrator](#orchestrator)
- [Result and progress handlers](#result-and-progress-handlers)
- [Chains](#chains)
- [Starting a chain from a route](#starting-a-chain-from-a-route)
- [Task-type sets](#task-type-sets)
- [Polling](#polling)
- [Run logs](#run-logs)
- [Prompts](#prompts)
- [Adding a task](#adding-a-task)

## Task pattern

Every task extends `BaseTask` (`orchestrator/base_task.py`):

- `TASK_TYPE` — class-level string constant (the class name, e.g. `"TaskTranslateFile"`), used as the key in every registry and by the frontend's `TASK_TYPES`.
- `task_type` property — returns `self.TASK_TYPE`.
- `run_task()` — reads `self.get_data()`, does the work, returns a dict.

**Pass-through rule**: every non-final task's `run_task()` returns `{**data, ...new_keys}`. Returning only the new keys silently drops upstream data (`file_path`, `series`, `log_dir`, etc.) and breaks every downstream task. Final tasks may return `{}`.

Standard body:

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
    result_handler.set_processing(self.task_type)
    try:
        model_manager.acquire_llm()   # raises if the LLM is not loaded, loading or in use
        # ... work, calling progress_handler.set(self.task_type, {...}) as it advances ...
        result_handler.set_complete(self.task_type)   # pass a result dict only in a chain's final task
        return {**data, "new_key": value}
    except Exception as exc:
        result_handler.set_error(self.task_type, str(exc))
        raise
    finally:
        model_manager.release_llm()
```

Tasks call the client directly: `llm_client.infer(...)`, `audio_client.transcribe_line/file(...)`, `search_client.search(...)`. Read provider settings through `llm_client.config`, e.g. `llm_client.config.temperature.value`. `TaskTranscribeFile` saves the returned subtitles itself. Tasks that receive an uploaded temp file delete it in `finally`.

## Orchestrator

`TaskOrchestrator` (`orchestrator/task_orchestrator.py`) holds one ordered task list:

- `clear_tasks()`, `add_task(task)`, `run_tasks(initial_data)` — runs each task in order, passing each task's returned dict to the next via `set_data()`.
- `run_task(task, data)` — clears the list, adds one task, and runs it.
- `run_tasks` raises `RuntimeError` if a chain is already running; `is_running()` and `get_active_task_type()` expose the current state.
- Each task's start, finish (with elapsed time and `log_dir`), and failure is written to `files/logs/translator-helper.log`.

## Result and progress handlers

- `ResultHandler` stores one record per task type: `set_processing`, `set_complete(task_type, result=None)`, `set_error(task_type, error)`, `clear`, `get`.
- Only a chain's **final task** passes a result dict to `set_complete`. Tasks whose output is a file (`TaskTranslateFile`, `TaskTranscribeFile`) complete with no payload; the frontend refreshes its downloads list instead.
- `ProgressHandler.set(task_type, {current, total, status, eta_seconds})` stores progress for the progress overlay. Tasks without granular progress use `current: 0, total: 1`.

## Chains

| Chain | Started by | Tasks in order (folder) | Final task (polled) |
|---|---|---|---|
| Translate line | `POST /translate/translate-line` | `TaskTranslateLine` (`tasks/`) | `TaskTranslateLine` |
| Translate file | `POST /translate/translate-file` | `TaskPlanTranslationBatches` → `TaskSplitOversizedBatches` → `TaskSelectLibraryContext` → `TaskTranslateFile` (`translate_file/`) | `TaskTranslateFile` |
| Review translated file | `POST /translate/review-translated-file` | `TaskPlanTranslationReviewBatches` → `TaskSelectLibraryContextForReview` → `TaskReviewTranslatedBatches` → `TaskRetranslateReviewedLines` (`review_file/`) | `TaskRetranslateReviewedLines` |
| Library update | `POST /library/{series_id}/update` | `TaskScanSubtitleFile` → `TaskCheckAgainstLibrary` → `TaskGenerateSearchQueries` → `TaskWebSearch` → `TaskGenerateLibraryProposals` → `TaskDeduplicateProposals` (`library/`) | `TaskDeduplicateProposals` |
| Transcribe line | `POST /transcribe/transcribe-line` | `TaskTranscribeLine` (`tasks/`) | `TaskTranscribeLine` |
| Transcribe file | `POST /transcribe/transcribe-file` | `TaskTranscribeFile` (`tasks/`) | `TaskTranscribeFile` |

Library-update proposals are only returned to the frontend; nothing is written to the series until the user accepts a proposal, which goes through the normal library CRUD endpoints.

## Starting a chain from a route

The route handler:

1. Checks preconditions — `task_orchestrator.is_running()` and `model_manager.is_llm_ready()` / `is_audio_ready()` — and returns an `error` envelope if they fail.
2. Saves uploads to temp files with `save_upload_to_temp()`.
3. Loads any needed data (e.g. `load_series(series_id)`).
4. Adds a background task and returns `processing_response({"task_type": ...})`.

Multi-task chains run through a runner function in the route module (`run_translation_file_chain`, `run_review_translated_file_chain` in `translate.py`; `_run_library_update_chain` in `library.py`). The runner creates the timestamped `log_dir`, calls `result_handler.clear(FinalTask.TASK_TYPE)` so a stale result isn't returned to the first poll, then `clear_tasks()` → `add_task(...)` → `run_tasks(initial_data=data)`, and records any exception against the final task type. (The library route clears the result and builds `log_dir` in the handler instead of the runner.) Single tasks run through `run_single_task()` in `shared.py`.

## Task-type sets

`routes/shared.py` defines:

| Set | Purpose |
|---|---|
| `LIBRARY_TASK_TYPES` | All six library-update tasks |
| `AUDIO_TASK_TYPES` | Transcription tasks |
| `TRANSLATE_TASK_TYPES` | `TaskTranslateLine`, `TaskTranslateFile`, `TaskRetranslateReviewedLines` |
| `TRANSCRIBE_TASK_TYPES` | `TaskTranscribeLine`, `TaskTranscribeFile` |

A task can be in more than one set. `GET /task-results/{task_type}` only accepts types in `LIBRARY_TASK_TYPES ∪ TRANSLATE_TASK_TYPES ∪ AUDIO_TASK_TYPES`; any other type returns 400.

## Polling

The frontend polls `GET /task-results/{task_type}` with the chain's **final** task type. `build_task_response()` in `shared.py` handles every chain with one rule: while the orchestrator is running and the polled type has no result yet, return `processing` with the *currently active* task's progress, so intermediate tasks' progress shows up without chain-specific code. Otherwise it returns `idle`, `error`, `complete` (with `result`), or `processing` from the stored record.

## Run logs

Each multi-task chain writes numbered JSON files into its per-run `log_dir` (`files/logs/<chain>/<YYYYmmdd-HHMMSS>-<name>/`), numbered by the task's position in the chain:

| Chain | Files |
|---|---|
| Translate file (`translate_file/`) | `01-plan-translation-batches.json`, `02-split-oversized-batches.json`, `03-select-library-context.json`, `04-translate-file-batch-failures.json` (only when batches fail) |
| Review (`review_file/`) | `01-plan-translation-batches.json`, `02-select-library-context.json`, `03-review-translated-batches.json` (+ `03-review-translated-batch-failures.json` on failure), `04-retranslate-reviewed-lines.json` |
| Library update (`update_library/`) | `01-scan-subtitle-file.json`, `02-check-against-library.json`, `03-generate-search-queries.json`, `04-web-search.json`, `05-generate-library-proposals.json`, `06-deduplicate-proposals.json` |

## Prompts

System-prompt builders live in `backend/prompts/`, one module per domain (`translate.py`, `translate_file.py`, `review_file.py`, `library.py`, `library_context.py`, `context.py`, shared `helpers.py`). They are plain functions that return a string used as the `system_prompt`; the user message (subtitle lines, etc.) is built in the task and passed as `prompt` to `llm_client.infer(...)`. There is no wrapper class.

## Adding a task

1. Create the task class in the chain's folder under `orchestrator/`, following the [task pattern](#task-pattern) and the pass-through rule.
2. Add its `TASK_TYPE` to the matching set(s) in `routes/shared.py`. If the new task is a chain's final task and is missing from the polling sets, `/task-results/{task_type}` returns 400 and the frontend's poll fails.
3. Add it to the chain runner in the right position.
4. If the chain writes run logs, write a numbered JSON matching its position and renumber later files.
5. If it changes the final task, update `TASK_TYPES` in the frontend (see [`frontend.md`](frontend.md#stateservice)) and the `result_handler.clear(...)` call.
