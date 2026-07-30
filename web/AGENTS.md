# AGENTS.md

This file defines the working agreement for coding agents in this repository.
Apply these instructions to every change unless a more specific `AGENTS.md`
exists deeper in the directory tree.

## Project overview

- Stack: React 19, TypeScript, Vite, React Aria Components, Tailwind CSS,
  React Router, Lucide React, and Axios.
- Package manager: npm. Keep `package-lock.json` in sync with `package.json`.
- Application source lives in `src/`; static files live in `public/`.
- Keep the project client-rendered unless the task explicitly changes the
  architecture.

## Before editing

1. Read the relevant source, configuration, and tests before making changes.
2. Check the working tree and preserve user-authored or unrelated changes.
3. Clarify only when a decision is consequential and cannot be inferred from
   the repository; otherwise make the smallest reasonable assumption.
4. Prefer existing project patterns and dependencies over introducing new
   abstractions or packages.

## Implementation practices

- Make focused changes that directly address the request. Avoid opportunistic
  rewrites.
- Use strict TypeScript. Do not add `any`, unsafe assertions, or suppressed
  errors without a documented reason.
- Prefer small, composable function components and colocate styles with the
  feature that uses them.
- Always inspect `src/components/` before creating a component. Reuse or extend
  an existing component when it already provides the required behavior.
- Reserve `src/components/` for reusable components shared across features.
  Place feature modules, feature-specific state, and route-level screens in
  `src/[feature_name]/`.
- When reusable UI with custom functionality is needed and no suitable
  component exists, compose it in `src/components/[component_name]/`. Colocate
  its implementation and component-specific supporting files in that folder.
- Prefer Tailwind utilities for component styling. Add reusable semantic tokens
  to `src/index.css`; use custom CSS only when utilities cannot express the
  requirement clearly.
- Keep state as local as practical. Derive values instead of synchronizing
  duplicate state with effects.
- Use semantic HTML before adding ARIA attributes. Never recreate native or
  React Aria interactions with ad hoc click and keyboard handlers.
- Import interactive primitives from `react-aria-components`. Style component
  states with React Aria data attributes such as `data-hovered`,
  `data-pressed`, and `data-focus-visible`.
- Define client routes with React Router and use `Link` or `NavLink` for
  internal navigation instead of plain anchors or imperative history calls.
- Import Lucide icons individually. Decorative icons must be hidden from
  assistive technology; meaningful icon-only controls need an accessible name.
- Use `src/utilities/useApi.tsx` for HTTP calls from React components and custom
  hooks. Call `useApi<ResponseType>()` only at the top level of a component or
  hook, then use its typed request methods and read the latest successful
  response from `data`.
- Pass query parameters as the second argument to `get` and `delete`; pass JSON
  request bodies as the second argument to `post`, `put`, and `patch`. Use
  `postUpload` or `patchUpload` with `FormData` for uploads, and do not set the
  multipart `Content-Type` manually because Axios must add the boundary.
- Configure request defaults with
  `useApi({ timeout, retries, retryDelay })`. Override them per request in the
  third config argument. `retries` means additional attempts and uses
  exponential backoff; it defaults to `0`.
- Retry `post`, `patch`, and upload requests only when the endpoint is
  idempotent or uses an idempotency key. Handle rejected Axios promises
  explicitly, and pass an `AbortSignal` in the request config when cancellation
  is needed.
- Authentication is managed through `AccountProvider` and
  `src/utilities/authToken.ts`. `useApi` automatically attaches the stored
  bearer token to protected requests; do not read, duplicate, log, or manually
  pass the token from feature components.
- Keep sign-in and registration routes outside the authenticated dashboard
  layout. New users must complete account, company, and first-project
  onboarding in that order before entering the project workspace.

Use this pattern:

```tsx
type User = { id: string; name: string }
type CreateUser = { name: string }

const userApi = useApi<User>({
  timeout: 10_000,
  retries: 0,
  retryDelay: 300,
})

await userApi.get("/api/users/1", undefined, { retries: 2 })
await userApi.post<CreateUser>("/api/users", { name: "Ada" }, { retries: 0 })

const formData = new FormData()
formData.append("avatar", file)
await userApi.patchUpload("/api/users/1/avatar", formData, { retries: 0 })
```

- Use `useAlerts` from `src/utilities/alerts` for transient, app-level
  feedback after meaningful actions such as saves, uploads, assignments,
  releases, and recoverable request failures. The application is already
  wrapped in `AlertsProvider`; do not add feature-level providers.
- Call `useAlerts()` only at the top level of a React component or custom hook.
  Use `showAlert({ title, description, variant, duration })`, choosing
  `success`, `error`, `warning`, or `info` to match the outcome. Alerts
  auto-dismiss after five seconds by default; pass `duration: 0` only when the
  user must explicitly dismiss the message.
- Keep alert titles short and action-oriented. Put useful recovery context in
  `description`, never include secrets or raw server responses, and avoid
  duplicate alerts for the same outcome. Use inline validation for field
  errors instead of alerts.
- `AlertsProvider` owns the singleton WebSocket connection to
  `/api/v1/agent-runs/events`; do not open duplicate feature-level sockets.
  API-backed providers whose data can change after an agent run should read
  `dataRefreshVersion` from `useAlerts()` and perform a cancelable refetch when
  it changes.

Use this pattern:

```tsx
const { showAlert } = useAlerts()

try {
  await projectApi.patch("/api/projects/1", changes)
  showAlert({
    title: "Project saved",
    description: "Your roadmap changes are now available to the team.",
    variant: "success",
  })
} catch {
  showAlert({
    title: "Project could not be saved",
    description: "Check your connection and try again.",
    variant: "error",
  })
}
```

- Preserve visible keyboard focus, logical tab order, accessible names, touch
  target size, color contrast, reduced-motion preferences, and screen-reader
  announcements where relevant.
- Keep modules easy to scan. Use descriptive names and comments only when they
  explain intent or a non-obvious constraint.
- Do not add secrets, credentials, generated build output, or machine-specific
  files to the repository.

## Validation

Run the checks relevant to the change before handing it off:

```sh
npm run lint
npm run build
```

For UI changes, also inspect the result at narrow and wide viewport sizes and
exercise it with keyboard-only navigation. Add or update tests when the project
has a test harness and behavior changes.

If a check cannot run, report exactly what was not verified and why. Do not
claim success from visual inspection alone.

## Communication

- Summarize the outcome and name the files materially changed.
- Report validation results and remaining risks or assumptions.
- Cite file paths and specific errors instead of pasting large logs.
- Never claim a command, test, or browser check was performed when it was not.
