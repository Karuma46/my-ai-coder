import { Bot, LoaderCircle, Plus, Save } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Button, Form, Heading, Input, Label, Switch, TextField } from 'react-aria-components'
import { useAccount } from '../account'
import { ConfirmActionDialog } from '../components/confirm-action-dialog'
import { useAlerts } from '../utilities/alerts'
import { apiEndpoint } from '../utilities/apiEndpoint'
import { useApi } from '../utilities/useApi'
import type { AgentProvider, LocalAgent, LocalAgentInput } from './types'

const blankAgent: LocalAgentInput = {
  name: '',
  provider: 'codex',
  modelName: '',
  enabled: true,
  isDefault: false,
  command: 'codex',
  gitCommand: 'git',
  gitRemote: 'origin',
  timeoutSeconds: 3600,
  maxOutputCharacters: 100000,
  pushEnabled: true,
}

const inputStyles = 'w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-heading outline-none data-[focused]:border-accent data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus'
const buttonStyles = 'inline-flex min-h-10 cursor-pointer items-center justify-center gap-2 rounded-lg bg-accent px-4 text-sm font-bold text-white data-[hovered]:bg-accent-hover data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:opacity-50'

function changedAgentFields(
  original: LocalAgentInput,
  edited: LocalAgentInput,
): Partial<LocalAgentInput> {
  const changes: Partial<LocalAgentInput> = {}

  for (const key of Object.keys(blankAgent) as Array<keyof LocalAgentInput>) {
    if (edited[key] !== original[key]) {
      Object.assign(changes, { [key]: edited[key] })
    }
  }

  return changes
}

function AgentForm({
  initial,
  submitLabel,
  onSubmit,
}: {
  initial: LocalAgentInput
  submitLabel: string
  onSubmit: (value: LocalAgentInput) => Promise<void>
}) {
  const [value, setValue] = useState(initial)
  const [saving, setSaving] = useState(false)
  const field = (key: keyof LocalAgentInput, next: string | number | boolean) =>
    setValue((current) => ({ ...current, [key]: next }))

  useEffect(() => {
    setValue(initial)
  }, [initial])

  return (
    <Form className="grid gap-4" onSubmit={async (event) => {
      event.preventDefault()
      setSaving(true)
      try { await onSubmit(value) } finally { setSaving(false) }
    }}>
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField isRequired value={value.name} onChange={(next) => field('name', next)} className="grid gap-2">
          <Label className="text-sm font-bold text-heading">Agent name</Label>
          <Input className={inputStyles} maxLength={120} placeholder="Primary Codex" />
        </TextField>
        <label className="grid gap-2 text-sm font-bold text-heading">
          Provider
          <select value={value.provider} onChange={(event) => {
            const provider = event.target.value as AgentProvider
            setValue((current) => ({
              ...current,
              provider,
              command: provider === 'ollama' ? 'codex' : provider,
            }))
          }} className={inputStyles}>
            <option value="codex">Codex</option>
            <option value="claude">Claude</option>
            <option value="ollama">Ollama</option>
          </select>
        </label>
        <TextField isRequired value={value.modelName} onChange={(next) => field('modelName', next)} className="grid gap-2">
          <Label className="text-sm font-bold text-heading">Model name</Label><Input className={inputStyles} placeholder={value.provider === 'ollama' ? 'qwen3.5' : 'Provider model name'} />
        </TextField>
        <TextField isRequired value={value.command} onChange={(next) => field('command', next)} className="grid gap-2">
          <Label className="text-sm font-bold text-heading">Command</Label><Input className={inputStyles} />
          {value.provider === 'ollama' && <p className="m-0 text-xs leading-5 font-normal text-muted">Use the Codex CLI command. Ollama runs the selected model through Codex’s local provider.</p>}
        </TextField>
        <TextField isRequired value={value.gitCommand} onChange={(next) => field('gitCommand', next)} className="grid gap-2">
          <Label className="text-sm font-bold text-heading">Git command</Label><Input className={inputStyles} />
        </TextField>
        <TextField isRequired value={value.gitRemote} onChange={(next) => field('gitRemote', next)} className="grid gap-2">
          <Label className="text-sm font-bold text-heading">Git remote</Label><Input className={inputStyles} />
        </TextField>
        <TextField isRequired value={String(value.timeoutSeconds)} onChange={(next) => field('timeoutSeconds', Number(next))} className="grid gap-2">
          <Label className="text-sm font-bold text-heading">Timeout (seconds)</Label><Input type="number" min={30} max={86400} className={inputStyles} />
        </TextField>
        <TextField isRequired value={String(value.maxOutputCharacters)} onChange={(next) => field('maxOutputCharacters', Number(next))} className="grid gap-2">
          <Label className="text-sm font-bold text-heading">Maximum output characters</Label><Input type="number" min={1000} max={1000000} className={inputStyles} />
        </TextField>
      </div>
      <div className="flex flex-wrap gap-5">
        <Switch isSelected={value.enabled} onChange={(next) => field('enabled', next)} className="group flex cursor-pointer items-center gap-2 text-sm font-semibold text-heading">
          <span className="h-6 w-10 rounded-full bg-border p-1 group-data-[selected]:bg-accent"><span className="block size-4 rounded-full bg-white transition-transform group-data-[selected]:translate-x-4" /></span>Enabled
        </Switch>
        <Switch isSelected={value.isDefault} onChange={(next) => { if (next) field('isDefault', true) }} className="group flex cursor-pointer items-center gap-2 text-sm font-semibold text-heading">
          <span className="h-6 w-10 rounded-full bg-border p-1 group-data-[selected]:bg-accent"><span className="block size-4 rounded-full bg-white transition-transform group-data-[selected]:translate-x-4" /></span>Default agent
        </Switch>
        <Switch isSelected={value.pushEnabled} onChange={(next) => field('pushEnabled', next)} className="group flex cursor-pointer items-center gap-2 text-sm font-semibold text-heading">
          <span className="h-6 w-10 rounded-full bg-border p-1 group-data-[selected]:bg-accent"><span className="block size-4 rounded-full bg-white transition-transform group-data-[selected]:translate-x-4" /></span>Allow pushes
        </Switch>
      </div>
      <div className="flex justify-end">
        <Button type="submit" isDisabled={saving} className={buttonStyles}>
          {saving ? <LoaderCircle aria-hidden="true" className="animate-spin" size={17} /> : <Save aria-hidden="true" size={17} />}
          {saving ? 'Saving…' : submitLabel}
        </Button>
      </div>
    </Form>
  )
}

export function LocalAgentsPage() {
  const { companies } = useAccount()
  const { showAlert } = useAlerts()
  const [companyId, setCompanyId] = useState(companies[0]?.id ?? '')
  const [agents, setAgents] = useState<LocalAgent[]>([])
  const [adding, setAdding] = useState(false)
  const listApi = useApi<LocalAgent[]>()
  const createApi = useApi<LocalAgent>()
  const updateApi = useApi<LocalAgent>()
  const deleteApi = useApi()
  const company = companies.find(({ id }) => id === companyId) ?? companies[0]
  const listAgents = listApi.get

  const refresh = useCallback(async () => {
    if (!company?.id) return
    const { data } = await listAgents(apiEndpoint(`/agent-runs/companies/${company.id}/local-agents`))
    setAgents(data)
  }, [company?.id, listAgents])

  useEffect(() => { void refresh().catch(() => showAlert({ title: 'Agents unavailable', description: 'Local agent configurations could not be loaded.', variant: 'error' })) }, [refresh, showAlert])

  if (!company) return <Heading level={1}>No company available</Heading>
  const isOwner = company.role === 'owner'
  const endpoint = (id?: string) => apiEndpoint(`/agent-runs/companies/${company.id}/local-agents${id ? `/${id}` : ''}`)
  const notify = (title: string) => showAlert({ title, description: 'The company local agent configuration is up to date.', variant: 'success' })

  return <>
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div><p className="m-0 text-xs font-bold tracking-[0.12em] text-accent uppercase">Settings</p><Heading level={1} className="mt-2 mb-0 text-3xl font-bold text-heading sm:text-4xl">Local Agents</Heading><p className="mt-3 mb-0 text-sm text-muted">Add and configure multiple local coding agents for your company.</p></div>
      {isOwner && <Button onPress={() => setAdding((current) => !current)} className={buttonStyles}><Plus aria-hidden="true" size={17} />Add agent</Button>}
    </header>
    {companies.length > 1 && <label className="mt-6 grid max-w-sm gap-2 text-sm font-bold text-heading">Company<select value={company.id} onChange={(event) => setCompanyId(event.target.value)} className={inputStyles}>{companies.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>}
    {adding && <section className="mt-6 rounded-xl border border-accent/40 bg-surface p-6 shadow-sm"><Heading level={2} className="mt-0 text-lg font-bold text-heading">New local agent</Heading><AgentForm initial={blankAgent} submitLabel="Create agent" onSubmit={async (value) => { const { data } = await createApi.post(endpoint(), value); setAgents((current) => [...current.map((item) => data.isDefault ? { ...item, isDefault: false } : item), data]); setAdding(false); notify('Agent created') }} /></section>}
    <div className="mt-6 grid gap-5">
      {agents.map((agent) => <section key={agent.id} className="rounded-xl border border-border bg-surface p-6 shadow-sm">
        <div className="mb-5 flex items-center justify-between gap-3"><div className="flex items-center gap-3"><span className="grid size-10 place-items-center rounded-lg bg-surface-muted text-accent"><Bot aria-hidden="true" size={20} /></span><div><Heading level={2} className="m-0 text-lg font-bold text-heading">{agent.name}</Heading><p className="m-0 text-xs text-muted capitalize">{agent.provider} · {agent.enabled ? 'Enabled' : 'Disabled'}{agent.isDefault ? ' · Default' : ''}</p></div></div>{isOwner && <ConfirmActionDialog triggerLabel="Delete" title={`Delete ${agent.name}?`} description="This removes the configuration from the company. Existing run history remains available." confirmLabel="Delete agent" onConfirm={async () => { await deleteApi.delete(endpoint(agent.id)); await refresh(); notify('Agent deleted') }} />}</div>
        {isOwner ? <AgentForm initial={agent} submitLabel="Save agent" onSubmit={async (value) => {
          const changes = changedAgentFields(agent, value)
          if (Object.keys(changes).length === 0) return
          const { data } = await updateApi.patch(endpoint(agent.id), changes)
          setAgents((current) => current.map((item) =>
            item.id === data.id
              ? data
              : data.isDefault
                ? { ...item, isDefault: false }
                : item
          ))
          notify('Agent saved')
        }} /> : <p className="m-0 text-sm text-muted">Only company owners can change this agent.</p>}
      </section>)}
      {!agents.length && !adding && <p className="rounded-xl border border-dashed border-border bg-surface p-8 text-center text-sm text-muted">No local agents have been configured for this company.</p>}
    </div>
  </>
}
