import { FolderKanban, Settings } from 'lucide-react'
import { Heading } from 'react-aria-components'
import { Link, Navigate, useNavigate, useParams } from 'react-router'
import { useAccount } from '../account'
import { AddVersionDialog } from './AddVersionDialog'
import { CreateProjectDialog } from './CreateProjectDialog'
import { sortByCreatedAtDescending } from './sortByCreatedAt'
import type { NewProject } from './types'
import { useProjects } from './useProjects'
import { VersionCard } from './VersionCard'
import { WipColumn } from './WipColumn'

export function ProjectsPage() {
  const { companies } = useAccount()
  const {
    projects,
    isLoading,
    hasLoadError,
    createProject,
    addVersion,
    addTodo,
    addWipTodo,
    markVersionReady,
    completeVersion,
    releaseVersion,
    deleteVersion,
    deleteTodo,
    markTodoPlanned,
    updateTodo,
    mergeTodo,
    assignWipTodo,
  } = useProjects()
  const { projectId } = useParams()
  const navigate = useNavigate()
  const selectedProject = projects.find(({ id }) => id === projectId)
  const orderedVersions = selectedProject
    ? sortByCreatedAtDescending(selectedProject.versions)
    : []
  const handleCreateProject = async (project: NewProject) => {
    const newProjectId = await createProject(project)
    navigate(`/projects/${newProjectId}`)
  }
  const pageHeader = (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="m-0 text-xs font-bold tracking-[0.12em] text-accent uppercase">
          Roadmaps
        </p>
        <Heading
          level={1}
          className="mt-2 mb-0 text-3xl font-bold tracking-[-0.035em] text-heading sm:text-4xl"
        >
          Projects
        </Heading>
        <p className="mt-3 mb-0 max-w-2xl text-sm leading-6 text-muted sm:text-base">
          Organize project versions, track roadmap work, and see the status of
          every todo in one place.
        </p>
      </div>
      <div className="w-full shrink-0 sm:w-auto">
        <CreateProjectDialog
          companies={companies}
          onCreate={handleCreateProject}
        />
      </div>
    </header>
  )

  if (isLoading) {
    return (
      <>
        {pageHeader}
        <p
          role="status"
          className="mt-8 rounded-xl border border-border bg-surface p-6 text-sm text-muted shadow-sm"
        >
          Loading project roadmaps…
        </p>
      </>
    )
  }

  if (projects.length === 0) {
    return (
      <>
        {pageHeader}
        <section className="mt-8 rounded-xl border border-dashed border-border bg-surface p-10 text-center">
          <Heading level={2} className="m-0 text-lg font-bold text-heading">
            {hasLoadError ? 'Projects unavailable' : 'No projects yet'}
          </Heading>
          <p className="mt-2 mb-0 text-sm text-muted">
            {hasLoadError
              ? 'Check that the API is available, then refresh this page.'
              : 'Create a project to start planning its roadmap.'}
          </p>
        </section>
      </>
    )
  }

  if (!projectId || !selectedProject) {
    const firstProject = projects[0]

    return <Navigate to={`/projects/${firstProject.id}`} replace />
  }

  return (
    <>
      {pageHeader}

      <div className="mt-8 grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_28rem]">
        <section aria-labelledby="selected-project-title" className="min-w-0">
          <header className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex min-w-0 items-start gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-surface text-accent shadow-sm ring-1 ring-border">
                <FolderKanban aria-hidden="true" size={19} />
              </span>
              <div className="min-w-0">
                <Heading
                  id="selected-project-title"
                  level={2}
                  className="m-0 truncate text-xl font-bold text-heading"
                >
                  {selectedProject.name}
                </Heading>
                <p
                  className="mt-1 mb-0 truncate text-xs text-muted"
                  title={selectedProject.path}
                >
                  {selectedProject.path}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Link
                to={`/projects/${selectedProject.id}/settings`}
                aria-label={`Settings for ${selectedProject.name}`}
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-border bg-surface px-3 text-sm font-bold text-heading no-underline transition-colors hover:bg-surface-muted focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-focus"
              >
                <Settings aria-hidden="true" size={17} />
                Settings
              </Link>
              <AddVersionDialog
                projectName={selectedProject.name}
                onAddVersion={(version) =>
                  addVersion(selectedProject.id, version)
                }
              />
            </div>
          </header>

          {orderedVersions.length > 0 ? (
            <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-4">
              {orderedVersions.map((version) => (
                <VersionCard
                  key={version.id}
                  projectId={selectedProject.id}
                  version={version}
                  onAddTodo={(todo) =>
                    addTodo(selectedProject.id, version.id, todo)
                  }
                  onMarkTodoPlanned={(todoId) =>
                    markTodoPlanned(selectedProject.id, todoId)
                  }
                  onUpdateTodo={(todoId, changes) =>
                    updateTodo(selectedProject.id, todoId, changes)
                  }
                  onDeleteTodo={(todoId) =>
                    deleteTodo(selectedProject.id, todoId)
                  }
                  onMergeTodo={(todoId) =>
                    mergeTodo(selectedProject.id, todoId)
                  }
                  onMarkReady={() =>
                    markVersionReady(selectedProject.id, version.id)
                  }
                  onComplete={() =>
                    completeVersion(selectedProject.id, version.id)
                  }
                  onRelease={() =>
                    releaseVersion(selectedProject.id, version.id)
                  }
                  onDelete={() =>
                    deleteVersion(selectedProject.id, version.id)
                  }
                />
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-border bg-surface p-10 text-center">
              <Heading level={3} className="m-0 text-base font-bold text-heading">
                No versions yet
              </Heading>
              <p className="mt-2 mb-0 text-sm text-muted">
                This project is ready for its first roadmap version.
              </p>
            </div>
          )}
        </section>

        <WipColumn
          projectName={selectedProject.name}
          todos={selectedProject.wipTodos}
          versions={orderedVersions}
          onAddTodo={(todo) => addWipTodo(selectedProject.id, todo)}
          onDeleteTodo={(todoId) =>
            deleteTodo(selectedProject.id, todoId)
          }
          onAssignTodo={(todoId, versionId) =>
            assignWipTodo(selectedProject.id, todoId, versionId)
          }
        />
      </div>
    </>
  )
}
