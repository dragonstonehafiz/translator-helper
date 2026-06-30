# Translator Helper - Agent Guidelines

Translator Helper is a full-stack application for transcribing, translating, and managing subtitle files.

- **Frontend**: Angular 17.3.12 standalone application with TypeScript and SCSS (`frontend/`)
- **Backend**: FastAPI Python server with WhisperX transcription and Claude/OpenAI/DeepSeek LLM backends (`backend/`)

For backend-specific conventions, task patterns, chain wiring, library storage, and API structure see:
@backend/CLAUDE.md

For frontend-specific conventions, services, polling pattern, component rules, and styling see:
@frontend/CLAUDE.md

---

## Testing
- No automated tests currently implemented — manual browser testing only
- The user normally keeps both frontend and backend running; do not start either server unless explicitly asked
- Backend task harnesses for isolated CLI validation live under `backend/tests/`

## Current Limitations
- No user authentication
- No database (in-memory state, lost on server restart)
- Single user at a time for transcription/translation
- Desktop-only UI

## IMPORTANT: Keep Docs Updated
When making structural changes — new components, new routes, new tasks, changed APIs — update the relevant CLAUDE.md file (`backend/CLAUDE.md` for backend changes, `frontend/CLAUDE.md` for frontend changes). This is how future agents stay accurate.
