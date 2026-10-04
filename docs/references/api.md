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
| `GET /utils/running` | — | `running`, `workflow`, `active_task` (the running workflow and its stage, or `false`/`null`), `running_llm`, `running_audio`, `running_search` (a task holds the model), `loading_llm_model`, `loading_audio_model`, `loading_search_model` |
| `GET /utils/server-variables` | — | `audio`, `llm`, `search` (each client's non-password settings as `[{key, label, value}]`, empty until the client exists), `llm_ready`, `audio_ready`, `search_ready`, `llm_loading_error`, `audio_loading_error`, `search_loading_error` |
| `GET /utils/settings-schema` | — | `audio`, `llm`, `search`: each `{provider, title, fields}` from `config.to_frontend()`, or `null` if the client could not be created |
| `POST /utils/load-audio-model` | JSON `{provider, settings}` | `null`; error if loading, in use, a value is invalid, or initialization fails |
| `POST /utils/load-llm-model` | JSON `{provider, settings}` | same |
| `POST /utils/load-search-model` | JSON `{provider, settings}` | same |
| `POST /utils/get-subtitle-file-info` | multipart `file` (`.ass`/`.srt` only) | `total_lines`, `character_count`, `average_character_count` (strings) |

The load endpoints call `ModelManager.load_*_model(settings)` in a thread pool: submitted keys are validated, saved, then the model is initialized. Omitted keys keep their saved values, so an empty password field leaves the stored key unchanged. Any rejection or failure becomes an `error` envelope; saved settings survive a failed initialization. `provider` is required by the request model but not used.

A schema field is `{key, label, type, value, default, required}` plus `help`, `placeholder`, `options` (select), `min`/`max`/`step` (number) where they apply. `type` is `text`, `password`, `number`, `boolean` or `select`. Password fields send `value: ""` and `is_set: boolean` instead of the stored key.

## Task results

| Method & path | `data` |
|---|---|
| `GET /task-results/{workflow}` | `{workflow, active_task, progress: [current, total], message, eta_seconds, result}` |

`workflow` is one of `translate_line`, `translate_file`, `review_file`, `transcribe_clip`, `transcribe_file`, `update_library`; anything else returns 400. `status` is `idle` (the workflow has not run since the server started; `data` is only `{workflow}`), `processing`, `complete`, or `error`. On `error`, the envelope `message` is the error and `data.message` is the failed stage's last progress text. `result` is null until `complete`:

| Workflow | `result` |
|---|---|
| `translate_line`, `transcribe_clip` | `{text}` |
| `translate_file` | `{output_filename, folder: "translated"}` |
| `transcribe_file` | `{output_filename, folder: "transcribed"}` |
| `review_file` | `{output_filename, folder: "reviewed", corrected_count}` |
| `update_library` | `{proposals: {new_characters, updated_characters, new_glossary, updated_glossary}}` |

Responses never include absolute paths or temp file names. See [`tasks.md`](tasks.md#polling).

## Translate

Prefix `/translate` (`routes/translate.py`). All are multipart form posts that start a workflow and return `processing` with `data: {workflow}`. Each returns an error envelope if a workflow is already running, the LLM isn't loaded, or the input is rejected (for review, files with different line counts).

| Path | Form fields | Workflow | Output |
|---|---|---|---|
| `POST /translate/translate-line` | `text` (required), `context` (JSON string, default `{}`), `input_lang` (`ja`), `output_lang` (`en`) | `translate_line` | `result` in the poll response |
| `POST /translate/translate-file` | `file`, `input_lang` (`ja`), `output_lang` (`en`), `batch_size` (`3`), `series_id` (optional) | `translate_file` | `files/outputs/translated/<base>.<output_lang>.<ext>` |
| `POST /translate/review-translated-file` | `file` (original), `translated_file`, `input_lang` (`ja`), `output_lang` (`en`), `batch_size` (`50`), `series_id` (optional) | `review_file` | `files/outputs/reviewed/<translated stem>.corrected<ext>` |

An unknown `series_id` is ignored and the workflow runs without library context.

## Transcribe

Prefix `/transcribe` (`routes/transcribe.py`). Multipart posts with `file` (audio) and `language` (required). They return `processing` with `data: {workflow}`, or an error if a workflow is running or the audio model isn't loaded.

| Path | Workflow | Output |
|---|---|---|
| `POST /transcribe/transcribe-line` | `transcribe_clip` | `result` in the poll response |
| `POST /transcribe/transcribe-file` | `transcribe_file` | `.ass` file in `files/outputs/transcribed/` |

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
| `POST /library/{series_id}/update` | multipart `file` (subtitle) | `processing` with `{workflow: "update_library"}` |

`relationships` is a dict keyed by character name, with a list of strings as each value. IDs are kebab-case slugs generated by the server.

`/update` completes only after deduplication; its `result` is `{proposals}`.

## File management

Prefix `/file-management` (`routes/file_management.py`). Works over the output folders under `backend/files/outputs/` (`OUTPUTS_DIR`).

| Method & path | Query | Response |
|---|---|---|
| `GET /file-management/list` | `folder` | `data: {files: [{name, size, modified}]}`, newest first |
| `GET /file-management/download` | `folder`, `filename` | File blob |
| `DELETE /file-management` | `folder`, `filename` | `success`, `data: null` |

- `get_files_dir()` checks each `/`-separated segment (alphanumeric, `-`, `_` only; no `..`) and creates the directory if it is missing. An invalid folder returns 400; a missing file returns 404.
- `folder` and `filename` are always **query parameters**. Do not switch these routes to path segments: once `folder` can contain `/`, a `{folder:path}` list route and a `{folder:path}/{filename}` download route are ambiguous, and whichever is registered first swallows the other's requests.

Output folders: `translated`, `reviewed`, `transcribed` (used by the frontend) and `context`.
