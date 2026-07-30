import {
  CircleDotDashed,
  ExternalLink,
  GitMerge,
  LoaderCircle,
  Pencil,
  Play,
  Save,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  Button,
  Dialog,
  DialogTrigger,
  Heading,
  Link,
  Modal,
  TextArea,
  TextField,
} from 'react-aria-components'
import { ConfirmActionDialog } from '../components/confirm-action-dialog'
import type { LocalAgent } from '../local-agents/types'
import { useAlerts } from '../utilities/alerts'
import { apiEndpoint } from '../utilities/apiEndpoint'
import { useApi } from '../utilities/useApi'
import { TodoStatusBadge } from './TodoStatusBadge'
import type {
  ProjectTodo,
  UpdateTodo,
  VersionStatus,
} from './types'
import { useProjects } from './useProjects'

type TodoItemProps = {
  projectId: string
  todo: ProjectTodo
  versionName: string
  versionStatus: VersionStatus
  onMarkPlanned: () => Promise<void>
  onUpdate: (changes: UpdateTodo) => Promise<void>
  onDelete: () => Promise<void>
  onMerge: () => Promise<void>
}

type AgentRun = {
  id: string
  projectId: string
  todoId: string
  status: 'running' | 'succeeded' | 'failed'
}

type CreateAgentRun = {
  projectId: string
  todoId: string
  localAgentId?: string
  push: boolean
}

type MergeTodoButtonProps = {
  todo: ProjectTodo
  isMerging: boolean
  onMerge: () => Promise<void>
  className?: string
}

function MergeTodoButton({
  todo,
  isMerging,
  onMerge,
  className = '',
}: MergeTodoButtonProps) {
  return (
    <Button
      aria-label={`${isMerging ? 'Merging' : 'Merge'} issue #${todo.issueNumber}: ${todo.title}`}
      isDisabled={isMerging}
      onPress={onMerge}
      className={`inline-flex min-h-9 cursor-pointer items-center justify-center gap-2 rounded-lg border border-accent bg-accent px-3 text-xs font-bold text-white transition-colors data-[hovered]:bg-accent-hover data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:cursor-wait disabled:opacity-60 ${className}`}
    >
      {isMerging ? (
        <LoaderCircle
          aria-hidden="true"
          className="motion-safe:animate-spin"
          size={15}
          strokeWidth={2.2}
        />
      ) : (
        <GitMerge aria-hidden="true" size={15} strokeWidth={2.2} />
      )}
      {isMerging ? 'Merging…' : 'Merge'}
    </Button>
  )
}

function ViewPullRequestLink({
  todo,
  className = '',
}: {
  todo: ProjectTodo
  className?: string
}) {
  if (!todo.pullRequestUrl) {
    return null
  }

  return (
    <Link
      aria-label={`View pull request for issue #${todo.issueNumber}: ${todo.title}`}
      href={todo.pullRequestUrl}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex min-h-9 cursor-pointer items-center justify-center gap-2 rounded-lg border border-border bg-surface px-3 text-xs font-bold text-heading no-underline transition-colors data-[hovered]:bg-surface-muted data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus ${className}`}
    >
      <ExternalLink aria-hidden="true" size={15} strokeWidth={2.2} />
      View PR
    </Link>
  )
}

function RunTodoButton({
  accessibleName,
  isRunning,
  onRun,
  className = '',
}: {
  accessibleName: string
  isRunning: boolean
  onRun: () => Promise<void>
  className?: string
}) {
  return (
    <Button
      aria-label={accessibleName}
      isDisabled={isRunning}
      onPress={onRun}
      className={`inline-flex min-h-9 cursor-pointer items-center justify-center gap-2 rounded-lg border border-border bg-surface px-3 text-xs font-bold text-heading transition-colors data-[hovered]:bg-surface-muted data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:cursor-wait disabled:opacity-60 ${className}`}
    >
      {isRunning ? (
        <LoaderCircle
          aria-hidden="true"
          className="motion-safe:animate-spin"
          size={15}
          strokeWidth={2.2}
        />
      ) : (
        <Play aria-hidden="true" size={15} strokeWidth={2.2} />
      )}
      {isRunning ? 'Running…' : 'Run'}
    </Button>
  )
}

export function TodoItem({
  projectId,
  todo,
  versionName,
  versionStatus,
  onMarkPlanned,
  onUpdate,
  onDelete,
  onMerge,
}: TodoItemProps) {
  const { showAlert } = useAlerts()
  const { projects } = useProjects()
  const project = projects.find(({ id }) => id === projectId)
  const { get: listAgents } = useApi<LocalAgent[]>()
  const { post } = useApi<AgentRun>({
    timeout: 900_000,
    retries: 0,
  })
  const [isRunning, setIsRunning] = useState(false)
  const [isMerging, setIsMerging] = useState(false)
  const [hasStarted, setHasStarted] = useState(false)
  const [agents, setAgents] = useState<LocalAgent[]>([])
  const [selectedAgentId, setSelectedAgentId] = useState('')
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [description, setDescription] = useState(todo.description)
  const [isSaving, setIsSaving] = useState(false)
  const canMerge = todo.status === 'done' && !todo.isMerged
  const isDraft = todo.status === 'draft'
  const hasFailed = todo.status === 'failed'
  const canMarkPlanned =
    isDraft &&
    (versionStatus === 'ready' || versionStatus === 'in-progress')
  const canRun =
    todo.status === 'planned' &&
    (versionStatus === 'ready' || versionStatus === 'in-progress') &&
    !hasStarted
  const canViewPullRequest =
    todo.status === 'done' && Boolean(todo.pullRequestUrl)

  useEffect(() => {
    if (!project?.companyId || !canRun) {
      return
    }

    const controller = new AbortController()
    void listAgents(
      apiEndpoint(
        `/agent-runs/companies/${project.companyId}/local-agents`,
      ),
      undefined,
      { signal: controller.signal },
    )
      .then(({ data }) => {
        const enabledAgents = data.filter(({ enabled }) => enabled)
        setAgents(enabledAgents)
        setSelectedAgentId(
          (current) => current || enabledAgents[0]?.id || '',
        )
      })
      .catch(() => {
        // The environment-configured agent remains available as a fallback.
      })

    return () => controller.abort()
  }, [canRun, listAgents, project?.companyId])

  useEffect(() => {
    setDescription(todo.description)
  }, [todo.description])

  const markPlannedAction = (
    <ConfirmActionDialog
      tone="primary"
      triggerLabel="Mark planned"
      triggerAriaLabel={`Mark issue #${todo.issueNumber} as planned`}
      title="Mark todo as planned?"
      description="This creates a branch for the todo and makes it available for an agent run."
      confirmLabel="Mark planned"
      onConfirm={onMarkPlanned}
    />
  )

  const deleteAction = (
    <ConfirmActionDialog
      triggerLabel="Delete"
      triggerAriaLabel={`Delete draft issue #${todo.issueNumber}: ${todo.title}`}
      title="Delete draft todo?"
      description={`This permanently removes “${todo.title}”.`}
      confirmLabel="Delete todo"
      onConfirm={onDelete}
    />
  )

  const rerunAction = (
    <ConfirmActionDialog
      tone="primary"
      triggerLabel="Rerun"
      triggerAriaLabel={`Rerun issue #${todo.issueNumber}: ${todo.title}`}
      title="Prepare todo to rerun?"
      description="This moves the failed todo back to planned so it can be run by a local agent again."
      confirmLabel="Prepare rerun"
      onConfirm={onMarkPlanned}
    />
  )

  const runTodo = async () => {
    setIsRunning(true)

    try {
      const { data: run } = await post<CreateAgentRun>(
        apiEndpoint('/agent-runs'),
        {
          projectId,
          todoId: todo.id,
          ...(selectedAgentId ? { localAgentId: selectedAgentId } : {}),
          push: true,
        },
        { retries: 0 },
      )

      if (run.status !== 'failed') {
        setHasStarted(true)
      }

      if (run.status === 'running') {
        showAlert({
          title: 'Agent run started',
          description: 'The local coding agent is working on this todo.',
          variant: 'info',
        })
      }
    } catch {
      showAlert({
        title: 'Todo could not be run',
        description: 'Check the agent service configuration and try again.',
        variant: 'error',
      })
    } finally {
      setIsRunning(false)
    }
  }

  const mergeTodo = async () => {
    setIsMerging(true)

    try {
      await onMerge()
    } catch {
      // The projects provider displays the request failure.
    } finally {
      setIsMerging(false)
    }
  }

  const saveDescription = async () => {
    const nextDescription = description.trim()
    if (!nextDescription || nextDescription === todo.description) {
      return
    }

    setIsSaving(true)
    try {
      await onUpdate({ description: nextDescription })
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="flex min-w-0 flex-col items-stretch sm:flex-row">
      <DialogTrigger
        isOpen={isDialogOpen}
        onOpenChange={(isOpen) => {
          setIsDialogOpen(isOpen)
          if (!isOpen) {
            setDescription(todo.description)
          }
        }}
      >
        <Button
          aria-label={`View issue #${todo.issueNumber}: ${todo.title}`}
          className="flex min-w-0 flex-1 cursor-pointer flex-col items-start gap-3 px-5 py-4 text-left transition-colors data-[hovered]:bg-surface-muted data-[focus-visible]:outline-3 data-[focus-visible]:-outline-offset-3 data-[focus-visible]:outline-focus"
        >
          <span className="w-full min-w-0">
            <span className="flex items-center gap-2">
              <span className="shrink-0 text-xs font-semibold text-muted">
                #{todo.issueNumber}
              </span>
              <span className="truncate text-sm font-semibold text-heading">
                {todo.title}
              </span>
            </span>
            <span className="mt-1 block line-clamp-2 text-xs leading-5 text-muted">
              {todo.description}
            </span>
          </span>
          <TodoStatusBadge status={todo.status} />
        </Button>

        <Modal className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-slate-950/70 p-4 backdrop-blur-sm">
          <Dialog className="w-full max-w-xl rounded-2xl border border-border bg-surface p-6 shadow-2xl outline-none">
            {({ close }) => (
              <>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="m-0 flex items-center gap-2 text-xs font-bold text-muted">
                      <CircleDotDashed aria-hidden="true" size={15} />
                      {versionName} · Issue #{todo.issueNumber}
                    </p>
                    <Heading
                      slot="title"
                      className="mt-2 mb-0 text-2xl font-bold tracking-[-0.03em] text-heading"
                    >
                      {todo.title}
                    </Heading>
                  </div>
                  <TodoStatusBadge status={todo.status} />
                </div>

                <section
                  aria-labelledby={`todo-${todo.id}-description`}
                  className="mt-6 border-t border-border pt-5"
                >
                  <Heading
                    id={`todo-${todo.id}-description`}
                    level={3}
                    className="m-0 text-sm font-bold text-heading"
                  >
                    Description
                  </Heading>
                  {isDraft ? (
                    <TextField
                      aria-label="Todo description"
                      value={description}
                      onChange={setDescription}
                      isRequired
                      className="mt-2"
                    >
                      <TextArea
                        maxLength={10000}
                        rows={7}
                        className="w-full resize-y rounded-lg border border-border bg-surface px-3 py-2.5 text-sm leading-6 text-heading outline-none data-[focused]:border-accent data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus"
                      />
                    </TextField>
                  ) : (
                    <p className="mt-2 mb-0 whitespace-pre-wrap text-sm leading-6 text-muted">
                      {todo.description}
                    </p>
                  )}
                </section>

                <div className="mt-6 flex flex-wrap justify-end gap-3">
                  {canRun && agents.length > 0 && (
                    <label className="mr-auto grid min-w-44 gap-1 text-xs font-bold text-heading">
                      Local agent
                      <select
                        value={selectedAgentId}
                        onChange={(event) =>
                          setSelectedAgentId(event.target.value)
                        }
                        className="min-h-10 rounded-lg border border-border bg-surface px-3 text-sm text-heading outline-none focus-visible:outline-3 focus-visible:outline-focus"
                      >
                        {agents.map((agent) => (
                          <option key={agent.id} value={agent.id}>
                            {agent.name} ({agent.provider})
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                  <Button
                    onPress={close}
                    className="inline-flex min-h-10 cursor-pointer items-center justify-center rounded-lg border border-border bg-surface px-4 text-sm font-bold text-heading transition-colors data-[hovered]:bg-surface-muted data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus"
                  >
                    Close
                  </Button>
                  {isDraft && (
                    <Button
                      isDisabled={
                        isSaving ||
                        !description.trim() ||
                        description.trim() === todo.description
                      }
                      onPress={saveDescription}
                      className="inline-flex min-h-10 cursor-pointer items-center justify-center gap-2 rounded-lg bg-accent px-4 text-sm font-bold text-white data-[hovered]:bg-accent-hover data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isSaving ? (
                        <LoaderCircle
                          aria-hidden="true"
                          className="motion-safe:animate-spin"
                          size={16}
                        />
                      ) : (
                        <Save aria-hidden="true" size={16} />
                      )}
                      {isSaving ? 'Saving…' : 'Save description'}
                    </Button>
                  )}
                  {canViewPullRequest && (
                    <ViewPullRequestLink
                      todo={todo}
                      className="min-h-10 px-4 text-sm"
                    />
                  )}
                  {canMerge && (
                    <MergeTodoButton
                      todo={todo}
                      isMerging={isMerging}
                      onMerge={mergeTodo}
                      className="min-h-10 px-4 text-sm"
                    />
                  )}
                  {canRun && (
                    <RunTodoButton
                      accessibleName={`Run issue #${todo.issueNumber}: ${todo.title}`}
                      isRunning={isRunning}
                      onRun={runTodo}
                      className="min-h-10 px-4 text-sm"
                    />
                  )}
                </div>
              </>
            )}
          </Dialog>
        </Modal>
      </DialogTrigger>

      {(canRun || canMerge || canViewPullRequest || isDraft || hasFailed) && (
        <div className="flex shrink-0 flex-row items-stretch justify-end gap-2 px-4 pb-4 sm:flex-col sm:justify-center sm:pr-4 sm:pb-0 sm:pl-0">
          {canViewPullRequest && <ViewPullRequestLink todo={todo} />}
          {canRun && (
            <RunTodoButton
              accessibleName={`Run issue #${todo.issueNumber}: ${todo.title}`}
              isRunning={isRunning}
              onRun={runTodo}
            />
          )}
          {canMerge && (
            <MergeTodoButton
              todo={todo}
              isMerging={isMerging}
              onMerge={mergeTodo}
            />
          )}
          {isDraft && (
            <>
              <Button
                aria-label={`Edit issue #${todo.issueNumber}: ${todo.title}`}
                onPress={() => setIsDialogOpen(true)}
                className="inline-flex min-h-9 cursor-pointer items-center justify-center gap-2 rounded-lg border border-border bg-surface px-3 text-xs font-bold text-heading transition-colors data-[hovered]:bg-surface-muted data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus"
              >
                <Pencil aria-hidden="true" size={15} />
                Edit
              </Button>
              {canMarkPlanned && markPlannedAction}
              {deleteAction}
            </>
          )}
          {hasFailed && rerunAction}
        </div>
      )}
    </div>
  )
}
