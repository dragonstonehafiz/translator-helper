# Tasks and Workflows

## Purpose

How long-running backend work is structured: typed task data, the `BaseTask` pattern, `TaskOrchestrator` and its state store, the six workflows and how routes start them, polling, run logs, and prompts. Endpoint contracts live in [`api.md`](api.md); the frontend side of polling lives in [`frontend.md`](frontend.md#polling-pattern).

## Contents

- [Typed task data](#typed-task-data)
- [Task pattern](#task-pattern)
- [Orchestrator](#orchestrator)
- [Workflows](#workflows)
- [Starting a workflow from a route](#starting-a-workflow-from-a-route)
- [Polling](#polling)
- [Run logs](#run-logs)
- [Prompts](#prompts)
- [Adding a task](#adding-a-task)

## Typed task data

Every task input and output is a `@dataclass(kw_only=True)` subclass of `TaskData`, in the `orchestrator/task_data/` package: `base.py` (`TaskData`, `extend()`, shared outputs), `library_types.py` (series library shapes), `general.py` (translate line and both transcriptions), `translation.py` (translate file and review) and `library_update.py` (library update and proposals). Import from the specific module. Required fields have no defaults, so a stage that forgets one fails when the next object is built, not several stages later.

- A stage that adds required fields builds the next class with `extend(data, NextClass, new_field=...)`, which copies every existing field.
- A stage that only changes existing fields returns `dataclasses.replace(data, ...)`.
- Subtitles are loaded **once**, by the workflow, and carried as `pysubs2.SSAFile` objects (`subtitles`, `translated_subtitles`). Tasks never open input files.
- Series library data is carried as typed mappings (`SeriesSnapshot`, `CharacterEntry`, `GlossaryEntry`); library-update proposals use `LibraryProposals` and its four entry types.
- `TaskData.run_label()` names the run's log folder (the uploaded filename where there is one).

Main chains of types:

| Workflow | Data, stage by stage |
|---|---|
| Translate file | `TranslationData` → `PlannedTranslationData` (+ `batches`) → same type with `context`/`library_context` → `TranslatedSubtitleData` → `FileOutputData` |
| Review | `ReviewData` (adds `translated_filename`, `translated_subtitles`) → `PlannedReviewData` → same type with context → `ReviewedData` (+ `corrections`) → `CorrectedSubtitleData` → `ReviewFileOutputData` (+ `corrected_count`) |
| Library update | `LibraryUpdateData` → `ExtractedLibraryData` (+ `findings`) → `ClassifiedLibraryData` (+ `known`, `unknown`) → `QueriedLibraryData` (+ `search_queries`) → `SearchedLibraryData` (+ `search_results`) → `ProposedLibraryData` (+ `proposals`) → `ProposalOutputData` |
| Translate line / transcribe clip | `TranslateLineData` / `TranscribeClipData` → `TextOutputData` |
| Transcribe file | `TranscribeFileData` → `TranscribedSubtitleData` → `FileOutputData` |

## Task pattern

Every task extends `BaseTask[InputData, OutputData]` (`orchestrator/base_task.py`) and declares `input_type` and `output_type`. The orchestrator supplies the input with `set_data()`; `get_data()` raises if none was supplied. The task name shown as the active stage is the class name.

```python
class TaskExample(BaseTask[PlannedTranslationData, PlannedTranslationData]):
    input_type = PlannedTranslationData
    output_type = PlannedTranslationData

    def run_task(self, report_progress: ReportProgress, write_log: WriteLog) -> PlannedTranslationData:
        data = self.get_data()
        model_manager = ModelManager.get_instance()
        llm = model_manager.acquire_llm()   # raises if the LLM is not loaded, loading or in use
        try:
            report_progress(0, 1, "Doing the thing", 0.0)
            raw = llm.infer(prompt=..., system_prompt=...)
        finally:
            model_manager.release_llm()
        write_log("01-example.json", {"raw_output": raw})
        return replace(data, ...)
```

- Tasks **raise** on failure. They never record errors, results or progress themselves; the orchestrator does.
- Progress goes only through `report_progress(current, total, message, eta_seconds)`; diagnostics only through `write_log(filename, content)`.
- Tasks call the model clients directly (`infer`, `transcribe_line`/`transcribe_file`, `search`) between `acquire_*()` and `release_*()`. Read provider settings through `llm.config`, e.g. `llm.config.temperature.value`.
- Tasks don't save output files or delete temp inputs; the workflow's `finish` and `cleanup` callbacks do.

## Orchestrator

`TaskOrchestrator` (`orchestrator/task_orchestrator.py`) runs **one workflow at a time** on its own single-worker thread pool.

- `run(workflow, tasks, data, *, finish, cleanup)` is the only way to run tasks. It rejects an unknown workflow, an empty task list, a busy runner or a shutting-down server by raising, without changing the running workflow. Otherwise it records the workflow as processing, schedules it and returns immediately; from then on the orchestrator owns the run.
- Each stage: record it as the active stage (resetting progress), check `isinstance(data, task.input_type)`, run it with bound `report_progress`/`write_log` callbacks, check the output against `task.output_type`, pass it to the next stage. Start, elapsed time and failure are written to `files/logs/translator-helper.log`.
- After the last stage, `finish(data)` turns the output into the workflow's result (saving a file where needed). `cleanup()` then always runs, on success and failure. A cleanup error is reported only if nothing failed earlier.
- `TaskStateHandler` (`orchestrator/task_state_handler.py`, reached with `get_state_handler()`) keeps one `TaskState` per workflow: `status`, `active_task`, `progress` (`current`, `total`), `message`, `eta_seconds`, `result`, `error`. Starting a workflow replaces its previous record; a failure keeps the failed stage and its last progress. `get()` returns a copy.
- `get_running_state()` returns the running workflow's state, or `None` when idle. `shutdown()` refuses new runs and waits for the running one, including its cleanup; the server lifespan calls it before releasing the models.

## Workflows

Workflow functions live in `orchestrator/workflows/`. Each prepares its typed input, builds its own task list and calls `run()`.

| Workflow ID | Started by | Function | Tasks in order | Result |
|---|---|---|---|---|
| `translate_line` | `POST /translate/translate-line` | `start_translate_line` | `TaskTranslateLine` | `TextOutputData` |
| `translate_file` | `POST /translate/translate-file` | `start_translate_file` | `TaskPrepareTranslationBatches` → `TaskSelectLibraryContext` → `TaskTranslateBatches` | `FileOutputData` |
| `review_file` | `POST /translate/review-translated-file` | `start_review_file` | `TaskPrepareReviewBatches` → `TaskSelectLibraryContext` → `TaskReviewTranslatedBatches` → `TaskRetranslateReviewedLines` | `ReviewFileOutputData` |
| `transcribe_clip` | `POST /transcribe/transcribe-line` | `start_transcribe_clip` | `TaskTranscribeClip` | `TextOutputData` |
| `transcribe_file` | `POST /transcribe/transcribe-file` | `start_transcribe_file` | `TaskTranscribeFile` | `FileOutputData` |
| `update_library` | `POST /library/{series_id}/update` | `start_update_library` | `TaskExtractLibraryFindings` → `TaskClassifyLibraryFindings` → `TaskGenerateSearchQueries` → `TaskWebSearch` → `TaskGenerateLibraryProposals` → `TaskDeduplicateCharacterUpdates` | `ProposalOutputData` |

Behaviour to know:

- **Batch preparation.** `TaskPrepareTranslationBatches` asks the LLM for semantic batches, then splits any batch larger than `batch_size` with a second LLM call per batch, falling back to an even split if that reply is invalid. `TaskPrepareReviewBatches` keeps the model's batches as planned (no splitting). Both use helpers in `translate_file/batch_preparation.py`.
- **Library context.** One `TaskSelectLibraryContext`, constructed with the data class it runs on (`PlannedTranslationData` or `PlannedReviewData`), returns that same class with `context` and `library_context` filled in. With no series or an empty library it returns the input unchanged without an LLM call. An unknown `series_id` means no library context.
- **Review pre-check.** `start_review_file` loads both files and rejects them before any LLM call if their line counts differ.
- **Library update.** Events found in the file are kept in `unknown.events` but never searched. No unknown names or terms gives an empty query list, and no queries gives empty search results, without needing the search client. When queries exist, a missing or unready search client fails the workflow. Deduplication only filters `updated_characters` additions to `personality`, `history` and `relationships`; the other proposal categories pass through. Proposals are only returned to the frontend; nothing is written to the series until the user accepts one through the library CRUD endpoints.
- **Saving.** `workflows/file_output.py` names and saves outputs, replacing any existing file:

| Workflow | Filename | Folder |
|---|---|---|
| `translate_file` | `<first filename segment>.<sanitized output language>.<original extension>` | `translated` |
| `review_file` | `<translated stem>.corrected<suffix>`, `.ass` if there is no suffix | `reviewed` |
| `transcribe_file` | `<first filename segment>.<sanitized language>.ass` | `transcribed` |

Translation also strips matching outer quotes or asterisks from each line (`TaskTranslateBatches`); review and transcription don't.

## Starting a workflow from a route

The route handler:

1. Checks preconditions — `TaskOrchestrator.get_instance().get_running_state()` and `ModelManager.get_instance().is_llm_ready()` / `is_audio_ready()` — and returns an `error` envelope if they fail. These checks are advisory; `run()` is what actually rejects a second workflow.
2. Saves uploads to temp files with `save_upload_to_temp()`. Until the workflow is accepted, the route owns them.
3. Loads any needed data (e.g. `load_series(series_id)`).
4. Calls the workflow's `start_*` function. If it raises (bad input, mismatched review files, busy runner), the route deletes its temp files with `remove_temp_files()` and returns an `error` envelope.
5. Returns `processing_response({"workflow": ...})`. The accepted workflow's `cleanup` deletes the temp files when the run ends.

## Polling

The frontend polls `GET /task-results/{workflow}` with the ID returned in `data.workflow`. The route reads one `TaskState` snapshot and returns it as `{workflow, active_task, progress: [current, total], message, eta_seconds, result}`. `result` is null until the workflow completes and then has its public shape (see [`api.md`](api.md#task-results)); absolute paths and subtitle objects are never returned. A workflow that has not run since the server started returns `idle` with only `{workflow}`.

## Run logs

Tasks write diagnostics with `write_log(filename, content)` (`RunLog` in `task_orchestrator.py`). The first write creates the run's folder, `files/logs/<workflow>/<YYYYmmdd-HHMMSS>-<input filename or workflow>/`, named from the run's start time (adding `-2`, `-3`, … if it already exists). The folder is kept after success or failure. A run that writes nothing creates no folder.

| Workflow | Files |
|---|---|
| `translate_file` | `01-plan-translation-batches.json` (the model's plan with batch sizes), `02-split-oversized-batches.json` (each repaired batch: original range and size, `model` or `deterministic_fallback`, failure and raw reply on fallback, replacement ranges; then the final plan), `04-translate-file-batch-failures.json` (only when batches fail) |
| `review_file` | `01-plan-translation-batches.json`, `03-review-translated-batches.json` (+ `03-review-translated-batch-failures.json` on failure), `04-retranslate-reviewed-lines.json` |
| `update_library` | `01-scan-subtitle-file.json`, `02-check-against-library.json`, `03-generate-search-queries.json`, `04-web-search.json`, `05-generate-library-proposals.json`, `06-deduplicate-proposals.json` |

Library-context selection writes no log. Line translation and both transcriptions write none, so they leave no folder.

## Prompts

System-prompt builders live in `backend/prompts/`, one module per domain (`translate.py`, `translate_file.py`, `review_file.py`, `library.py`, `library_context.py`, `context.py`, shared `helpers.py`). They are plain functions that return a string used as the `system_prompt`; the user message (subtitle lines, etc.) is built in the task and passed as `prompt` to `llm.infer(...)`. There is no wrapper class.

## Adding a task

1. Declare its input and output types in the matching `orchestrator/task_data/` module (or reuse existing ones), with required fields and no defaults.
2. Create the task class in the workflow's folder under `orchestrator/`, following the [task pattern](#task-pattern).
3. Add it to the workflow function's task list in `orchestrator/workflows/`, between stages whose output and input types match.
4. If it writes diagnostics, use `write_log` with a numbered filename matching its position.
5. A new workflow also needs its ID added to `WORKFLOWS` in `task_orchestrator.py`, a public result shape in `routes/task_results.py`, and an entry in `WORKFLOW_TYPES` in the frontend (see [`frontend.md`](frontend.md#stateservice)).
