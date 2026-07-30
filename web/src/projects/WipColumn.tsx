import { CircleDotDashed } from 'lucide-react'
import { Heading } from 'react-aria-components'
import { ConfirmActionDialog } from '../components/confirm-action-dialog'
import { AddWipTodoDialog } from './AddWipTodoDialog'
import { AssignTodoDialog } from './AssignTodoDialog'
import { TodoStatusBadge } from './TodoStatusBadge'
import type { NewWipTodo, ProjectTodo, ProjectVersion } from './types'

type WipColumnProps = {
  projectName: string
  todos: ProjectTodo[]
  versions: ProjectVersion[]
  onAddTodo: (todo: NewWipTodo) => Promise<void>
  onDeleteTodo: (todoId: string) => Promise<void>
  onAssignTodo: (todoId: string, versionId: string) => Promise<void>
}

export function WipColumn({
  projectName,
  todos,
  versions,
  onAddTodo,
  onDeleteTodo,
  onAssignTodo,
}: WipColumnProps) {
  const headingId = `project-${projectName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')}-wip`
  const assignableVersions = versions.filter(
    (version) =>
      version.status === 'pending' ||
      version.status === 'ready' ||
      version.status === 'in-progress',
  )

  return (
    <aside
      aria-labelledby={headingId}
      className="min-w-0 overflow-hidden rounded-xl border border-border bg-surface shadow-sm xl:sticky xl:top-20"
    >
      <header className="border-b border-border px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <CircleDotDashed
              aria-hidden="true"
              className="shrink-0 text-accent"
              size={18}
            />
            <Heading
              id={headingId}
              level={2}
              className="m-0 truncate text-base font-bold text-heading"
            >
              WIP
            </Heading>
          </div>
          <span
            aria-label={`${todos.length} unassigned ${todos.length === 1 ? 'todo' : 'todos'}`}
            className="grid size-7 shrink-0 place-items-center rounded-full bg-surface-muted text-xs font-bold text-muted"
          >
            {todos.length}
          </span>
        </div>
        <p className="mt-2 mb-0 text-xs leading-5 text-muted">
          Pending issues not yet assigned to a version.
        </p>
        <AddWipTodoDialog
          projectName={projectName}
          onAddTodo={onAddTodo}
        />
      </header>

      {todos.length > 0 ? (
        <ul className="m-0 list-none divide-y divide-border p-0">
          {todos.map((todo) => (
            <li key={todo.id} className="px-5 py-4">
              <p className="m-0 truncate text-sm font-semibold text-heading">
                {todo.title}
              </p>
              <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                <TodoStatusBadge status="draft" />
                <div className="flex flex-wrap justify-end gap-2">
                  <AssignTodoDialog
                    todoId={todo.id}
                    todoTitle={todo.title}
                    versions={assignableVersions}
                    onAssign={onAssignTodo}
                  />
                  <ConfirmActionDialog
                    triggerLabel="Delete"
                    title="Delete draft todo?"
                    description={`This permanently removes “${todo.title}” from WIP.`}
                    confirmLabel="Delete todo"
                    onConfirm={() => onDeleteTodo(todo.id)}
                  />
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="m-0 px-5 py-6 text-center text-sm text-muted">
          No unassigned todos.
        </p>
      )}
    </aside>
  )
}
