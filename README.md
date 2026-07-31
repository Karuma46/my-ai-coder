# My AI Coder

My AI Coder is a full-stack roadmap and release-management application for
organizing projects, versions, and GitHub-aligned todos. It combines a React
dashboard with a FastAPI service that can coordinate local coding agents,
pull-request workflows, releases, and real-time run notifications.

## Features

- Account registration, sign-in, and guided company/project onboarding
- Company, account, and project settings
- Project roadmaps with version and WIP todo management
- Todo status, assignment, agent-run, pull-request, and merge workflows
- Version readiness, completion, preview, and release workflows
- Real-time agent-run alerts over WebSockets
- Optional GitHub MCP integration with explicit write, merge, and release gates
- Optional Celery worker for automatically processing planned todos

## Repository layout

| Path | Purpose |
| --- | --- |
| [`web/`](web/) | Vite, React, TypeScript, React Aria, and Tailwind frontend |
| [`api/`](api/) | FastAPI, async SQLAlchemy, SQLite, Celery, and MCP backend |
| [`web/api-contract.json`](web/api-contract.json) | API and WebSocket contract used by the frontend |

## Technology

**Frontend:** React 19, TypeScript, Vite, React Router, React Aria Components,
Tailwind CSS, Axios, and Lucide.

**Backend:** Python 3.11+, FastAPI, SQLAlchemy, SQLite, Celery, Redis, FastMCP,
PyJWT, and Argon2.

## Prerequisites

For the basic application:

- Node.js with npm
- Python 3.11 or newer

For agent automation and GitHub operations:

- Docker with Docker Compose
- Redis (provided by the Compose configuration)
- A supported local coding-agent CLI, such as Codex or Claude
- A fine-grained GitHub personal access token

## Quick start

### 1. Start the API

From the repository root:

```bash
cd api
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
fastapi dev src/main.py --port 3000
```

The API creates its local SQLite database on first startup.

### 2. Start the frontend

In another terminal:

```bash
cd web
npm install
```

Create `web/.env` with the API base URL:

```dotenv
VITE_APP_API_URL=http://127.0.0.1:3000/api/v1
```

Then start Vite:

```bash
npm run dev
```

Open the URL printed by Vite, normally
<http://localhost:5173>. Register an account and follow the onboarding flow to
create a company and first project.

## Local service URLs

| Service | URL |
| --- | --- |
| Frontend | <http://localhost:5173> |
| API | <http://127.0.0.1:3000> |
| Interactive API documentation | <http://127.0.0.1:3000/docs> |
| OpenAPI document | <http://127.0.0.1:3000/openapi.json> |
| Curated MCP gateway | <http://127.0.0.1:3000/mcp> |

## Optional agent automation

The basic web and API processes do not require the automation services. To
process planned todos continuously, first configure the GitHub and local-agent
settings in `api/.env`. The important safety controls default to disabled:

```dotenv
GITHUB_ENABLED=false
GITHUB_WRITE_ENABLED=false
GITHUB_MERGE_ENABLED=false
GITHUB_RELEASE_ENABLED=false
LOCAL_AGENT_ENABLED=false
```

Enable only the operations required for your environment. Never commit the
token or the `.env` file.

Start Redis and the GitHub MCP service:

```bash
cd api
docker compose up -d redis github-mcp
```

With the API virtual environment active, start a single worker:

```bash
celery -A src.agents.celery_app:celery_app worker \
  --loglevel=INFO \
  --pool=solo \
  --concurrency=1
```

In another terminal, start the scheduler:

```bash
cd api
source .venv/bin/activate
celery -A src.agents.celery_app:celery_app beat --loglevel=INFO
```

Agent execution is intentionally serialized because runs share Git working-tree
state. See the [API documentation](api/README.md) for the full GitHub MCP,
worker, security, and troubleshooting configuration.

## Development checks

Run frontend checks:

```bash
cd web
npm run lint
npm run build
```

Run backend checks with the virtual environment active:

```bash
cd api
pytest
ruff check .
ruff format --check .
```

## API contract

The frontend integrates with the endpoints and WebSocket metadata in
[`web/api-contract.json`](web/api-contract.json). When the backend interface
changes, update this contract and the corresponding frontend types and calls in
the same change.

The frontend reads its API origin exclusively from `VITE_APP_API_URL`. Keep the
`/api/v1` suffix in that value; endpoint helpers append resource paths to it.

## Core workflow

1. Create an account, company, and project.
2. Add draft work to the project's WIP queue.
3. Mark a todo as planned and assign it to a version.
4. Run the configured coding agent.
5. Review the resulting pull request and merge completed work.
6. Complete and release a version after its todos are finished.

## Security notes

- Keep `.env`, access tokens, database files, and generated credentials out of
  version control.
- Bind development services to localhost unless authentication and transport
  security have been configured.
- Use fine-grained GitHub tokens restricted to the required repositories and
  permissions.
- Treat local agent execution as trusted code execution within each project's
  configured folder.
- Review GitHub mutation gates before enabling write, merge, or release actions.

