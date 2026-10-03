# AGENTS.md

Translator Helper — subtitle transcription, translation, and translation-review app. FastAPI backend (WhisperX transcription, DeepSeek/Claude/OpenAI/llama.cpp LLM backends, Tavily web search) + Angular 17 standalone frontend. No database: series library and outputs are JSON/files under `backend/outputs/`, task state is in memory.

Read [`docs/repository-rules.md`](docs/repository-rules.md) first — it holds the coding rules, verification expectations, and safety/permission boundaries that apply to virtually every task.

The user normally keeps both the backend and frontend running; do not start either server unless asked.

## Repository workflow

- Implementation planning: [`docs/programming-workflow/implementation-planning.md`](docs/programming-workflow/implementation-planning.md).
- Issue drafting: [`docs/github-workflow/issue-authoring.md`](docs/github-workflow/issue-authoring.md).
- Pull request drafting: [`docs/github-workflow/pull-request-authoring.md`](docs/github-workflow/pull-request-authoring.md).
- Commit message drafting: [`docs/github-workflow/commit-message-authoring.md`](docs/github-workflow/commit-message-authoring.md).
- Documentation writing and maintenance: [`docs/documentation-workflow/documentation-maintenance.md`](docs/documentation-workflow/documentation-maintenance.md).
- Codebase discovery (architecture, API, task chains, frontend references): [`docs/README.md`](docs/README.md).
- Verification commands: [`docs/references/verification.md`](docs/references/verification.md).
