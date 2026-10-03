# HTTP API

## Purpose

Endpoint contracts for the FastAPI backend at `http://localhost:8000`. How task-starting endpoints run their work lives in [`tasks.md`](tasks.md); the frontend wrappers live in `ApiService` (see [`frontend.md`](frontend.md#apiservice)).

## Contents

- [Response envelope](#response-envelope)
- [Errors](#errors)
- [Utils](#utils)
- [Task results](#task-results)
- [Translate](#translate)
- [Transcribe](#transcribe)
- [Library](#library)
- [File management](#file-management)

## Response envelope

Every JSON endpoint returns:

```json
{ "status": "success | processing | complete | idle | error | loading", "message": null, "data": {} }
```

- Build responses with the helpers in `utils/api_response.py` (`success_response`, `processing_response`, `complete_response`, `idle_response`, `error_response`, `loading_response`) — never construct raw dicts in routes.
- Payload fields go under `data`. Never add root-level fields such as `files` or `result`.
- File download endpoints return the file blob directly, not an envelope.

## Errors

- Precondition failures (model not loaded, a task already running, item not found in a series) return HTTP 200 with `status: "error"` and a `message`.
- `HTTPException`s (e.g. 404 from `load_series`, 400 from an invalid folder or task type) are converted to the envelope with the same HTTP status.
- Request validation errors return 422 with `message: "Invalid request data."` and `data.details`.
- Unhandled exceptions return 500 with `message: "Internal server error."` and are logged.

## Utils

Prefix `/utils` (`routes/utils.py`).

| Method & path | Body | `data` on success |
|---|---|---|
| `GET /utils/running` | — | `running_llm`, `running_audio`, `loading_audio_model`, `loading_llm_model`, `active_task_type` |
| `GET /utils/server-variables` | — | `audio`, `llm`, `search` (each client's server variables), `llm_ready`, `audio_ready`, `search_ready`, `llm_loading_error`, `audio_loading_error`, `search_loading_error` |
| `GET /utils/settings-schema` | — | `audio`, `llm`, `search` settings schemas |
| `POST /utils/load-audio-model` | JSON `{provider, settings}` | `null`; error if already loading or load fails |
| `POST /utils/load-llm-model` | JSON `{provider, settings}` | same |
| `POST /utils/load-search-model` | JSON `{provider, settings}` | same |
| `POST /utils/get-subtitle-file-info` | multipart `file` (`.ass`/`.srt` only) | `total_lines`, `character_count`, `average_character_count` (strings) |

The load endpoints apply `settings` to the current client, then load it synchronously in a thread pool. `provider` is required by the request model but not used.

## Task results

| Method & path | `data` |
|---|---|
| `GET /task-results/{task_type}` | `{task_type, result, progress}` |

`status` is `idle`, `processing`, `complete`, or `error`. `progress` is `{task_type, current, total, status, eta_seconds}` or `null`. Unregistered task types return 400. See [`tasks.md`](tasks.md#polling) for how the status is resolved.

## Translate

Prefix `/translate` (`routes/translate.py`). All are multipart form posts that start background work and return `processing` with `data: {task_type}`. Each returns an error envelope if a task is already running or the LLM isn't loaded.

| Path | Form fields | Polled task type | Output |
|---|---|---|---|
| `POST /translate/translate-line` | `text` (required), `context` (JSON string, default `{}`), `input_lang` (`ja`), `output_lang` (`en`) | `TaskTranslateLine` | `result` in the poll response |
| `POST /translate/translate-file` | `file`, `input_lang` (`ja`), `output_lang` (`en`), `batch_size` (`3`), `series_id` (optional) | `TaskTranslateFile` | `outputs/sub-files/translated/<base>.<output_lang>.<ext>` |
| `POST /translate/review-translated-file` | `file` (original), `translated_file`, `input_lang` (`ja`), `output_lang` (`en`), `batch_size` (`50`), `series_id` (optional) | `TaskRetranslateReviewedLines` | `outputs/sub-files/reviewed/` and `result` in the poll response |

An unknown `series_id` is ignored and the chain runs without library context.

## Transcribe

Prefix `/transcribe` (`routes/transcribe.py`). Multipart posts with `file` (audio) and `language` (required). They return `processing` with `data: {task_type}`, or an error if a task is running or the audio model isn't loaded.

| Path | Polled task type | Output |
|---|---|---|
| `POST /transcribe/transcribe-line` | `TaskTranscribeLine` | `result` in the poll response |
| `POST /transcribe/transcribe-file` | `TaskTranscribeFile` | `.ass` file in `outputs/transcribe-sub-files/` |

## Library

Prefix `/library` (`routes/library.py`). JSON bodies; every mutating endpoint returns the full updated series object (`id`, `name`, `input_lang`, `output_lang`, `notes`, `characters`, `glossary`) as `data`. An unknown `series_id` returns 404; an unknown character or term ID returns an error envelope.

| Method & path | Body | `data` |
|---|---|---|
| `GET /library/` | — | `{series: [{id, name, input_lang, output_lang, character_count, glossary_count}]}` |
| `POST /library/` | `{name, input_lang="ja", output_lang="en", notes=""}` | New series |
| `GET /library/{series_id}` | — | Series |
| `PATCH /library/{series_id}` | Any of `name`, `input_lang`, `output_lang`, `notes` | Series |
| `DELETE /library/{series_id}` | — | `null`; deletes the series folder |
| `POST /library/{series_id}/characters` | `{name, aliases=[], personality=[], relationships={}, history=[]}` | Series |
| `PATCH /library/{series_id}/characters/{character_id}` | Any character field | Series |
| `DELETE /library/{series_id}/characters/{character_id}` | — | Series |
| `POST /library/{series_id}/glossary` | `{term, translation, notes=""}` | Series |
| `PATCH /library/{series_id}/glossary/{term_id}` | Any of `term`, `translation`, `notes` | Series |
| `DELETE /library/{series_id}/glossary/{term_id}` | — | Series |
| `POST /library/{series_id}/update` | multipart `file` (subtitle) | `processing`; starts the library update chain |

`relationships` is a dict keyed by character name, with a list of strings as each value. IDs are kebab-case slugs generated by the server.

For `/update`, the frontend polls `TaskDeduplicateProposals`, whose `result` is `{proposals}`. The start response's `data.task_type` currently says `TaskGenerateLibraryProposals`; the frontend ignores it and uses `TASK_TYPES.updateLibrary`.

## File management

Prefix `/file-management` (`routes/file_management.py`). Works over any directory under `backend/outputs/`.

| Method & path | Query | Response |
|---|---|---|
| `GET /file-management/list` | `folder` | `data: {files: [{name, size, modified}]}`, newest first |
| `GET /file-management/download` | `folder`, `filename` | File blob |
| `DELETE /file-management` | `folder`, `filename` | `success`, `data: null` |

- `folder` may be nested (`sub-files/translated`). `get_files_dir()` checks each `/`-separated segment (alphanumeric, `-`, `_` only; no `..`) and creates the directory if it is missing. An invalid folder returns 400; a missing file returns 404.
- `folder` and `filename` are always **query parameters**. Do not switch these routes to path segments: once `folder` can contain `/`, a `{folder:path}` list route and a `{folder:path}/{filename}` download route are ambiguous, and whichever is registered first swallows the other's requests.

Folders the frontend uses: `sub-files/translated`, `sub-files/reviewed`, `transcribe-sub-files`.
