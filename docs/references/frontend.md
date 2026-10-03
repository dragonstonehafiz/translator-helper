# Frontend

## Purpose

Angular 17.3 standalone app in `frontend/`: layout, app shell, routes, services and state, the polling pattern, shared components, and styling. Backend contracts live in [`api.md`](api.md).

## Contents

- [Layout](#layout)
- [App shell](#app-shell)
- [Routes and pages](#routes-and-pages)
- [Services](#services)
  - [ApiService](#apiservice)
  - [StateService](#stateservice)
  - [ConfirmationService and ErrorDialogService](#confirmationservice-and-errordialogservice)
- [Polling pattern](#polling-pattern)
- [Shared components](#shared-components)
- [Styling](#styling)
- [Editable lists](#editable-lists)

## Layout

```
frontend/src/
  styles.scss                 Global styles and layout/form classes
  app/
    app.component.ts          App shell: navbar, router-outlet, progress overlay, confirm/error dialogs
    app.routes.ts             Route definitions
    app.config.ts             Providers (HttpClient, router)
    pages/                    One folder per page: home, settings, library (+ library/library-detail), transcribe, translate
    components/               Reusable standalone components
    services/                 api, state, confirmation, error-dialog
    shared/language-options.ts  LANGUAGE_OPTIONS for every language dropdown
```

The project was generated with Angular SSR (`server.ts`, `main.server.ts`, `app.config.server.ts`), but the app is used through `ng serve`. TypeScript runs in `strict` mode with `strictTemplates`.

## App shell

`AppComponent` renders three global overlays outside any page:

- `app-confirm-dialog`, driven by `ConfirmationService.dialog$`.
- `app-error-dialog`, driven by `ErrorDialogService.dialog$`.
- The progress overlay. It appears when a task state has `status === 'processing'` and a `progress` object, and shows `app-progress-bar` for the first matching task in this priority order: `reviewTranslatedFile` → `translateFile` → `translateLine` → `transcribeFile` → `transcribeLine` → `updateLibrary`.

On startup it calls `getServerVariables()` and navigates to `/settings` if the LLM or audio model isn't ready.

Add app-wide overlays to `AppComponent`, never to a page.

## Routes and pages

| Path | Component | Purpose |
|---|---|---|
| `/` | `HomeComponent` | Landing page |
| `/settings` | `SettingsComponent` | Model status; audio/LLM/search forms rendered from `/utils/settings-schema` by field type, with no field names hardcoded; reload models |
| `/library` | `LibraryComponent` | Series list; create series |
| `/library/:seriesId` | `LibraryDetailComponent` | Series metadata, characters, glossary; run library update and accept/reject proposals |
| `/transcribe` | `TranscribeComponent` | Record/transcribe a line; transcribe an audio file; downloads |
| `/translate` | `TranslateComponent` | Translate a line; translate a file; review a translated file; downloads |
| `**` | — | Redirects to `/` |

## Services

### ApiService

`services/api.service.ts` holds every backend HTTP call. The base URL `http://localhost:8000` is hardcoded. Always add new calls here; never inject `HttpClient` into a component.

- It exports the response and payload interfaces: `ApiResponse<TData>`, `SeriesData`, `SeriesCharacter`, `SeriesGlossaryTerm`, `SeriesSummary`, `LibraryProposals`, `SubtitleFileInfoData`, `FileListData`, `RunningStatusData`, `ServerVariablesData`, `TaskStartData`, `TaskResultData` and `TaskResultResponse`.
- File uploads and task starts send `FormData`. Library CRUD and model loading send JSON.
- `getTaskResult(taskType)` calls `GET /task-results/{task_type}`.
- `listFiles`, `getFileBlob` and `deleteFile` take a `folder` (`translated`, `reviewed`, `transcribed`), sent as a query parameter.

### StateService

`services/state.service.ts` holds cross-component state in BehaviorSubjects. It survives route changes but not a browser refresh.

`TASK_TYPES` maps friendly names to each chain's final backend task type. Always use it instead of hardcoding the strings:

```ts
TASK_TYPES.updateLibrary        // 'TaskDeduplicateProposals'
TASK_TYPES.translateLine        // 'TaskTranslateLine'
TASK_TYPES.translateFile        // 'TaskTranslateFile'
TASK_TYPES.reviewTranslatedFile // 'TaskRetranslateReviewedLines'
TASK_TYPES.transcribeLine       // 'TaskTranscribeLine'
TASK_TYPES.transcribeFile       // 'TaskTranscribeFile'
```

Task state API:

- `getTaskState(taskType)` returns a `StoredTaskState`, or an idle default.
- `setTaskState(taskType, patch)` applies a partial update.
- `clearTaskState(taskType)`.
- `hasActiveTask(taskTypes?)`.
- `StoredTaskState` is `{ taskType, status, result, message, progress, isPolling }`.

Shared file state, used by both the Library and Translate pages:

- `activeSubtitleFile$`, `activeTranslatedSubtitleFile$`
- `subtitleFileInfo$` / `...Loading$` / `...Error$`, and the translated equivalents
- `selectedSeriesId$`

Each comes with get/set methods.

Model readiness: `llmReady$`, `audioReady$`, `searchReady$` (`boolean | null`, where `null` means unknown), `loadingAudio$`, `loadingLlm$`, and `isReady$`, which is true only when both the LLM and audio are ready.

### ConfirmationService and ErrorDialogService

```ts
const confirmed = await this.confirmationService.confirm({
  title: 'Confirm Deletion',
  message: `Delete ${filename}? This cannot be undone.`,
  confirmLabel: 'Delete',
  cancelLabel: 'Cancel',
});
if (!confirmed) return;

this.errorDialogService.show({ title: 'Import Failed', message: '...', acknowledgeLabel: 'OK' });
```

- Never use `confirm(...)` or `alert(...)`.
- Confirm before deleting or overwriting anything, and say exactly what will be lost.
- Every `error:` callback in a subscription shows the error dialog. An empty `error: () => {}` is never acceptable.

## Polling pattern

```ts
// 1. Start
this.apiService.translateFile(...).subscribe({
  next: () => {
    this.stateService.setTaskState(taskType, { status: 'processing', isPolling: true });
    this.pollTaskResult(taskType);
  },
  error: () => this.errorDialogService.show({ title: '...', message: '...' }),
});

// 2. Poll every second until complete or error
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
    },
  });
}
```

Always poll the chain's **final** task through `TASK_TYPES.*` (see [`tasks.md`](tasks.md#polling)).

## Shared components

All of these live in `src/app/components/<name>/`. Use them instead of duplicating their markup.

| Selector | Use | Key inputs / outputs |
|---|---|---|
| `app-navbar` | Fixed 60px top bar (z-index 100) with links to every page | — |
| `app-subsection` | Titled section container | `title` (required), `tooltip` |
| `app-tooltip-icon` | Hover tooltip icon | `tooltip` |
| `app-tabs` / `app-tab` | Pill tabs; use instead of hand-rolled tab buttons or `*ngIf` switching | `app-tab label` |
| `app-file-upload` | Drag-and-drop upload. Re-selecting the same file after a state clear must still emit | `accept`, `placeholder` (required), `subtext`, `selectedFiles`; `(filesSelected)` → `File[]` |
| `app-text-field` | Multi-line text with read/write toggle, font size, copy and markdown rendering; use instead of a raw `<textarea>` | `label` (required), `placeholder`, `tooltip`, `rows` (8), `readMode` (true), `[(ngModel)]` |
| `app-primary-button` | Main action button | `disabled`, `fullWidth`, `type` (`button`), `variant` (`primary` \| `danger`) |
| `app-secondary-button` | Bordered secondary/cancel button | `disabled`, `type` |
| `app-loading-text-indicator` | Pulsing loading/recording text | `text`, `color`, `size`, `weight` |
| `app-progress-bar` | Row in the global progress overlay | `taskLabel`, `current`, `total`, `statusText`, `etaSeconds` |
| `app-downloads-list` | Files panel with search, sort (newest first), pagination, refresh, collapse, download and delete | `title`, `files`, `isLoading`, `error`, `deletingFilename`, `collapsed`, `pageSize` (7); `(refresh)`, `(download)`, `(delete)`, `(collapsedChange)` |
| `app-waveform-player` | Canvas waveform with playback and optional selection/trim | `selectionEnabled`, `audioBlob`. Via `ViewChild`: `togglePlayback()`, `getActiveBlob()`, `getDecodedBuffer()`, `clearAudio()`, `hasAudio`, `isPlaying`, `playbackTime`, `playbackDuration` |
| `app-confirm-dialog`, `app-error-dialog` | Rendered only by `AppComponent`; drive them through their services | — |
| `app-context-status` | Shows which context fields are filled. Currently not rendered anywhere | `characterList`, `synopsis`, `summary`, `additionalInstructions` |

Usage notes:

- **Tabs.**
  - `app-tab` uses `[hidden]`, so tab state survives switching.
  - Put both `TabsComponent` and `TabComponent` in the page's `imports`.
  - Tabs can nest: use `app-tab > app-subsection` for top-level tabs, and leave out the subsection for inner sub-tab switchers.
- **Several download categories on one page** (e.g. Translated and Reviewed on Translate).
  - Model each category as a state object `{ folder, title, tooltip, files, isLoading, error, deletingFilename }` in an array, and render it with `*ngFor`, each in its own `app-subsection`.
  - Use generic section-parameterized handlers. Don't duplicate fields or methods per category.

## Styling

Global classes in `src/styles.scss` are defined once. Never redefine them in a page's `.scss`; only add page-specific overrides on top of them.

- `.page-container` sets `padding: 80px 20px 40px` and `max-width: 1400px`, centered. Pages need no SCSS of their own for it.
- `.header-container` is a centered flex row that styles a nested `h1`.
- `.form-section` is a flex column with a 24px gap. Use the `.form-section--loose` modifier (40px gap) for pages with few large subsections, currently Settings.
- `.form-row` is a flex row with a 20px gap, for side-by-side `.form-group`s.
- `.form-group` is a flex column with an 8px gap. It styles `label`, `input`, `select` and `textarea`.
- `.empty-state` and `.loading-row` are centered placeholders.

Page template:

```html
<div class="page-container">
  <div class="header-container"><h1>Page Title</h1></div>
  <div class="form-section">
    <!-- app-tabs > app-tab > app-subsection -->
  </div>
</div>
```

Colors:

| Use | Colors |
|---|---|
| Primary purple | `#667eea`, hover `#5568d3` |
| Mode-toggle green | `#28a745`, hover `#218838` |
| Border | `#ddd` |
| Background | White; `#f8f9fa` for read-only areas |
| Text | `#333` |

Inputs and selects have 12px padding, a `2px solid #ddd` border and 8px radius, and a `#667eea` border on focus. The UI is desktop-only.

## Editable lists

These rules cover personality, history and relationships on `library-detail`.

- Use `.list-entry` for every row inside a `.list-entries` container, **including the trailing "add new" row**, so all rows share the same spacing and input styling.
- Each row is a full-width `<input>` plus a trailing button: `<app-primary-button variant="danger">Delete</app-primary-button>` on existing rows and `Add` on the trailing row. Never use custom ✕ buttons or `.btn-remove`.
- `.list-entry` has no outer border.
- Two-input rows, such as a relationship's character and detail, use `.list-entry.two-input`.
- Personality, Relationships and History are nested `app-tabs` inside both the character add/edit form and the read-only card body.
