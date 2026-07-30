import { createContext } from 'react'
import type {
  NewProject,
  NewTodo,
  NewVersion,
  NewWipTodo,
  Project,
  UpdateProject,
  UpdateTodo,
} from './types'

export type ProjectsContextValue = {
  projects: Project[]
  isLoading: boolean
  hasLoadError: boolean
  createProject: (project: NewProject) => Promise<string>
  updateProject: (projectId: string, changes: UpdateProject) => Promise<void>
  addVersion: (projectId: string, version: NewVersion) => Promise<void>
  addTodo: (
    projectId: string,
    versionId: string,
    todo: NewTodo,
  ) => Promise<void>
  addWipTodo: (projectId: string, todo: NewWipTodo) => Promise<void>
  markVersionReady: (projectId: string, versionId: string) => Promise<void>
  completeVersion: (projectId: string, versionId: string) => Promise<void>
  releaseVersion: (projectId: string, versionId: string) => Promise<void>
  deleteVersion: (projectId: string, versionId: string) => Promise<void>
  deleteTodo: (projectId: string, todoId: string) => Promise<void>
  markTodoPlanned: (projectId: string, todoId: string) => Promise<void>
  updateTodo: (
    projectId: string,
    todoId: string,
    changes: UpdateTodo,
  ) => Promise<void>
  mergeTodo: (projectId: string, todoId: string) => Promise<void>
  assignWipTodo: (
    projectId: string,
    todoId: string,
    versionId: string,
  ) => Promise<void>
}

export const ProjectsContext = createContext<ProjectsContextValue | null>(null)
