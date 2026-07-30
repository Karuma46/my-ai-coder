import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Eye,
  LoaderCircle,
  Rocket,
} from 'lucide-react'
import { useState } from 'react'
import { Button, Heading } from 'react-aria-components'
import { ConfirmActionDialog } from '../components/confirm-action-dialog'
import { AddTodoDialog } from './AddTodoDialog'
import { sortByCreatedAtDescending } from './sortByCreatedAt'
import { TodoItem } from './TodoItem'
import type { NewTodo, ProjectVersion, UpdateTodo } from './types'
import { VersionStatusBadge } from './VersionStatusBadge'

type VersionCardProps = {
  projectId: string
  version: ProjectVersion
  onAddTodo: (todo: NewTodo) => Promise<void>
  onMarkTodoPlanned: (todoId: string) => Promise<void>
  onUpdateTodo: (todoId: string, changes: UpdateTodo) => Promise<void>
  onDeleteTodo: (todoId: string) => Promise<void>
  onMergeTodo: (todoId: string) => Promise<void>
  onMarkReady: () => Promise<void>
  onComplete: () => Promise<void>
  onRelease: () => Promise<void>
  onDelete: () => Promise<void>
}

const actionButtonStyles =
  'inline-flex min-h-9 cursor-pointer items-center justify-center gap-2 rounded-lg border border-border bg-surface px-3 text-xs font-bold text-heading transition-colors data-[hovered]:bg-surface-muted data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:cursor-not-allowed disabled:opacity-50'

export function VersionCard({
  projectId,
  version,
  onAddTodo,
  onMarkTodoPlanned,
  onUpdateTodo,
  onDeleteTodo,
  onMergeTodo,
  onMarkReady,
  onComplete,
  onRelease,
  onDelete,
}: VersionCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isCompleting, setIsCompleting] = useState(false)
  const [isReleasing, setIsReleasing] = useState(false)
  const contentId = `version-${version.id}-content`
  const completedTodos = version.todos.filter(
    ({ status }) => status === 'done',
  ).length
  const orderedTodos = sortByCreatedAtDescending(version.todos)
  const isPending = version.status === 'pending'
  const canAddTodos = ['pending', 'ready', 'in-progress'].includes(
    version.status,
  )
  const canMarkComplete =
    version.status === 'ready' || version.status === 'in-progress'
  const isReadyToComplete =
    version.todos.length > 0 &&
    version.todos.every(
      ({ isMerged, status }) => status === 'done' && isMerged,
    )
  const canRelease = version.status === 'complete'

  const markComplete = async () => {
    setIsCompleting(true)

    try {
      await onComplete()
    } catch {
      // The projects provider displays the request failure.
    } finally {
      setIsCompleting(false)
    }
  }

  const release = async () => {
    setIsReleasing(true)

    try {
      await onRelease()
    } catch {
      // The projects provider displays the request failure.
    } finally {
      setIsReleasing(false)
    }
  }

  return (
    <article
      id={`version-${version.id}`}
      className="min-w-0 scroll-mt-20 rounded-xl border border-border bg-surface shadow-sm"
    >
      <header className="px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <Heading level={2} className="m-0 text-lg font-bold text-heading">
              {version.name}
            </Heading>
            <p className="mt-1 mb-0 text-sm text-muted">{version.summary}</p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <VersionStatusBadge status={version.status} />
            <Button
              aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${version.name}`}
              aria-expanded={isExpanded}
              aria-controls={contentId}
              onPress={() => setIsExpanded((expanded) => !expanded)}
              className="grid size-10 shrink-0 cursor-pointer place-items-center rounded-lg border border-border bg-surface text-muted transition-colors data-[hovered]:bg-surface-muted data-[hovered]:text-heading data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus"
            >
              {isExpanded ? (
                <ChevronDown aria-hidden="true" size={18} strokeWidth={2.2} />
              ) : (
                <ChevronRight aria-hidden="true" size={18} strokeWidth={2.2} />
              )}
            </Button>
          </div>
        </div>
      </header>

      <div id={contentId} hidden={!isExpanded}>
        <div className="flex flex-wrap items-center gap-2 border-y border-border px-5 py-4">
          <span className="rounded-full bg-surface-muted px-3 py-1 text-xs font-bold text-muted">
            {completedTodos}/{version.todos.length} complete
          </span>
          <div className="ml-auto flex flex-wrap items-center justify-end gap-2">
            <Button
              isDisabled
              aria-label={`Preview ${version.name} (coming soon)`}
              aria-description="Preview functionality is coming later."
              className={actionButtonStyles}
            >
              <Eye aria-hidden="true" size={15} strokeWidth={2.2} />
              Preview
            </Button>
            {isPending && (
              <ConfirmActionDialog
                tone="primary"
                triggerLabel="Mark ready"
                triggerAriaLabel={`Mark ${version.name} as ready`}
                title={`Mark ${version.name} as ready?`}
                description="This enables agent runs for planned todos in the version."
                confirmLabel="Mark ready"
                onConfirm={onMarkReady}
              />
            )}
            {canMarkComplete && (
              <Button
                isDisabled={!isReadyToComplete || isCompleting}
                aria-description={
                  isReadyToComplete
                    ? undefined
                    : 'Every todo must be complete and merged first.'
                }
                onPress={markComplete}
                className={actionButtonStyles}
              >
                {isCompleting ? (
                  <LoaderCircle
                    aria-hidden="true"
                    className="motion-safe:animate-spin"
                    size={15}
                    strokeWidth={2.2}
                  />
                ) : (
                  <CheckCircle2
                    aria-hidden="true"
                    size={15}
                    strokeWidth={2.2}
                  />
                )}
                {isCompleting ? 'Completing…' : 'Mark complete'}
              </Button>
            )}
            {canRelease && (
              <Button
                isDisabled={isReleasing}
                onPress={release}
                className={`${actionButtonStyles} border-accent bg-accent text-white data-[hovered]:bg-accent-hover`}
              >
                {isReleasing ? (
                  <LoaderCircle
                    aria-hidden="true"
                    className="motion-safe:animate-spin"
                    size={15}
                    strokeWidth={2.2}
                  />
                ) : (
                  <Rocket aria-hidden="true" size={15} strokeWidth={2.2} />
                )}
                {isReleasing ? 'Releasing…' : 'Release'}
              </Button>
            )}
            {isPending && (
              <ConfirmActionDialog
                triggerLabel="Delete"
                triggerAriaLabel={`Delete ${version.name}`}
                title={`Delete ${version.name}?`}
                description="This permanently removes the pending version and all of its todos."
                confirmLabel="Delete version"
                onConfirm={onDelete}
              />
            )}
            {canAddTodos && (
              <AddTodoDialog
                versionName={version.name}
                onAddTodo={onAddTodo}
              />
            )}
          </div>
        </div>

        {orderedTodos.length > 0 ? (
          <ul className="m-0 list-none divide-y divide-border p-0">
            {orderedTodos.map((todo) => (
              <li key={todo.id}>
                <TodoItem
                  projectId={projectId}
                  todo={todo}
                  versionName={version.name}
                  versionStatus={version.status}
                  onMarkPlanned={() => onMarkTodoPlanned(todo.id)}
                  onUpdate={(changes) => onUpdateTodo(todo.id, changes)}
                  onDelete={() => onDeleteTodo(todo.id)}
                  onMerge={() => onMergeTodo(todo.id)}
                />
              </li>
            ))}
          </ul>
        ) : (
          <p className="m-0 px-5 py-6 text-center text-sm text-muted">
            {canAddTodos
              ? 'No todos yet. Add the first issue for this version.'
              : 'No todos were assigned to this version.'}
          </p>
        )}
      </div>
    </article>
  )
}
