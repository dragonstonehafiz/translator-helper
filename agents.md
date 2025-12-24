# Translator Helper - Agent Guidelines

This document provides guidelines for AI agents working on the Translator Helper project. It describes the project structure, reusable components, and best practices.

## Project Overview

Translator Helper is a full-stack application for transcribing, translating, and managing subtitle files. It consists of:
- **Frontend**: Angular 17.3.12 standalone application with TypeScript and SCSS
- **Backend**: FastAPI Python server with Whisper (transcription), OpenAI (translation/context), and Tavily (web search)

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

**Purpose**: Collapsible section container with title, optional tooltip, and content area.

**When to use**: 
- Grouping related form controls or content sections
- Any section that should be collapsible
- Organizing page content into logical sections

**Usage**:
```html
<app-subsection 
  title="Section Title"
  [collapsed]="sectionCollapsed"
  tooltip="Optional tooltip text">
  <!-- Content goes here -->
</app-subsection>
```

**Properties**:
- `title` (required): Section title displayed in header
- `collapsed` (optional, default: false): Two-way binding for collapsed state
- `tooltip` (optional): Tooltip text shown on hover

---

### app-file-upload
**Location**: `frontend/src/app/components/file-upload/`

**Purpose**: Drag-and-drop file upload area with file type restrictions and visual feedback.

**When to use**:
- Any file upload functionality
- Supporting drag-and-drop or click-to-browse
- Showing selected files with removal capability

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
- `ngModel` (two-way binding): Text content value

**Features**:
- Toggle between Read Mode (markdown view) and Write Mode (editable textarea)
- Font size controls (A- / A+) with range 12-24px
- Copy button with SVG icon to copy content to clipboard
- Markdown rendering in read mode (bold, italic, line breaks)
- Shows placeholder text even in read mode when empty

---

## Backend API Structure

### Endpoints

**Health & Status**:
- `GET /api/health`: Health check
- `GET /api/ready`: Check if models/APIs are loaded
- `GET /api/running`: Check running operations status

**Settings**:
- `GET /api/devices`: Get available compute devices
- `POST /api/load-whisper-model`: Load Whisper transcription model
- `POST /api/load-gpt-model`: Load OpenAI GPT model
- `POST /api/load-tavily-api`: Load Tavily search API
- `GET /api/server/variables`: Get current server configuration

**Context Generation** (`business/context.py`):
- `POST /api/context/generate-web-context`: Generate web-based context
- `POST /api/context/generate-character-list`: Generate character list from subtitle file
- `POST /api/context/generate-synopsis`: Generate synopsis from subtitle file
- `POST /api/context/generate-high-level-summary`: Generate summary from subtitle file
- `POST /api/context/generate-recap`: Generate recap from multiple contexts
- `GET /api/context/result`: Poll for context generation result

**Transcription** (`business/transcribe.py`):
- `POST /api/transcribe/transcribe-line`: Transcribe audio file
- `POST /api/transcribe/get-file-info/`: Upload an ASS or SRT file to get dialogue count, total characters (Speaker: dialogue), and average characters per line
- `GET /api/transcribe/result`: Poll for transcription result

**Translation** (`business/translate.py`):
- `POST /api/translate/translate-line`: Translate text line with context (FormData: text, context JSON, input_lang, output_lang)
- `POST /api/translate/translate-file`: Translate subtitle file with context window (FormData: file, context JSON, input_lang, output_lang, context_window)
- `GET /api/translate/result`: Poll for translation result

### Background Tasks

Long-running operations use FastAPI's BackgroundTasks with polling:
1. POST endpoint starts background task, returns `{"status": "processing"}`
2. Background function sets `running_X = True`, performs operation, stores result in `X_result`, sets `running_X = False`
3. GET `/result` endpoint polls for completion: `"processing"` | `"complete"` | `"error"` | `"idle"`

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
- **Page Padding**: `padding: 130px 20px 40px` (top accounts for navbar + subnav + offset)
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
  padding: 130px 20px 40px;
  max-width: 1200px;
  margin: 0 auto;
}
```

### State Management
- Use `StateService` for cross-component state
  - `getState()`: Returns Observable with all saved context data (webContext, characterList, synopsis, summary, recap)
  - Individual getters: `getWebContext()`, `getCharacterList()`, `getSynopsis()`, `getSummary()`, `getRecap()`
  - Individual setters: `setWebContext()`, `setCharacterList()`, etc.
- Use component-level state for local UI state
- Use `ApiService` for all backend API calls

### API Integration
1. Add method to `ApiService` (`frontend/src/app/services/api.service.ts`)
2. Use Observables with proper typing
3. Handle errors in component with user-friendly messages
4. For long operations, implement polling

## Important Notes

### **⚠️ KEEP THIS DOCUMENT UPDATED**
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

### Current Limitations
- No user authentication
- No database (in-memory state)
- Single user at a time for transcription/context generation
- Desktop-only UI (no mobile responsiveness)

## File Structure

```
translator-helper/
├── backend/
│   ├── server.py              # FastAPI application
│   ├── settings.py            # Environment configuration
│   ├── business/              # Business logic
│   │   ├── context.py         # Context generation
│   │   ├── transcribe.py      # Audio transcription
│   │   └── translate.py       # Translation with context
│   └── utils/                 # Utilities
│       ├── config.py
│       ├── load_models.py
│       └── utils.py
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/    # Reusable components (described above)
│   │   │   ├── pages/         # Page components
│   │   │   │   ├── context/
│   │   │   │   ├── home/
│   │   │   │   ├── settings/
│   │   │   │   ├── transcribe/
│   │   │   │   └── translate/
│   │   │   └── services/      # Angular services
│   │   └── assets/
└── data/                      # Sample subtitle files
```

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
1. Add function in appropriate `business/` module
2. Create endpoint in `server.py`
3. Add method to `ApiService` in frontend
4. Call from component using the service method

## Quick Reference

When working on this codebase:
1. Check if a reusable component exists before creating new markup
2. Follow existing code for API calls and styling
3. Match the style and structure of similar existing features
4. Update this file if you make structural changes
