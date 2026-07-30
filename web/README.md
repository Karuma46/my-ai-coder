# Vite + React Aria + Tailwind frontend

A TypeScript frontend starter built with React, Vite, React Aria Components,
Tailwind CSS, React Router, Lucide icons, and Axios.

## Get started

```sh
npm install
npm run dev
```

## Commands

- `npm run dev` starts the local development server.
- `npm run build` type-checks and creates a production build.
- `npm run lint` runs Oxlint.
- `npm run preview` serves the production build locally.

## Accessibility

Use components from `react-aria-components` for interactive UI. React Aria
provides accessible semantics and interaction behavior; product code is still
responsible for clear labels, logical focus order, sufficient contrast, and
testing with keyboard and assistive technology.

## Styling

Tailwind is integrated through the official `@tailwindcss/vite` plugin. Global
theme tokens and the Tailwind import live in `src/index.css`; component styles
use utility classes directly in the relevant TSX file.

## Routing and icons

`BrowserRouter` is mounted in `src/main.tsx`, with declarative routes and
navigation in `src/App.tsx`. The shared dashboard shell lives in
`src/components/layout/` and renders nested routes through React Router's
`Outlet`. Its sidebar can be collapsed from the top bar into an icon-only rail,
and routed content uses the full remaining width. Import icons individually
from `lucide-react` and mark decorative icons with `aria-hidden="true"`.

## Project roadmaps

The `src/projects/` feature module powers the `/projects` route. It includes an
expandable project/version tree, version todo status cards, and a React Aria
dialog that creates projects from a name and selected directory. Selected
projects can add roadmap versions, each version can add GitHub issue-style
todos, and todo rows open a details dialog with their issue number, title,
description, and status.

## HTTP requests

`src/utilities/useApi.tsx` provides typed `get`, `post`, `put`, `patch`, and
`delete` functions backed by Axios. Its `postUpload` and `patchUpload` methods
accept `FormData` and support Axios options such as upload progress callbacks
and abort signals. The hook exposes the latest successful response through
`data`, and each request resolves to `{ data }`.

The hook defaults to a 10-second timeout with retries disabled. Pass `timeout`,
`retries`, and `retryDelay` to the hook to set defaults, or in an individual
request's config to override them. Retries use exponential backoff and only run
for network errors, timeouts, HTTP 408/429 responses, and server errors.

The frontend reads its versioned API base URL from `VITE_APP_API_URL` (for
example, `http://127.0.0.1:8000/api/v1`) and appends resource paths from
`api-contract.json`. The health check is requested from `/health` on the same
origin. Dashboard, account, health, reports, and project roadmap screens use
those endpoints directly; successful response bodies are not expected to have
an additional `data` wrapper. Vite proxies local development requests through
the configured URL so the backend does not need permissive development CORS;
production deployments must still allow the frontend origin when the API is
hosted separately.
