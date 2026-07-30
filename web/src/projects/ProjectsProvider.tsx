import axios from 'axios'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useAlerts } from '../utilities/alerts'
import { apiEndpoint } from '../utilities/apiEndpoint'
import { useApi } from '../utilities/useApi'
import { ProjectsContext, type ProjectsContextValue } from './context'
import type {
  NewProject,
  NewTodo,
  NewVersion,
  NewWipTodo,
  Project,
  ProjectTodo,
  ProjectVersion,
  UpdateProject,
  UpdateTodo,
} from './types'

type ProjectsProviderProps = {
  children: ReactNode
}

type ProjectListResponse = {
  items: Array<Pick<Project, 'id' | 'companyId' | 'name' | 'path'>>
  nextCursor: string | null
}

export function ProjectsProvider({ children }: ProjectsProviderProps) {
  const { dataRefreshVersion, showAlert } = useAlerts()
  const [projects, setProjects] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [hasLoadError, setHasLoadError] = useState(false)
  const hasLoadedProjects = useRef(false)
  const { get: listProjects } = useApi<ProjectListResponse>()
  const {
    get: getProject,
    patch: patchProject,
    post: postProject,
  } = useApi<Project>()
  const { patch: patchVersion, post: postVersion } = useApi<ProjectVersion>()
  const { patch: patchTodo, post: postTodo } = useApi<ProjectTodo>()
  const { delete: deleteRequest } = useApi<void>()

  useEffect(() => {
    const controller = new AbortController()

    const loadProjects = async () => {
      if (!hasLoadedProjects.current) {
        setIsLoading(true)
      }
      setHasLoadError(false)

      try {
        const { data: projectList } = await listProjects(
          apiEndpoint('/projects'),
          undefined,
          {
            signal: controller.signal,
            retries: 2,
          },
        )
        const projectResponses = await Promise.all(
          projectList.items.map(({ id }) =>
            getProject(
              apiEndpoint(`/projects/${encodeURIComponent(id)}`),
              undefined,
              {
                signal: controller.signal,
                retries: 2,
              },
            ),
          ),
        )

        setProjects(projectResponses.map(({ data }) => data))
        hasLoadedProjects.current = true
      } catch (error) {
        if (!axios.isCancel(error)) {
          setHasLoadError(true)
          showAlert({
            title: 'Projects unavailable',
            description:
              'Project roadmaps could not be loaded. Check the API and try again.',
            variant: 'error',
          })
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      }
    }

    void loadProjects()

    return () => controller.abort()
  }, [dataRefreshVersion, getProject, listProjects, showAlert])

  const createProject = async (projectDetails: NewProject) => {
    try {
      const { data: project } = await postProject<NewProject>(
        apiEndpoint('/projects'),
        projectDetails,
        { retries: 0 },
      )

      setProjects((currentProjects) => [project, ...currentProjects])
      showAlert({
        title: 'Project created',
        description: `${project.name} is ready for roadmap planning.`,
        variant: 'success',
      })

      return project.id
    } catch (error) {
      showAlert({
        title: 'Project could not be created',
        description: 'Check the project details and try again.',
        variant: 'error',
      })
      throw error
    }
  }

  const updateProject = async (
    projectId: string,
    changes: UpdateProject,
  ) => {
    try {
      const { data: updatedProject } = await patchProject<UpdateProject>(
        apiEndpoint(`/projects/${encodeURIComponent(projectId)}`),
        changes,
        { retries: 0 },
      )

      setProjects((currentProjects) =>
        currentProjects.map((project) =>
          project.id === projectId ? updatedProject : project,
        ),
      )
      showAlert({
        title: 'Project saved',
        description: 'The project details were updated.',
        variant: 'success',
      })
    } catch (error) {
      showAlert({
        title: 'Project could not be saved',
        description: 'Check the project details and try again.',
        variant: 'error',
      })
      throw error
    }
  }

  const addVersion = async (
    projectId: string,
    versionDetails: NewVersion,
  ) => {
    try {
      const { data: version } = await postVersion<NewVersion>(
        apiEndpoint(
          `/projects/${encodeURIComponent(projectId)}/versions`,
        ),
        versionDetails,
        { retries: 0 },
      )

      setProjects((currentProjects) =>
        currentProjects.map((project) =>
          project.id === projectId
            ? { ...project, versions: [version, ...project.versions] }
            : project,
        ),
      )
      showAlert({
        title: 'Version added',
        description: `${version.name} was added to the roadmap.`,
        variant: 'success',
      })
    } catch (error) {
      showAlert({
        title: 'Version could not be added',
        description: 'Check the version details and try again.',
        variant: 'error',
      })
      throw error
    }
  }

  const addTodo = async (
    projectId: string,
    versionId: string,
    todoDetails: NewTodo,
  ) => {
    try {
      const { data: todo } = await postTodo<NewTodo>(
        apiEndpoint(
          `/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}/todos`,
        ),
        todoDetails,
        { retries: 0 },
      )

      setProjects((currentProjects) =>
        currentProjects.map((project) =>
          project.id === projectId
            ? {
                ...project,
                versions: project.versions.map((version) =>
                  version.id === versionId
                    ? { ...version, todos: [...version.todos, todo] }
                    : version,
                ),
              }
            : project,
        ),
      )
      showAlert({
        title: 'Todo added',
        description: 'The issue is now part of this version.',
        variant: 'success',
      })
    } catch (error) {
      showAlert({
        title: 'Todo could not be added',
        description: 'Check the todo details and try again.',
        variant: 'error',
      })
      throw error
    }
  }

  const addWipTodo = async (
    projectId: string,
    todoDetails: NewWipTodo,
  ) => {
    try {
      const { data: todo } = await postTodo<NewWipTodo>(
        apiEndpoint(
          `/projects/${encodeURIComponent(projectId)}/wip/todos`,
        ),
        todoDetails,
        { retries: 0 },
      )

      setProjects((currentProjects) =>
        currentProjects.map((project) =>
          project.id === projectId
            ? { ...project, wipTodos: [todo, ...project.wipTodos] }
            : project,
        ),
      )
      showAlert({
        title: 'WIP todo added',
        description: 'The draft todo is ready to be assigned to a version.',
        variant: 'success',
      })
    } catch (error) {
      showAlert({
        title: 'WIP todo could not be added',
        description: 'Check the todo details and try again.',
        variant: 'error',
      })
      throw error
    }
  }

  const completeVersion = async (projectId: string, versionId: string) => {
    try {
      const { data: completedVersion } = await patchVersion<{
        status: 'complete'
      }>(
        apiEndpoint(
          `/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}`,
        ),
        { status: 'complete' },
        { retries: 0 },
      )

      setProjects((currentProjects) =>
        currentProjects.map((project) =>
          project.id === projectId
            ? {
                ...project,
                versions: project.versions.map((version) =>
                  version.id === versionId ? completedVersion : version,
                ),
              }
            : project,
        ),
      )
      showAlert({
        title: 'Version marked complete',
        description: 'The version is ready to be released.',
        variant: 'success',
      })
    } catch (error) {
      showAlert({
        title: 'Version could not be completed',
        description: 'Confirm every todo is complete and merged, then try again.',
        variant: 'error',
      })
      throw error
    }
  }

  const markVersionReady = async (projectId: string, versionId: string) => {
    try {
      const { data: readyVersion } = await patchVersion<{
        status: 'ready'
      }>(
        apiEndpoint(
          `/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}`,
        ),
        { status: 'ready' },
        { retries: 0 },
      )

      setProjects((currentProjects) =>
        currentProjects.map((project) =>
          project.id === projectId
            ? {
                ...project,
                versions: project.versions.map((version) =>
                  version.id === versionId ? readyVersion : version,
                ),
              }
            : project,
        ),
      )
      showAlert({
        title: 'Version marked ready',
        description: 'Planned todos in this version can now be run.',
        variant: 'success',
      })
    } catch (error) {
      showAlert({
        title: 'Version could not be marked ready',
        description: 'Confirm the version is still pending and try again.',
        variant: 'error',
      })
      throw error
    }
  }

  const deleteVersion = async (projectId: string, versionId: string) => {
    try {
      await deleteRequest(
        apiEndpoint(
          `/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}`,
        ),
        undefined,
        { retries: 0 },
      )

      setProjects((currentProjects) =>
        currentProjects.map((project) =>
          project.id === projectId
            ? {
                ...project,
                versions: project.versions.filter(
                  (version) => version.id !== versionId,
                ),
              }
            : project,
        ),
      )
      showAlert({
        title: 'Version deleted',
        description: 'The pending version and its todos were removed.',
        variant: 'success',
      })
    } catch (error) {
      showAlert({
        title: 'Version could not be deleted',
        description: 'Only pending versions can be deleted.',
        variant: 'error',
      })
      throw error
    }
  }

  const deleteTodo = async (projectId: string, todoId: string) => {
    try {
      await deleteRequest(
        apiEndpoint(
          `/projects/${encodeURIComponent(projectId)}/todos/${encodeURIComponent(todoId)}`,
        ),
        undefined,
        { retries: 0 },
      )

      setProjects((currentProjects) =>
        currentProjects.map((project) =>
          project.id === projectId
            ? {
                ...project,
                wipTodos: project.wipTodos.filter(
                  (todo) => todo.id !== todoId,
                ),
                versions: project.versions.map((version) => ({
                  ...version,
                  todos: version.todos.filter((todo) => todo.id !== todoId),
                })),
              }
            : project,
        ),
      )
      showAlert({
        title: 'Todo deleted',
        description: 'The draft todo was removed from the roadmap.',
        variant: 'success',
      })
    } catch (error) {
      showAlert({
        title: 'Todo could not be deleted',
        description: 'Only draft todos can be deleted.',
        variant: 'error',
      })
      throw error
    }
  }

  const markTodoPlanned = async (projectId: string, todoId: string) => {
    try {
      const { data: plannedTodo } = await patchTodo<{ status: 'planned' }>(
        apiEndpoint(
          `/projects/${encodeURIComponent(projectId)}/todos/${encodeURIComponent(todoId)}`,
        ),
        { status: 'planned' },
        { retries: 0 },
      )

      setProjects((currentProjects) =>
        currentProjects.map((project) =>
          project.id === projectId
            ? {
                ...project,
                versions: project.versions.map((version) => ({
                  ...version,
                  todos: version.todos.map((todo) =>
                    todo.id === todoId ? plannedTodo : todo,
                  ),
                })),
              }
            : project,
        ),
      )
      showAlert({
        title: 'Todo marked planned',
        description: 'The todo is ready for an agent run.',
        variant: 'success',
      })
    } catch (error) {
      showAlert({
        title: 'Todo could not be marked planned',
        description: 'Confirm the todo is a draft or failed and try again.',
        variant: 'error',
      })
      throw error
    }
  }

  const updateTodo = async (
    projectId: string,
    todoId: string,
    changes: UpdateTodo,
  ) => {
    try {
      const { data: updatedTodo } = await patchTodo<UpdateTodo>(
        apiEndpoint(
          `/projects/${encodeURIComponent(projectId)}/todos/${encodeURIComponent(todoId)}`,
        ),
        changes,
        { retries: 0 },
      )
      setProjects((currentProjects) =>
        currentProjects.map((project) =>
          project.id === projectId
            ? {
                ...project,
                wipTodos: project.wipTodos.map((todo) =>
                  todo.id === todoId ? updatedTodo : todo,
                ),
                versions: project.versions.map((version) => ({
                  ...version,
                  todos: version.todos.map((todo) =>
                    todo.id === todoId ? updatedTodo : todo,
                  ),
                })),
              }
            : project,
        ),
      )
      showAlert({
        title: 'Todo saved',
        description: 'The draft description has been updated.',
        variant: 'success',
      })
    } catch (error) {
      showAlert({
        title: 'Todo could not be saved',
        description: 'Check the description and try again.',
        variant: 'error',
      })
      throw error
    }
  }

  const releaseVersion = async (projectId: string, versionId: string) => {
    try {
      const { data: releasedVersion } = await postVersion(
        apiEndpoint(
          `/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}/release`,
        ),
        undefined,
        { retries: 0 },
      )

      setProjects((currentProjects) =>
        currentProjects.map((project) =>
          project.id === projectId
            ? {
                ...project,
                versions: project.versions.map((version) =>
                  version.id === versionId ? releasedVersion : version,
                ),
              }
            : project,
        ),
      )
      showAlert({
        title: 'Version released',
        description: 'The completed version is now marked as released.',
        variant: 'success',
      })
    } catch (error) {
      showAlert({
        title: 'Version could not be released',
        description: 'Confirm the version is complete and try again.',
        variant: 'error',
      })
      throw error
    }
  }

  const mergeTodo = async (projectId: string, todoId: string) => {
    try {
      const { data: mergedTodo } = await postTodo(
        apiEndpoint(
          `/projects/${encodeURIComponent(projectId)}/todos/${encodeURIComponent(todoId)}/merge`,
        ),
        undefined,
        { retries: 0 },
      )

      setProjects((currentProjects) =>
        currentProjects.map((project) =>
          project.id === projectId
            ? {
                ...project,
                versions: project.versions.map((version) => ({
                  ...version,
                  todos: version.todos.map((todo) =>
                    todo.id === todoId ? mergedTodo : todo,
                  ),
                })),
              }
            : project,
        ),
      )
      showAlert({
        title: 'Todo merged',
        description: 'The completed todo has been marked as merged.',
        variant: 'success',
      })
    } catch (error) {
      showAlert({
        title: 'Todo could not be merged',
        description: 'Confirm the todo is complete and try again.',
        variant: 'error',
      })
      throw error
    }
  }

  const assignWipTodo = async (
    projectId: string,
    todoId: string,
    versionId: string,
  ) => {
    try {
      const { data: assignedTodo } = await postTodo<{ versionId: string }>(
        apiEndpoint(
          `/projects/${encodeURIComponent(projectId)}/todos/${encodeURIComponent(todoId)}/assign`,
        ),
        { versionId },
        { retries: 0 },
      )

      setProjects((currentProjects) =>
        currentProjects.map((project) =>
          project.id === projectId
            ? {
                ...project,
                wipTodos: project.wipTodos.filter(
                  (todo) => todo.id !== todoId,
                ),
                versions: project.versions.map((version) =>
                  version.id === versionId
                    ? {
                        ...version,
                        todos: [...version.todos, assignedTodo],
                      }
                    : version,
                ),
              }
            : project,
        ),
      )
      showAlert({
        title: 'Todo assigned',
        description: 'The draft todo was moved into the selected version.',
        variant: 'success',
      })
    } catch (error) {
      showAlert({
        title: 'Todo could not be assigned',
        description: 'Choose an active version and try again.',
        variant: 'error',
      })
      throw error
    }
  }

  const value: ProjectsContextValue = {
    projects,
    isLoading,
    hasLoadError,
    createProject,
    updateProject,
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
  }

  return (
    <ProjectsContext.Provider value={value}>
      {children}
    </ProjectsContext.Provider>
  )
}
