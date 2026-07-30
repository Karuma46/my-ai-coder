export type AgentProvider = 'codex' | 'claude' | 'ollama'

export type LocalAgent = {
  id: string
  companyId: string
  name: string
  provider: AgentProvider
  modelName: string
  enabled: boolean
  isDefault: boolean
  command: string
  gitCommand: string
  gitRemote: string
  timeoutSeconds: number
  maxOutputCharacters: number
  pushEnabled: boolean
  createdAt: string
  updatedAt: string
}

export type LocalAgentInput = Omit<
  LocalAgent,
  'id' | 'companyId' | 'createdAt' | 'updatedAt'
>
