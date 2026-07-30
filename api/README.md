# Project Release API

A FastAPI application for managing project work and coordinating a controlled,
AI-assisted GitHub workflow. It uses async SQLAlchemy with SQLite and exposes a
curated MCP gateway through FastMCP.

## Setup

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
fastapi dev src/main.py --port 3000
```

The API is available at <http://127.0.0.1:3000>, with interactive
documentation at <http://127.0.0.1:3000/docs>.

The SQLite database is created as `app.db` on first startup. Copy
`.env.example` to `.env` to customize its location.

## Authentication and onboarding

Passwords are hashed with Argon2 and sign-in tokens are created with PyJWT.
Set a unique secret of at least 32 characters before exposing the API:

```dotenv
AUTH_JWT_SECRET=replace-with-a-long-random-secret
AUTH_ACCESS_TOKEN_MINUTES=60
```

Register, then send the returned token as `Authorization: Bearer <token>`:

```bash
curl -X POST http://127.0.0.1:3000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Alex Morgan",
    "email": "alex@example.com",
    "password": "correct-horse-battery-staple"
  }'
```

Create a company to complete onboarding. The creator becomes its first owner.
Users can belong to several companies as an `owner` or `member`. Only owners
can add, remove, or change members, and every company must retain an owner.
Projects require `companyId` and are visible only to that company's members.

## GitHub MCP setup

Docker Compose runs the pinned official GitHub MCP server as a long-running
HTTP service. Docker must be installed and running.

1. Create a fine-grained GitHub personal access token restricted to the
   repositories this service may manage.
2. Grant only the required repository permissions. The configured tools
   typically need Metadata read access plus Contents, Issues, Pull requests,
   and Actions permissions appropriate to the operations you enable.
3. Create your local configuration:

   ```bash
   cp .env.example .env
   ```

4. Set these values in `.env`:

   ```dotenv
   GITHUB_ENABLED=true
   GITHUB_PERSONAL_ACCESS_TOKEN=github_pat_replace_me
   GITHUB_OWNER=your-user-or-organization
   GITHUB_ALLOWED_REPOSITORIES=project-one,project-two
   ```

5. Enable mutations deliberately:

   ```dotenv
   GITHUB_WRITE_ENABLED=true
   GITHUB_MERGE_ENABLED=false
   GITHUB_RELEASE_ENABLED=false
   ```

6. Start the GitHub MCP server:

   ```bash
   docker compose up -d github-mcp
   ```

   Its MCP endpoint is <http://127.0.0.1:8082/mcp>. Inspect it with
   `docker compose logs -f github-mcp`, and stop it with `docker compose down`.

The token is passed to the pinned GitHub MCP container through its environment.
It is not returned by API or MCP tool responses. Never commit `.env`.

The API connects to the Compose service through `GITHUB_MCP_URL` and
authenticates with the configured token. Set `GITHUB_MCP_TRANSPORT=stdio` only
if you want the API to launch an ephemeral Docker container for each upstream
MCP operation instead.

The API's curated MCP gateway remains available at
<http://127.0.0.1:3000/mcp>. Connect AI clients to this endpoint rather than
the unrestricted upstream server on port 8082. Keep both services bound to
localhost during development; add authentication before exposing them over a
network. The repository's `.codex/config.toml` already registers the curated
endpoint with Codex; restart Codex after starting the API so it reloads the
project MCP configuration.

## Endpoints

- `GET /health` — health check
- `POST /items` — create an item
- `GET /items` — list items
- `GET /items/{item_id}` — get an item
- `PATCH /items/{item_id}` — update an item
- `DELETE /items/{item_id}` — delete an item
- `GET /github/tools` — inspect enabled upstream GitHub tools
- `POST /github/issues` — create an issue
- `POST /github/branches` — create a branch
- `POST /github/pull-requests` — create a pull request
- `POST /github/pull-requests/merge` — merge when separately enabled
- `POST /github/releases` — trigger an existing release workflow when enabled
- `POST /api/v1/auth/register` — register and receive a JWT
- `POST /api/v1/auth/login` — sign in and receive a JWT
- `GET /api/v1/me` — get the signed-in user
- `PATCH /api/v1/me` — update the signed-in user's profile
- `GET /api/v1/companies` — list the user's companies
- `POST /api/v1/companies` — create a company as its owner
- `GET /api/v1/companies/{companyId}/members` — list company members
- `POST /api/v1/companies/{companyId}/members` — owner-only member addition
- `GET /api/v1/projects` — list projects
- `POST /api/v1/projects` — register a GitHub repository as a project
- `GET /api/v1/projects/{projectId}` — get its roadmap
- `POST /api/v1/projects/{projectId}/versions` — create a version and branch
- `POST /api/v1/projects/{projectId}/versions/{versionId}/todos` — create an
  issue-backed draft todo
- `PATCH /api/v1/projects/{projectId}/todos/{todoId}` — update a todo; changing
  a version todo from `draft` to `planned` creates its branch
- `POST /api/v1/projects/{projectId}/wip/todos` — create an unassigned draft
  issue
- `POST /api/v1/projects/{projectId}/todos/{todoId}/assign` — assign WIP work
  and create its branch
- `POST /api/v1/projects/{projectId}/todos/{todoId}/merge` — merge the todo PR
  into its version branch
- `POST /api/v1/projects/{projectId}/versions/{versionId}/release` — merge the
  completed version PR into `main`
- `POST /api/v1/agent-runs` — fetch and check out a planned todo branch, then
  execute it with a configured local coding agent
- `GET /api/v1/agent-runs/{runId}` — inspect the recorded agent result and
  output
- `WS /api/v1/agent-runs/events` — receive agent-run completion events

The MCP gateway exposes the corresponding curated tools:

- `github_create_issue`
- `github_close_issue`
- `github_create_branch`
- `github_create_pull_request`
- `github_merge_pull_request`
- `github_trigger_release`

The release tool triggers a repository workflow named `release.yml` by
default. That workflow must accept `version` and `prerelease` inputs through
`workflow_dispatch`.

## Project workflow

Projects use the repository name derived from their submitted display path.
That repository must be present in `GITHUB_ALLOWED_REPOSITORIES`.

Branch references are stored internally. Todo pull-request numbers and URLs are
included in public todo responses so clients can link to completed work.
The workflow is:

1. Creating a project requires a company membership and stores that
   `companyId`.
2. Creating a version creates `version/{versionId}` from `main`.
3. A new version starts as `pending`. Set it to `ready` when its planned todos
   may be dispatched to the local agent. `in-progress` versions also remain
   eligible for dispatch.
4. Creating a todo stores it as a branchless draft with a GitHub issue number
   and URL.
5. Changing an assigned todo from `draft` to `planned` creates
   `todo/{todoId}` from its version branch. Assigning WIP work performs this
   same transition.
6. Marking a todo `done` opens a pull request from the todo branch to the
   version branch.
7. Merging the todo merges that pull request and records the merge SHA.
8. Marking a version `complete` requires every todo to be done and merged, then
   opens the version pull request to `main`.
9. Releasing the version merges that pull request and makes the version
   immutable.

GitHub write operations require `GITHUB_WRITE_ENABLED=true`. Todo and version
merges additionally require `GITHUB_MERGE_ENABLED=true`.

## Local coding agents

Local agent execution is disabled by default. It never uses the client-provided
`Project.path` as a filesystem path. Configure a trusted directory containing
local repository clones instead:

```dotenv
LOCAL_AGENT_ENABLED=true
LOCAL_AGENT_PROVIDER=codex
LOCAL_AGENT_REPOSITORY_ROOT=/absolute/path/to/repositories
LOCAL_AGENT_PUSH_ENABLED=true
```

A GitHub project named `shoppa` is resolved as
`/absolute/path/to/repositories/shoppa`. The directory must be the root of a
Git repository with an `origin` remote. The agent runner:

1. Accepts only a todo whose status is `planned`, with a stored todo branch,
   and whose version is `ready` or `in-progress`.
2. Fetches that exact branch from `origin`.
3. If another branch is checked out, stashes tracked and untracked working
   changes under an identifiable `project-release-api` stash, then checks out
   the todo branch. The stash is preserved for later manual restoration.
4. If the todo branch is already checked out, keeps its working changes in
   place and runs the agent without checking out or stashing again. A clean
   todo branch receives a fast-forward-only update from `origin`.
5. Sends the todo title and description to `codex exec` or `claude -p` over
   standard input without invoking a shell.
6. Stages the resulting changes, creates a `todo: <title>` commit, and pushes
   it to the todo branch.
7. Calls the GitHub MCP server to open a pull request from the todo branch into
   its version branch, then stores the pull request number and URL.
8. Records the command output and exit status in `agent_run`.
9. Changes the todo to `done` only after the pull request is created, and moves
   a ready version to `in-progress`. A failed agent, commit, push, or pull
   request operation changes the todo to `failed`; change it back to `planned`
   before retrying the runner.

Start a run with:

```bash
curl -X POST http://127.0.0.1:3000/api/v1/agent-runs \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <access-token>' \
  -d '{
    "projectId": "shoppa",
    "todoId": "todo-add-cart-42",
    "provider": "codex",
    "push": true
  }'
```

The request remains open while the local agent runs. Codex uses its
`workspace-write` sandbox and an ephemeral session. Claude support requires the
`claude` executable on `PATH`.

Agents are instructed to edit and test, but not to commit or push. The runner
owns the commit and push steps so it can verify the branch before opening the
pull request. `LOCAL_AGENT_PUSH_ENABLED=true` and `"push": true` are required
for this completion workflow. GitHub write access must also be enabled.

## Continuous planned-todo processing

Celery Beat scans for planned todos every 30 seconds by default. Each todo is
claimed with an atomic database update from `planned` to `in-progress` before a
Celery job is published, so overlapping scans cannot enqueue the same todo
twice. The worker then executes the agent, commit, push, and pull-request
workflow described above.

Start the Redis broker and GitHub MCP server:

```bash
docker compose up -d redis github-mcp
```

The managed Redis instance is available only on
`redis://127.0.0.1:6380`. In separate terminals, start one local worker and one
Beat scheduler from the API directory:

```bash
source .venv/bin/activate
celery -A src.agents.celery_app:celery_app worker \
  --loglevel=INFO \
  --pool=solo \
  --concurrency=1
```

```bash
source .venv/bin/activate
celery -A src.agents.celery_app:celery_app beat --loglevel=INFO
```

The worker intentionally runs on the host rather than in Compose so it can use
the locally authenticated Codex or Claude executable and access the configured
repository root. Use a single worker process because Git checkouts are shared
filesystem state. Both processes are required: Beat only publishes
`agents.dispatch_planned_todos`; the worker consumes it and claims the todos.
You can verify that the worker is connected with:

```bash
celery -A src.agents.celery_app:celery_app inspect ping
```

Queue behavior:

- Beat dispatches up to `CELERY_PLANNED_TODO_BATCH_SIZE` todos per scan.
- Periodic dispatch messages expire after one scan interval, preventing a
  backlog of stale scans while the worker is stopped or busy.
- Queued runs use `AgentRunStatus.queued`; workers change them to `running`.
- Successful runs finish as `done` after their pull request is created.
- Agent, Git, push, and GitHub MCP failures finish as `failed`.
- If publishing to Redis fails, the queued run is failed and the todo is
  returned to `planned` for the next scan.

Tune the scheduler and Redis connections with:

```dotenv
CELERY_BROKER_URL=redis://127.0.0.1:6380/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6380/1
CELERY_PLANNED_TODO_SCAN_SECONDS=30
CELERY_PLANNED_TODO_BATCH_SIZE=10
CELERY_RESULT_EXPIRES_SECONDS=86400
CELERY_AGENT_EXECUTION_LOCK_KEY=project-release-api:agent-execution
CELERY_AGENT_EXECUTION_LOCK_RETRY_SECONDS=5
CELERY_TASK_EVENTS_CHANNEL=project-release-api:agent-events
```

Agent work is serialized. The worker is configured with concurrency `1`, and
each run must acquire a shared Redis lock before invoking the local agent. This
also prevents concurrent runs if multiple workers are started accidentally.
Jobs that cannot acquire the lock remain queued and retry after
`CELERY_AGENT_EXECUTION_LOCK_RETRY_SECONDS`.

## Agent completion WebSocket

Connect while the client is open to receive terminal agent-run updates. Both
the JWT token and authorized `projectId` are required:

```javascript
const socket = new WebSocket(
  `ws://127.0.0.1:3000/api/v1/agent-runs/events?projectId=shoppa&token=${accessToken}`,
);

socket.onmessage = ({ data }) => {
  const event = JSON.parse(data);
  if (event.type === "agent-run.completed") {
    console.log(event.todoId, event.status, event.error);
  }
};
```

Messages have this shape:

```json
{
  "type": "agent-run.completed",
  "runId": "87a9...",
  "projectId": "shoppa",
  "todoId": "todo-payment-workflow-19",
  "status": "succeeded",
  "completedAt": "2026-07-28T12:00:00Z",
  "error": null
}
```

Events use Redis Pub/Sub and are delivered to currently connected clients.
Clients should reconnect after network interruptions and use
`GET /api/v1/agent-runs/{runId}` when they need to recover durable state.

## Checks

```bash
pytest
ruff check .
ruff format --check .
```
