# Frontend — Agent Guidelines

Angular 17.3.12 standalone application. For project-wide guidelines see the root `CLAUDE.md`. For backend conventions see `backend/CLAUDE.md`.

## Directory Layout

```
frontend/src/app/
  app.component.ts         — App shell: navbar, router-outlet, progress overlay, confirm/error dialogs
  app.routes.ts            — Route definitions
  app.config.ts            — Angular app config (HttpClient, router providers)
  pages/                   — One folder per page (home, settings, library, library/library-detail, transcribe, translate)
  components/              — Reusable standalone components (see Reusable Components section below)
  services/
    api.service.ts         — All HTTP calls to the backend; add new methods here
    state.service.ts       — Cross-component BehaviorSubject state; task state, model readiness, subtitle files
    confirmation.service.ts — Drives app-confirm-dialog; use instead of confirm(...)
    error-dialog.service.ts — Drives app-error-dialog; use instead of alert(...)
  shared/
    language-options.ts    — Shared LANGUAGE_OPTIONS array; use for all language dropdowns
```

## App Shell (AppComponent)

The app shell owns three global overlays rendered outside of any page component:
- **`app-confirm-dialog`** — driven by `ConfirmationService.dialog$`
- **`app-error-dialog`** — driven by `ErrorDialogService.dialog$`
- **Progress overlay** — shown when any task state has `status === 'processing'` and a `progress` object; displays `app-progress-bar` with the active task's label and progress

On startup `AppComponent` calls `getServerVariables()` and navigates to `/settings` if LLM or audio is not ready.

Task priority order for the progress overlay (first match wins):
`reviewTranslatedFile` → `translateFile` → `translateLine` → `transcribeFile` → `transcribeLine` → `updateLibrary`

Do not add new global overlays directly in page components — add them to `AppComponent` if they must be app-wide.

## Routes

| Path | Component |
|---|---|
| `/` | `HomeComponent` |
| `/settings` | `SettingsComponent` |
| `/library` | `LibraryComponent` |
| `/library/:seriesId` | `LibraryDetailComponent` |
| `/transcribe` | `TranscribeComponent` |
| `/translate` | `TranslateComponent` |
| `**` | redirects to `/` |

When adding a new page: create the component under `pages/`, add the route here, and add a navbar link in `navbar.component.html`.

## Services

### ApiService (`services/api.service.ts`)

Single service for all backend HTTP calls. Base URL is `http://localhost:8000`.

**Always add new backend calls here** — never call `HttpClient` directly from a component.

Key interfaces exported from this file:
- `ApiResponse<TData>` — `{ status, message, data }`
- `SeriesData`, `SeriesCharacter`, `SeriesGlossaryTerm`, `SeriesSummary`
- `LibraryProposals`, `SubtitleFileInfoData`, `FileListData`
- `RunningStatusData`, `ServerVariablesData`
- `TaskStartData`, `TaskResultData`, `TaskResultResponse`

**FormData pattern** — all file uploads and task-start calls use `FormData`:
```ts
const formData = new FormData();
formData.append('file', file);
formData.append('series_id', seriesId);
return this.http.post<ApiResponse<TaskStartData>>(`${this.baseUrl}/translate/translate-file`, formData);
```

**Polling** — use `apiService.getTaskResult(taskType)` which calls `GET /task-results/{task_type}`.

### StateService (`services/state.service.ts`)

BehaviorSubject-based cross-component state. Task state persists across route changes but not browser refresh.

**TASK_TYPES constant** — maps friendly names to backend task type strings:
```ts
TASK_TYPES.updateLibrary        // 'TaskDeduplicateProposals'  (final task in library chain)
TASK_TYPES.translateLine        // 'TaskTranslateLine'
TASK_TYPES.translateFile        // 'TaskTranslateFile'
TASK_TYPES.reviewTranslatedFile // 'TaskRetranslateReviewedLines'
TASK_TYPES.transcribeLine       // 'TaskTranscribeLine'
TASK_TYPES.transcribeFile       // 'TaskTranscribeFile'
```
Always use `TASK_TYPES.*` — never hardcode task type strings in components.

**Task state API**:
```ts
stateService.getTaskState(taskType)              // returns StoredTaskState (idle default if not set)
stateService.setTaskState(taskType, patch)       // partial update, returns new state
stateService.clearTaskState(taskType)
stateService.hasActiveTask(taskTypes?)           // true if any (or listed) tasks are processing
```

**StoredTaskState shape**: `{ taskType, status: TaskStatus, result, message, progress, isPolling }`

**Shared file state** (cross-page, Library ↔ Translate):
- `activeSubtitleFile$` / `setActiveSubtitleFile()` / `getActiveSubtitleFile()`
- `activeTranslatedSubtitleFile$` / `setActiveTranslatedSubtitleFile()` / `getActiveTranslatedSubtitleFile()`
- `subtitleFileInfo$` / `subtitleFileInfoLoading$` / `subtitleFileInfoError$` (and setters)
- `translatedSubtitleFileInfo$` / `translatedSubtitleFileInfoLoading$` / `translatedSubtitleFileInfoError$` (and setters)
- `selectedSeriesId$` / `setSelectedSeriesId()` / `getSelectedSeriesId()`

**Model readiness**:
- `llmReady$`, `audioReady$`, `searchReady$` — `boolean | null` (null = unknown)
- `loadingAudio$`, `loadingLlm$`
- `isReady$` — true only when both LLM and audio are ready

### ConfirmationService (`services/confirmation.service.ts`)

```ts
const confirmed = await this.confirmationService.confirm({
  title: 'Confirm Deletion',
  message: `Delete ${filename}? This cannot be undone.`,
  confirmLabel: 'Delete',
  cancelLabel: 'Cancel',
});
if (!confirmed) return;
```

Never use `confirm(...)`. The dialog is rendered by `AppComponent`, not the calling page.

### ErrorDialogService (`services/error-dialog.service.ts`)

```ts
this.errorDialogService.show({
  title: 'Import Failed',
  message: 'Failed to import context. Invalid JSON file.',
  acknowledgeLabel: 'OK',
});
```

Never use `alert(...)`. Every `error:` callback in an Observable subscription must call this — an empty `error: () => {}` is never acceptable.

## Polling Pattern

Long-running backend tasks use a start → poll loop:

```ts
// 1. Start task
this.apiService.translateFile(...).subscribe({
  next: (response) => {
    this.stateService.setTaskState(taskType, { status: 'processing', isPolling: true });
    this.pollTaskResult(taskType);
  },
  error: () => this.errorDialogService.show({ title: '...', message: '...' })
});

// 2. Poll
private pollTaskResult(taskType: string): void {
  this.apiService.getTaskResult(taskType).subscribe({
    next: (response) => {
      if (response.status === 'processing') {
        this.stateService.setTaskState(taskType, { progress: response.data?.progress ?? null });
        setTimeout(() => this.pollTaskResult(taskType), 1000);
      } else if (response.status === 'complete') {
        this.stateService.setTaskState(taskType, { status: 'complete', result: response.data?.result ?? null, isPolling: false });
      } else if (response.status === 'error') {
        this.stateService.setTaskState(taskType, { status: 'error', message: response.message, isPolling: false });
        this.errorDialogService.show({ title: 'Task Failed', message: response.message ?? 'Unknown error' });
      }
    },
    error: () => {
      this.stateService.setTaskState(taskType, { status: 'error', isPolling: false });
      this.errorDialogService.show({ title: 'Polling Failed', message: 'Lost connection to backend.' });
    }
  });
}
```

Always poll the **final task** in a chain using `TASK_TYPES.*`. Surface polling-time errors to the user via `errorDialogService` — never swallow them.

---

## Reusable Components

Always use these components instead of creating duplicate markup. They live in `frontend/src/app/components/`.

### app-navbar
**Location**: `frontend/src/app/components/navbar/`

Fixed top navigation bar (60px height) with brand logo and direct links to all pages. Fixed with z-index 100.

Pages use the global `.page-container` class which sets `padding-top: 80px`. Defined in `frontend/src/styles.scss` — do not duplicate in page SCSS.

---

### app-subsection
**Location**: `frontend/src/app/components/subsection/`

Section container with title, optional tooltip, and content area.

```html
<app-subsection title="Section Title" tooltip="Optional tooltip">
  <!-- Content goes here -->
</app-subsection>
```

- `title` (required): Section title
- `tooltip` (optional): Tooltip text on hover

---

### app-tooltip-icon
**Location**: `frontend/src/app/components/tooltip-icon/`

```html
<app-tooltip-icon tooltip="Helpful text"></app-tooltip-icon>
```

---

### app-file-upload
**Location**: `frontend/src/app/components/file-upload/`

Drag-and-drop file upload with file type restrictions and visual feedback. Re-selecting the same file after a state clear must still emit `filesSelected`.

```html
<app-file-upload
  accept=".ass,.srt"
  placeholder="Upload Subtitle File"
  subtext=".ass / .srt"
  [selectedFiles]="selectedFiles"
  (filesSelected)="onFilesSelected($event)">
</app-file-upload>
```

- `accept` (optional): File type restrictions
- `placeholder` (required): Main text in upload area
- `subtext` (optional): Secondary text below placeholder
- `selectedFiles` (optional): Array of currently selected File objects
- `filesSelected` (output): Emits File[] when files are selected

---

### app-text-field
**Location**: `frontend/src/app/components/text-field/`

Multi-line text area with read/write mode toggle, font size controls, copy button, and markdown rendering. Use instead of a raw `<textarea>`.

```html
<app-text-field
  label="Field Label"
  placeholder="Placeholder text..."
  tooltip="Optional tooltip"
  [rows]="10"
  [(ngModel)]="textValue">
</app-text-field>
```

- `label` (required): Field label
- `placeholder` (optional): Placeholder text
- `tooltip` (optional): Tooltip text
- `rows` (optional, default: 8): Number of textarea rows
- `readMode` (optional, default: true): Start in read mode
- `ngModel` (two-way binding): Text content

---

### app-tabs / app-tab
**Location**: `frontend/src/app/components/tabs/`

Pill-style tab container. Use instead of hand-rolled tab buttons or `*ngIf` visibility switching.

```html
<app-tabs>
  <app-tab label="Tab One">
    <app-subsection title="Tab One"><!-- content --></app-subsection>
  </app-tab>
  <app-tab label="Tab Two">
    <app-subsection title="Tab Two"><!-- content --></app-subsection>
  </app-tab>
</app-tabs>
```

- `TabComponent` uses `[hidden]` on its host — tab state is preserved (no DOM teardown unlike `*ngIf`)
- Both `TabsComponent` and `TabComponent` must be in the page component's `imports` array
- Can be nested: use `app-subsection` inside `app-tab` for top-level tabs; omit it for inner sub-tab switchers

---

### app-loading-text-indicator
**Location**: `frontend/src/app/components/loading-text-indicator/`

Animated pulsing text for loading/recording states.

```html
<app-loading-text-indicator text="Recording..." color="#667eea" size="1.5rem">
</app-loading-text-indicator>
```

- `text` (default: "Loading..."), `color` (default: "#667eea"), `size` (default: "1.5rem"), `weight` (default: 700)

---

### app-primary-button
**Location**: `frontend/src/app/components/primary-button/`

```html
<app-primary-button [disabled]="isBusy" [fullWidth]="true">Run Action</app-primary-button>
```

- `disabled` (default: false), `fullWidth` (default: false), `type` (default: "button")

---

### app-confirm-dialog
**Location**: `frontend/src/app/components/confirm-dialog/`

Confirmation modal rendered from the app shell. Use instead of `confirm(...)`.

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

App-level error modal rendered from the app shell. Use instead of `alert(...)`.

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

Progress row for the global fixed-bottom task overlay. Tasks without granular backend progress use `current: 0, total: 1` as a single-step frontend model.

```html
<app-progress-bar
  [taskLabel]="taskLabel"
  [current]="current"
  [total]="total"
  [statusText]="statusText"
  [etaSeconds]="etaSeconds">
</app-progress-bar>
```

---

### app-downloads-list
**Location**: `frontend/src/app/components/downloads-list/`

Downloads panel with search, sort, pagination, refresh, collapse, and per-file actions. Defaults to sorting by date descending (most recently modified first).

```html
<app-downloads-list
  [files]="section.files"
  [isLoading]="section.isLoading"
  [error]="section.error"
  [deletingFilename]="section.deletingFilename"
  (refresh)="refreshDownloadSection(section)"
  (download)="downloadFile(section, $event)"
  (delete)="deleteFile(section, $event)">
</app-downloads-list>
```

- `title` (default: "Downloads"), `files`, `isLoading`, `error`, `deletingFilename`, `collapsed`, `pageSize` (default: 7)
- Events: `refresh`, `download` (filename), `delete` (filename), `collapsedChange`
- For pages with multiple distinct file categories (e.g. translate page's Translated/Reviewed downloads), model each category as a small state object (`{ folder, title, tooltip, files, isLoading, error, deletingFilename }`) in a `downloadSections`-style array, wrap each in its own `app-subsection`, and use `*ngFor` with generic section-parameterized handler methods — do not duplicate fields/methods per category. `ApiService.listFiles/getFileBlob/deleteFile` accept a `folder` string that may contain `/` for nested output subdirectories (e.g. `sub-files/translated`), sent as a query parameter, not a URL path segment.

---

### app-waveform-player
**Location**: `frontend/src/app/components/waveform-player/`

Canvas-based audio waveform with playback and optional selection/trimming.

```html
<app-waveform-player #waveformRef [selectionEnabled]="true" [audioBlob]="audioBlob">
</app-waveform-player>
```

**Inputs**: `selectionEnabled` (default: false), `audioBlob`

**Public API (via ViewChild)**:
- `togglePlayback()`, `async getActiveBlob()`, `getDecodedBuffer()`, `clearAudio()`
- `hasAudio` (getter), `isPlaying`, `playbackTime`, `playbackDuration`, `formatDuration(seconds)`

---

## Styling Guidelines

### Color Scheme
- **Primary Purple**: `#667eea` — buttons, headers, accents
- **Primary Purple Hover**: `#5568d3`
- **Green (Mode Toggle)**: `#28a745` / hover `#218838`
- **Border**: `#ddd`
- **Background**: white / `#f8f9fa` for read-only areas
- **Text**: `#333`

### Layout
- **Navbar**: Fixed 60px height at top
- **Page Container**: Max-width 1400px, centered — defined globally in `frontend/src/styles.scss`, never duplicate in page SCSS
- **Page Padding**: `padding: 80px 20px 40px`
- **Responsive**: Desktop-only, no mobile

### Form Elements
- Inputs/Selects: 12px padding, `2px solid #ddd` border, 8px border-radius
- Focus: border changes to `#667eea`
- Buttons: purple gradient or solid purple, white text
- Spacing: 20–25px between form elements

### Page Layout Template
```html
<div class="page-container">
  <div class="header-container"><h1>Page Title</h1></div>
  <div class="form-section">
    <!-- app-tabs > app-tab > app-subsection -->
  </div>
</div>
```
No per-page SCSS needed for `.page-container`.

---

## Development Guidelines

### Code Style
- TypeScript strict mode; prefer standalone Angular components over NgModules
- SCSS with component encapsulation
- Reduce emoji usage — prefer text labels or SVG icons
- No backward-compat shims; update call sites directly

### Errors
- Use `ErrorDialogService` instead of `alert(...)`
- Never swallow errors silently — every `error:` callback in an Observable subscription must show the error dialog

### Destructive Actions
- Use `ConfirmationService` before deleting or overwriting
- Keep confirmation copy specific about what will be deleted/overwritten

### Editable Lists (personality, history, relationships)
- Use `.list-entry` for every row — one class for all list types
- Each row: full-width `<input>` with `2px solid #ddd` border + delete button
- Delete: `<div class="btn-danger"><app-primary-button>Delete</app-primary-button></div>` — never custom ✕ buttons or `.btn-remove`
- No outer border on `.list-entry` itself

### Shared Utilities
- **`LANGUAGE_OPTIONS`** (`shared/language-options.ts`): Use for all language dropdowns — never duplicate the list in a component
- **`TASK_TYPES`** (`services/state.service.ts`): Use for all task type references — never hardcode backend task type strings

---

## Adding a New Page
1. Create component in `frontend/src/app/pages/`
2. Add route in `frontend/src/app/app.routes.ts`
3. Add link in `navbar.component.html`
4. Use `<div class="page-container">` — no per-page SCSS needed
5. Use `app-subsection` for sections, `app-tabs` to group them

## Adding a New Backend Endpoint
1. Add handler in the appropriate module under `backend/routes/`
2. Add method to `ApiService` in frontend
3. Call from component via the service
