export type TodoStatus =
  | 'draft'
  | 'planned'
  | 'in-progress'
  | 'blocked'
  | 'failed'
  | 'done'

export type VersionStatus =
  | 'pending'
  | 'ready'
  | 'in-progress'
  | 'complete'
  | 'released'

export type ProjectTodo = {
  id: string
  createdAt: string
  issueNumber: number
  pullRequestUrl: string | null
  title: string
  description: string
  status: TodoStatus
  isMerged: boolean
}

export type ProjectVersion = {
  id: string
  createdAt: string
  name: string
  summary: string
  status: VersionStatus
  todos: ProjectTodo[]
}

export type Project = {
  id: string
  companyId: string
  name: string
  path: string
  versions: ProjectVersion[]
  wipTodos: ProjectTodo[]
}

export type NewProject = Pick<Project, 'companyId' | 'name' | 'path'>

export type UpdateProject = Pick<Project, 'name' | 'path'>

export type NewVersion = Pick<ProjectVersion, 'name' | 'summary'>

export type NewTodo = Pick<ProjectTodo, 'title' | 'description'>

export type UpdateTodo = Pick<ProjectTodo, 'description'>

export type NewWipTodo = Pick<ProjectTodo, 'title' | 'description'>
