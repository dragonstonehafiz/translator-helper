# Translator Helper - Agent Guidelines

This document provides guidelines for AI agents working on the Translator Helper project. It describes the project structure, reusable components, and best practices.

## Project Overview

Translator Helper is a full-stack application for transcribing, translating, and managing subtitle files. It consists of:
- **Frontend**: Angular 17.3.12 standalone application with TypeScript and SCSS
- **Backend**: FastAPI Python server with WhisperX (transcription) and Claude/OpenAI-capable LLM backends (translation/context)
- **Backend Interfaces**: Abstract interfaces for LLM and audio models (see `backend/interface/`)
- **Backend Models**: Concrete model implementations (see `backend/models/`)
  - `backend/models/model_manager.py` is model-focused (load/config/infer), not task-result orchestration
- **Backend Routes**: Domain-specific route modules under `backend/routes/`
  - `context.py`, `transcribe.py`, `translate.py`, `file_management.py`, and `utils.py`
  - `shared.py` contains shared route helpers and singleton access
- **Backend Orchestrator**: Task execution and in-memory task state (see `backend/orchestrator/`)
  - `TaskOrchestrator`: runs one active task at a time (`is_running`)
  - `ResultHandler`: stores latest task output per task class (`task_type`)
  - `ProgressHandler`: stores progress per task class (`task_type`) for exact-task polling
  - LLM and audio interfaces now expose `get_status()` returning `"loaded" | "not_loaded" | "error"`
  - Local LLM implementation is available via llama.cpp (GGUF)
- **Backend Tests**: Isolated CLI test harnesses live under `backend/tests/`
  - `run_plan_translation_batches.py` runs the translation batch planner task directly with CLI args
- **Backend Prompts**: Prompt-generation helpers now live under `backend/prompts/`
  - Prompt functions are imported and called directly rather than through a wrapper class
  - `translate.py` contains single-line translation prompts
  - `translate_file.py` contains full-file translation prompts and translation-batch planning/splitting prompts
  - `context.py` and `recap.py` contain context-generation prompts

## Navigation

### app-navbar
**Location**: `frontend/src/app/components/navbar/`

**Purpose**: Fixed top navigation bar with page links and automatic subsection navigation.

**Features**:
- **Main navbar** (60px height): Contains brand logo and direct links to all pages (Settings, Context, Transcribe, Translate)
- **Subnav** (50px height): Automatically detects and displays subsection links for the current page
- Subsection links scroll smoothly to the corresponding section on click
- Active subsection is highlighted in purple
- Both navbars are fixed at the top with z-index layering

**Layout Impact**:
- Pages should have `padding-top: 130px` to account for both navbars (60px + 50px + 20px offset)
- Subsection links are auto-generated from `app-subsection` components on the page

**How it works**:
- Detects all `<app-subsection>` elements on the current page
- Reads the `title` attribute from each subsection
- Creates clickable links in the subnav
- Updates active state based on scroll position

---

## Reusable Frontend Components

The application uses several reusable standalone components located in `frontend/src/app/components/`. **Always use these components instead of creating duplicate markup.**

### app-subsection
**Location**: `frontend/src/app/components/subsection/`

**Purpose**: Section container with title, optional tooltip, and content area.

**When to use**: 
- Grouping related form controls or content sections
- Organizing page content into logical sections

**Usage**:
```html
<app-subsection 
  title="Section Title"
  tooltip="Optional tooltip text">
  <!-- Content goes here -->
</app-subsection>
```

**Properties**:
- `title` (required): Section title displayed in header
- `tooltip` (optional): Tooltip text shown on hover

---

### app-tooltip-icon
**Location**: `frontend/src/app/components/tooltip-icon/`

**Purpose**: Shared tooltip icon used across labels and subsection headers.

**When to use**:
- Any place you need a consistent tooltip icon

**Usage**:
```html
<app-tooltip-icon tooltip="Helpful text"></app-tooltip-icon>
```

**Properties**:
- `tooltip` (required): Tooltip text shown on hover

---

### app-file-upload
**Location**: `frontend/src/app/components/file-upload/`

**Purpose**: Drag-and-drop file upload area with file type restrictions and visual feedback.

**When to use**:
- Any file upload functionality
- Supporting drag-and-drop or click-to-browse
- Showing selected files with removal capability
- Re-selecting the same file after a state clear should still emit `filesSelected`

**Usage**:
```html
<app-file-upload
  accept=".ass,.srt"
  placeholder="Upload Subtitle File"
  subtext=".ass / .srt"
  [selectedFiles]="selectedFiles"
  (filesSelected)="onFilesSelected($event)">
</app-file-upload>
```

**Properties**:
- `accept` (optional): File type restrictions (e.g., ".ass,.srt")
- `placeholder` (required): Main text displayed in upload area
- `subtext` (optional): Additional text below placeholder
- `selectedFiles` (optional): Array of currently selected File objects
- `filesSelected` (output): Event emitted when files are selected, emits File[]

---

### app-text-field
**Location**: `frontend/src/app/components/text-field/`

**Purpose**: Reusable text area with read/write mode toggle, font size controls, copy functionality, and markdown rendering in read mode.

**When to use**:
- Any multi-line text input/display
- Displaying generated content (context, transcripts, translations)
- Text that needs both editing and viewing modes
- Replace any manual `<textarea>` with multiple controls

**Usage**:
```html
<app-text-field 
  label="Field Label"
  placeholder="Placeholder text..."
  tooltip="Optional tooltip"
  [rows]="10"
  [(ngModel)]="textValue">
</app-text-field>
```

**Properties**:
- `label` (required): Field label displayed above controls
- `placeholder` (optional): Placeholder text shown when empty
- `tooltip` (optional): Tooltip text shown next to label
- `rows` (optional, default: 8): Number of textarea rows
- `readMode` (optional, default: true): Whether the field starts in read mode
- `ngModel` (two-way binding): Text content value

**Features**:
- Toggle between Read Mode (markdown view) and Write Mode (editable textarea)
- Collapse/expand button to hide the text area when you need to save vertical space
- Font size controls (A- / A+) with range 12-24px
- Copy button with SVG icon to copy content to clipboard
- Markdown rendering in read mode (bold, italic, line breaks)
- Shows placeholder text even in read mode when empty

---

### app-context-status
**Location**: `frontend/src/app/components/context-status/`

**Purpose**: Displays status pills for context completeness (Character List, Synopsis, Summary, Recap).

**When to use**:
- Any place you want a quick visual indicator of which context fields are filled

**Usage**:
```html
<app-context-status
  [additionalInstructions]="additionalInstructions"
  [characterList]="characterList"
  [synopsis]="synopsis"
  [summary]="summary"
  [recap]="recap">
</app-context-status>
```

**Properties**:
- `additionalInstructions` (optional): string
- `characterList` (optional): string
- `synopsis` (optional): string
- `summary` (optional): string
- `recap` (optional): string

---

### app-active-subtitle-panel
**Location**: `frontend/src/app/components/active-subtitle-panel/`

**Purpose**: Sticky workspace-side panel for the single active subtitle file shared by Context and Translate workflows.

**When to use**:
- Pages that operate on the current subtitle file
- Replacing per-page subtitle upload controls
- Showing subtitle file details while users scroll through long workflow sections

**How it works**:
- Uses `app-file-upload` for `.ass` / `.srt` selection
- Stores the selected subtitle `File` in `StateService`
- Calls `ApiService.getSubtitleFileInfo()` once after selection
- Stores subtitle stats in `StateService` so the file and stats persist across route changes in the current app session
- Derives the matching saved context filename from the subtitle basename and auto-loads it from backend `context-files` when it exists
- Writes loaded context fields into global `StateService` context state so Context and Translate update from the same source

**Layout**:
- Rendered in a sticky left sidebar on Context and Translate pages
- The right column contains the page-specific workflow sections
- The panel only owns active subtitle upload and file details; context file download/delete remains in the Context page's saved context list

---

### app-loading-text-indicator
**Location**: `frontend/src/app/components/loading-text-indicator/`

**Purpose**: Animated pulsing text indicator for loading/recording states.

**When to use**:
- Any place you want a subtle pulsing text status (e.g., Recording..., Loading...)

**Usage**:
```html
<app-loading-text-indicator
  text="Recording..."
  color="#667eea"
  size="1.5rem">
</app-loading-text-indicator>
```

**Properties**:
- `text` (optional, default: "Loading..."): Display text
- `color` (optional, default: "#667eea"): Text color
- `size` (optional, default: "1.5rem"): CSS font-size value
- `weight` (optional, default: 700): Font weight

---

### app-primary-button
**Location**: `frontend/src/app/components/primary-button/`

**Purpose**: Shared primary action button (based on Translate page styling).

**When to use**:
- Primary actions like Generate / Translate / Export

**Usage**:
```html
<app-primary-button [disabled]="isBusy" [fullWidth]="true">
  Run Action
</app-primary-button>
```

**Properties**:
- `disabled` (optional, default: false): Disable the button
- `fullWidth` (optional, default: false): Stretch to container width
- `type` (optional, default: "button"): Button type

---

### app-confirm-dialog
**Location**: `frontend/src/app/components/confirm-dialog/`

**Purpose**: Shared confirmation modal rendered from the app shell for user-confirmed actions.

**When to use**:
- Confirming destructive actions like deleting files
- Confirming overwrite flows or other user decisions that should not use the browser's native `confirm(...)`

**How it works**:
- Trigger confirmations through `ConfirmationService` in `frontend/src/app/services/confirmation.service.ts`
- The dialog is rendered centrally by `AppComponent`, not manually inside individual pages
- Supports configurable title, message, confirm/cancel labels, and tone

**Usage**:
```ts
const confirmed = await this.confirmationService.confirm({
  title: 'Confirm Deletion',
  message: `Delete ${filename}? This cannot be undone.`,
  confirmLabel: 'Delete',
  cancelLabel: 'Cancel',
});
if (!confirmed) return;
```

---

### app-error-dialog
**Location**: `frontend/src/app/components/error-dialog/`

**Purpose**: Shared app-level error modal rendered from the app shell for validation failures, task-start failures, and other user-visible errors that should not use the browser's native `alert(...)`.

**When to use**:
- Showing blocking error or notice messages through app UI instead of `alert(...)`
- Surfacing shared page-level failures from services or page components

**How it works**:
- Trigger errors through `ErrorDialogService` in `frontend/src/app/services/error-dialog.service.ts`
- The dialog is rendered centrally by `AppComponent`, not manually inside individual pages
- Supports configurable title, message, and acknowledge label

**Usage**:
```ts
this.errorDialogService.show({
  title: 'Import Failed',
  message: 'Failed to import context. Invalid JSON file.',
  acknowledgeLabel: 'OK',
});
```

---

### app-progress-bar
**Location**: `frontend/src/app/components/progress-bar/`

**Purpose**: Shared progress row used by the global fixed bottom overlay for active tasks.

**When to use**:
- Showing task progress with task label, current/total, status text, and ETA metadata
- Rendered from the app shell as a fixed bottom overlay instead of inline within a single page section
- Used for all active tasks; tasks without granular backend progress use a single-step `0/1` progress model in the frontend

**Usage**:
```html
<app-progress-bar
  [taskLabel]="taskLabel"
  [current]="current"
  [total]="total"
  [statusText]="statusText"
  [etaSeconds]="etaSeconds">
</app-progress-bar>
```

**Properties**:
- `taskLabel` (optional, default: "Task"): Display label for the active task
- `current` (optional, default: 0): Current step
- `total` (optional, default: 0): Total steps
- `statusText` (optional, default: ""): Task metadata shown next to the bar
- `labelColor` (optional, default: "#5568d3"): Label text color
- `etaSeconds` (optional, default: 0): Estimated seconds remaining

---

### app-downloads-list
**Location**: `frontend/src/app/components/downloads-list/`

**Purpose**: Reusable downloads panel with search, sort, refresh, collapse, and per-file actions.

**When to use**:
- Showing downloadable files for translations, exports, or other outputs

**Usage**:
```html
<app-downloads-list
  [files]="availableDownloads"
  [isLoading]="isFetchingDownloads"
  [error]="downloadError"
  [deletingFilename]="deletingDownload"
  (refresh)="refreshDownloads()"
  (download)="downloadTranslatedFile($event)"
  (delete)="deleteTranslatedFile($event)">
</app-downloads-list>
```

**Properties**:
- `title` (optional, default: "Downloads"): Header title
- `files` (optional): Array of `{ name, size, modified }`
- `isLoading` (optional, default: false): Loading state
- `error` (optional): Error message string
- `deletingFilename` (optional): Filename currently deleting
- `collapsed` (optional, default: false): Collapse state

**Events**:
- `refresh`: Fired when refresh is clicked
- `download`: Fired with filename when download is clicked
- `delete`: Fired with filename when delete is clicked
- `collapsedChange`: Fired when collapse state changes

---

### app-waveform-player
**Location**: `frontend/src/app/components/waveform-player/`

**Purpose**: Audio waveform visualization and playback control with optional selection/trimming capability.

**When to use**:
- Displaying and playing recorded or uploaded audio files
- Allowing users to visualize and trim audio (selection mode)
- Any feature that needs audio playback with visual waveform feedback

**Usage**:
```html
<app-waveform-player
  #waveformRef
  [selectionEnabled]="true"
  [audioBlob]="audioBlob">
</app-waveform-player>
```

**Inputs**:
- `selectionEnabled` (optional, default: false): Enable audio trimming/selection mode. When true, users can click and drag to select a portion of audio
- `audioBlob` (optional): Set the audio blob to decode and display. When set, the component decodes the audio, displays the waveform, and prepares it for playback

**Public API (via ViewChild)**:
- `togglePlayback()`: Play or pause the audio
- `async getActiveBlob()`: Get the audio blob (returns selected portion if selection enabled, otherwise full blob)
- `getDecodedBuffer()`: Get the decoded AudioBuffer for advanced audio manipulation
- `clearAudio()`: Clear the waveform and stop playback
- `hasAudio` (getter): Check if audio is loaded
- `isPlaying` (public property): Current playback state (true if playing, false if paused)
- `playbackTime` (public property): Current playback position in seconds
- `playbackDuration` (public property): Total audio duration in seconds
- `formatDuration(seconds)`: Format seconds to `M:SS.MMM` string for display

**Features**:
- Canvas-based waveform rendering with device pixel ratio scaling
- Smooth 60fps playback progress indicator
- Selection/trimming with visual overlay (start and end handles when enabled)
- Automatic audio clipping to WAV format when selection is active
- Audio URL cleanup on component destroy
- Responsive to audio loading and playback state changes
- Plays audio in configured selection range only (if selection enabled)

**Internal Details**:
- Decodes audio using Web Audio API's `AudioContext.decodeAudioData()`
- Renders waveform to canvas using downsampled channel data
- Uses `requestAnimationFrame` for smooth progress line updates (60fps)
- Mouse event handling for selection drag/adjust on canvas (when enabled)
- Encodes clipped audio to WAV format using manual PCM encoding

## Backend API Structure

### Endpoints

All JSON endpoints return the shared response envelope from `backend/utils/api_response.py`:
```json
{
  "status": "success | processing | complete | idle | error | loading",
  "message": "Optional backend-authored user-facing text, or null",
  "data": {}
}
```
Use `message` for display text and `data` for structured payloads. Do not add route-specific root payload fields such as `files`, `result`, or `audio`; place those under `data`. File download endpoints still return file blobs.

**Health & Status**:
- `GET /utils/running`: Check running operations status
  - Returns `running_llm`, `running_audio`, `loading_llm_model`, and `loading_audio_model` under `data`

**Settings**:
- `POST /utils/load-audio-model`: Load audio transcription model
- `POST /utils/load-llm-model`: Load LLM model (API key optional, omit it to reuse the stored key)
- `GET /utils/settings-schema`: Get settings schema for model configuration
- `GET /utils/server-variables`: Get current server configuration and readiness grouped by provider
The server loads `.env` via python-dotenv at startup, and models read defaults from environment (e.g., `OPENAI_*`, `WHISPER_*`).
Frontend note: Settings surfaces `llm_loading_error` and `audio_loading_error` visibly so model load failures are not silent.

### Settings Schema (Backend -> Frontend)
Model backends can expose a settings schema so the frontend can render controls dynamically.
Schema shape is a dict with `provider`, `title`, and `fields`. Each field supports:
- `key`, `label`, `type`, `default`, `required`
- `options` for `select` fields as `{ "label": string, "value": string }`
- `min`, `max`, `step` for `number` fields
- `placeholder`, `help` for text inputs

Supported `type` values: `select`, `text`, `password`, `number`, `boolean`.
Audio models also expose `get_available_devices()` for device dropdown options.

### Server Variables (Backend -> Frontend)
The server variables endpoint returns provider-grouped data so the frontend can map
status cards correctly. Values are returned as display-ready objects:
```json
{
  "status": "success",
  "message": null,
  "data": {
    "audio": [{ "key": "whisper_model", "label": "Model", "value": "..." }],
    "llm": [{ "key": "openai_model", "label": "Model", "value": "..." }],
    "llm_ready": true,
    "audio_ready": true,
    "llm_loading_error": null,
    "audio_loading_error": null
  }
}
```
When no client is loaded yet, `audio` and `llm` are empty arrays (`[]`).

The running-status endpoint returns:
```json
{
  "status": "success",
  "message": null,
  "data": {
    "running_llm": false,
    "running_audio": false,
    "loading_llm_model": false,
    "loading_audio_model": false
  }
}
```

**Context Generation** (`backend/routes/context.py`):
- `POST /context/generate-character-list`: Generate character list from subtitle file
- `POST /context/generate-synopsis`: Generate synopsis from subtitle file
- `POST /context/generate-high-level-summary`: Generate summary from subtitle file
- `POST /context/generate-recap`: Generate recap from multiple contexts
- `POST /context/save`: Save a context JSON file

**Transcription** (`backend/routes/transcribe.py`):
- `POST /transcribe/transcribe-line`: Transcribe audio file or recording to text
- `POST /transcribe/transcribe-file`: Transcribe a full audio file and generate .ass subtitle file (FormData: file, language)

**Utils** (`backend/routes/utils.py`):
- `POST /utils/get-subtitle-file-info`: Upload an ASS or SRT file to get dialogue count, total characters (Speaker: dialogue), and average characters per line
  - Frontend uses `ApiService.getSubtitleFileInfo(file)` for this endpoint
- `GET /task-results/{task_type}`: Poll the latest result/progress for a specific backend task type
  - Replaces the old domain-specific `/context/result`, `/translate/result`, and `/transcribe/result` routes

**Translation** (`backend/routes/translate.py`):
- `POST /translate/translate-line`: Translate text line with context (FormData: text, context JSON, input_lang, output_lang)
- `POST /translate/translate-file`: Translate subtitle file with batch size (FormData: file, context JSON, input_lang, output_lang, batch_size)
  - file translation now runs a 3-stage backend chain: `TaskPlanTranslationBatches` -> `TaskSplitOversizedBatches` -> `TaskTranslateFile`

**File Management** (`backend/routes/file_management.py`):
- `GET /file-management/{folder}`: List files in `backend/outputs/{folder}/`
- `GET /file-management/{folder}/{filename}`: Download a file
- `DELETE /file-management/{folder}/{filename}`: Delete a file

### Backend Tasks

**TaskGenerateCharacterList** (`backend/orchestrator/task_generate_character_list.py`):
- Purpose: Generate a character reference list from an uploaded subtitle file
- Inputs:
  - `file_path`
  - `context`
  - `input_lang`
  - `output_lang`
- Output payload:
```json
{
  "type": "character_list",
  "data": "..."
}
```
- Progress: no granular backend progress

**TaskGenerateSynopsis** (`backend/orchestrator/task_generate_synopsis.py`):
- Purpose: Generate a detailed synopsis from an uploaded subtitle file
- Inputs:
  - `file_path`
  - `context`
  - `input_lang`
  - `output_lang`
- Output payload:
```json
{
  "type": "synopsis",
  "data": "..."
}
```
- Progress: no granular backend progress

**TaskGenerateSummary** (`backend/orchestrator/task_generate_summary.py`):
- Purpose: Generate a shorter high-level summary from an uploaded subtitle file
- Inputs:
  - `file_path`
  - `context`
  - `input_lang`
  - `output_lang`
- Output payload:
```json
{
  "type": "summary",
  "data": "..."
}
```
- Progress: no granular backend progress

**TaskGenerateRecap** (`backend/orchestrator/task_generate_recap.py`):
- Purpose: Merge multiple context files into a continuity recap for future translation
- Inputs:
  - `contexts`
  - `input_lang`
  - `output_lang`
- Output payload:
```json
{
  "type": "recap",
  "data": "..."
}
```
- Progress: no granular backend progress

**TaskTranscribeLine** (`backend/orchestrator/task_transcribe_line.py`):
- Purpose: Transcribe a short audio clip or recording to text
- Inputs:
  - `file_path`
  - `language`
- Output payload:
```json
{
  "type": "transcription",
  "data": "..."
}
```
- Progress: no granular backend progress

**TaskTranscribeFile** (`backend/orchestrator/task_transcribe_file.py`):
- Purpose: Transcribe a full audio file and save an `.ass` subtitle output
- Inputs:
  - `file_path`
  - `language`
  - `original_filename`
- Output payload: none. The generated file is discovered through `/file-management/transcribe-sub-files`.
- Progress: no granular backend progress

**TaskTranslateLine** (`backend/orchestrator/task_translate_line.py`):
- Purpose: Translate a single line of text with optional context
- Inputs:
  - `text`
  - `context`
  - `input_lang`
  - `output_lang`
- Output payload:
```json
{
  "type": "line_translation",
  "data": "..."
}
```
- Progress: no granular backend progress

**TaskTranslateFile** (`backend/orchestrator/task_translate_file.py`):
- Purpose: Translate a subtitle file using upstream planned batches when available, otherwise fixed-size batching, and save the translated subtitle file
- Inputs:
  - `batches`
  - `file_path`
  - `original_filename`
  - `context`
  - `input_lang`
  - `output_lang`
  - `batch_size`
- Output payload: none. The generated file is discovered through `/file-management/sub-files`.
- Progress: writes `current`, `total`, `status`, and `eta_seconds`
- Notes:
  - when `batches` are provided by upstream tasks, translation uses those planned consecutive spans instead of slicing by fixed `batch_size`
  - if no `batches` are provided, translation falls back to fixed-size batching
  - `TaskTranslateFile` owns batch selection and malformed-batch recovery logic instead of pushing planner-chain data into lower-level translation utilities
  - if a batch translation response is malformed (for example, line-count mismatch or missing delimiters), translation retries once by splitting the failed batch in half; if either half still fails, it falls back to per-line translation for that failed span
  - malformed batch recovery and per-line fallback events are logged to `backend/outputs/translator-helper.log`

**TaskPlanTranslationBatches** (`backend/orchestrator/task_plan_translation_batches.py`):
- Purpose: Stage 1 semantic planning task for subtitle translation batches
- Inputs:
  - `file_path`
  - `original_filename`
  - `context`
  - `input_lang`
  - `output_lang`
- Output payload:
```json
{
  "batches": [
    {
      "start_index": 1,
      "end_index": 42,
      "reason": "A single continuous conversation with setup and reply lines kept together."
    }
  ],
  "file_path": "...",
  "original_filename": "...",
  "context": {},
  "input_lang": "ja",
  "output_lang": "en",
  "batch_size": 50
}
```
- Progress: writes planning status and completion counts
- Notes:
  - does not enforce maximum batch size on semantic output
  - passes through the chain data needed by downstream translation tasks
  - validates contiguous, ordered, gap-free, non-overlapping coverage of the entire subtitle file
  - is wired into the file translation chain before `TaskSplitOversizedBatches` and `TaskTranslateFile`

**TaskSplitOversizedBatches** (`backend/orchestrator/task_split_oversized_batches.py`):
- Purpose: Stage 2 repair task that splits only the oversized semantic batches into smaller consecutive batches within the configured maximum size
- Inputs:
  - `file_path`
  - `original_filename`
  - `batches`
  - `context`
  - `input_lang`
  - `output_lang`
  - maximum `batch_size`
- Output payload:
```json
{
  "batches": [
    {
      "start_index": 1,
      "end_index": 42,
      "reason": "A single continuous conversation with setup and reply lines kept together."
    }
  ],
  "file_path": "...",
  "original_filename": "...",
  "context": {},
  "input_lang": "ja",
  "output_lang": "en",
  "batch_size": 50
}
```
- Progress: writes split progress while repairing oversized batches
- Notes:
  - rereads the subtitle file and independently detects which semantic batches exceed `batch_size`
  - only oversized semantic batches are reprocessed
  - final output enforces `batch_size` as a hard maximum allowed batch length
  - if the LLM returns an invalid repair split for an oversized batch, the task falls back to deterministic consecutive chunking for that span only
  - deterministic fallback events are logged to `backend/outputs/translator-helper.log`
  - does not delete the working subtitle temp file; downstream tasks or the calling harness own final cleanup

### Background Tasks

Long-running operations use FastAPI's BackgroundTasks with polling:
1. POST endpoint starts background task, returns the shared envelope with `status: "processing"` and `data.task_type`
2. Background function executes a task class through `TaskOrchestrator`
3. Each task writes final output/error to `ResultHandler` keyed by `task_type`
4. Progress-capable tasks write progress to `ProgressHandler` keyed by `task_type`
5. `GET /task-results/{task_type}` requires the exact `task_type` being polled and returns the shared envelope with `"processing"` | `"complete"` | `"error"` | `"idle"` plus task `result`/`progress` under `data`
6. Task classes write execution timing entries to a shared `backend/outputs/task-timings.log` file (no per-task log files)
Task result API payload shape:
```json
{
  "status": "complete",
  "message": null,
  "data": {
    "task_type": "TaskTranslateFile",
    "result": null,
    "progress": null
  }
}
```
Text-producing task results expose generated text as `data.result.text`; file-producing task results do not expose filenames or paths.
Additional backend warnings and fallback/audit events are written to `backend/outputs/translator-helper.log`.
Model load/unload and general backend lifecycle events are also written to `backend/outputs/translator-helper.log`.
Frontend note: polling-time task errors are surfaced visibly to the user and not only stored in frontend task state.


Translation progress (file translation) includes:
- `current`
- `total`
- `status`
- `eta_seconds`

Tasks without backend-provided granular progress use a frontend-created single-step overlay progress payload:
- `current: 0`
- `total: 1`
- task-specific `status`
- `eta_seconds: 0`

For file translations, `/task-results/TaskTranslateFile` reports status/progress only. The translated files are saved in `backend/outputs/sub-files/` and retrieved via `/file-management/sub-files`.

## Styling Guidelines

### Color Scheme
- **Primary Purple**: `#667eea` (buttons, headers, accents)
- **Primary Purple Hover**: `#5568d3`
- **Green (Mode Toggle)**: `#28a745` (read/write mode toggle)
- **Green Hover**: `#218838`
- **Border**: `#ddd`
- **Background**: White with `#f8f9fa` for read-only areas
- **Text**: `#333`

### Layout
- **Navbar**: Fixed 60px height at top, with 50px subnav below when subsections exist
- **Page Container**: Max-width 1200px, centered with `margin: 0 auto`
- **Page Padding**: `padding: 75px 20px 40px` (top accounts for navbar + subnav + offset)
- **Responsive**: None currently - desktop-focused

### Form Elements
- **Inputs/Selects**: 12px padding, 2px `#ddd` border, 8px border-radius
- **Focus**: Border color changes to `#667eea`
- **Buttons**: Purple gradient or solid purple background, white text
- **Spacing**: 20-25px between form elements

## Development Guidelines

### Code Style
- **Reduce emoji usage**: Prefer text labels or SVG icons over emojis in UI
- Use TypeScript strict mode
- Prefer standalone components over NgModules
- Use SCSS for component styling with encapsulation
- Avoid backward-compat fallbacks during refactors; update call sites instead

### Component Creation
- Always check if an existing reusable component can be used
- If creating textarea with controls, use `app-text-field`
- If creating file upload, use `app-file-upload`
- If creating sections, use `app-subsection`

### Page Layout
- Use standard page container with proper padding for navbar
- Example page structure:
```html
<div class="page-container">
  <div class="header-container">
    <h1>Page Title</h1>
  </div>
  <!-- Page content with app-subsection components -->
</div>
```
- SCSS for page container:
```scss
.page-container {
  padding: 75px 20px 40px;
  max-width: 1200px;
  margin: 0 auto;
}
```

### State Management
- Use `StateService` for cross-component state
  - `getState()`: Returns Observable with all saved context data (characterList, synopsis, summary, recap)
  - Individual getters: `getCharacterList()`, `getSynopsis()`, `getSummary()`, `getRecap()`
  - Individual setters: `setCharacterList()`, `setSynopsis()`, `setSummary()`, `setRecap()`
  - Task state is also tracked per backend task type using `getTaskState()`, `setTaskState()`, `clearTaskState()`, and `hasActiveTask()`
  - Task state shape is `taskType`, `status`, `result`, `message`, `progress`, `isPolling`
  - Active subtitle state is shared across Context and Translate via `activeSubtitleFile$`, `setActiveSubtitleFile()`, `getActiveSubtitleFile()`
  - Subtitle file details are shared through `subtitleFileInfo$`, `subtitleFileInfoLoading$`, and `subtitleFileInfoError$`
  - Task state persists across Angular route changes within the current app session, but not across a full browser refresh
- Use component-level state for local UI state
- Use `ApiService` for all backend API calls
- Use `ConfirmationService` for confirmation dialogs instead of native browser `confirm(...)`
- Use shared `LANGUAGE_OPTIONS` from `frontend/src/app/shared/language-options.ts` for page language dropdowns instead of duplicating language arrays

### API Integration
1. Add method to `ApiService` (`frontend/src/app/services/api.service.ts`)
2. Use Observables with proper typing
3. Handle errors in component with user-friendly messages
4. For long operations, implement polling

## Important Notes

### IMPORTANT: KEEP THIS DOCUMENT UPDATED
When making changes to:
- **Reusable components** (sidebar, subsection, file-upload, text-field)
- **Component APIs** (adding/removing properties, events)
- **Backend endpoints** (new routes, parameter changes)
- **Project structure** (new directories, major refactoring)

**You MUST update this `agents.md` file** to reflect those changes. This ensures future agents and developers have accurate documentation.

### Testing
- No automated tests currently implemented
- Manual testing in browser required
- Backend terminal shows FastAPI logs
- Frontend terminal shows build errors
- Backend task harnesses can be run directly from the CLI under `backend/tests/` for isolated task validation
- `backend/tests/run_plan_translation_batches.py` chains `TaskPlanTranslationBatches` and `TaskSplitOversizedBatches` through `TaskOrchestrator.run_tasks(...)`

### Current Limitations
- No user authentication
- No database (in-memory state)
- Single user at a time for transcription/context generation
- Desktop-only UI (no mobile responsiveness)

## Common Tasks

### Adding a New Page
1. Create page component in `frontend/src/app/pages/`
2. Add route in `frontend/src/app/app.routes.ts`
3. Add link in `navbar.component.html` (main navbar menu)
4. Use standard page container structure with proper padding (130px top)
5. Use `app-subsection` components for content organization (will automatically appear in subnav)

### Adding a New Text Field
Use `app-text-field` instead of creating a new textarea:
```html
<app-text-field 
  label="My Field"
  placeholder="Enter text..."
  [(ngModel)]="myValue">
</app-text-field>
```

### Adding a New Backend Endpoint
1. Add handler in the appropriate module under `backend/routes/`
2. Add method to `ApiService` in frontend
3. Call from component using the service method

### Adding a Destructive Action
1. Use `ConfirmationService` to ask the user to confirm before deleting or overwriting data
2. Do not use the browser's native `confirm(...)`
3. Keep the confirmation copy specific about what will happen (for example, deletion or overwrite)

### Showing an Error
1. Use `ErrorDialogService` to show user-visible errors or notices
2. Do not use the browser's native `alert(...)`
3. Keep the message specific about what failed and what the user should check when relevant
 
## Quick Reference

When working on this codebase:
1. Check if a reusable component exists before creating new markup
2. Follow existing code for API calls and styling
3. Match the style and structure of similar existing features
4. Update this file if you make structural changes
