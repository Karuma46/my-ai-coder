import { ArrowLeft, FolderCog, LoaderCircle, Save } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  Button,
  FieldError,
  Form,
  Heading,
  Input,
  Label,
  TextField,
} from 'react-aria-components'
import { Link, Navigate, useParams } from 'react-router'
import { isAbsoluteFolderPath } from '../utilities/isAbsoluteFolderPath'
import type { Project, UpdateProject } from './types'
import { useProjects } from './useProjects'

type ProjectSettingsFormProps = {
  project: Project
  onSave: (changes: UpdateProject) => Promise<void>
}

const inputStyles =
  'w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-heading outline-none data-[focused]:border-accent data-[invalid]:border-red-500 data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus'

const buttonStyles =
  'inline-flex min-h-10 cursor-pointer items-center justify-center gap-2 rounded-lg px-4 text-sm font-bold transition-colors data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:cursor-not-allowed disabled:opacity-50'

function ProjectSettingsForm({
  project,
  onSave,
}: ProjectSettingsFormProps) {
  const [name, setName] = useState(project.name)
  const [folderPath, setFolderPath] = useState(project.path)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    setName(project.name)
    setFolderPath(project.path)
  }, [project.name, project.path])

  const trimmedName = name.trim()
  const trimmedPath = folderPath.trim()
  const hasValidFolderPath = isAbsoluteFolderPath(folderPath)
  const hasChanges =
    trimmedName !== project.name || trimmedPath !== project.path

  const resetForm = () => {
    setName(project.name)
    setFolderPath(project.path)
  }

  return (
    <Form
      className="grid gap-6"
      onSubmit={async (event) => {
        event.preventDefault()

        if (!trimmedName || !hasValidFolderPath || !hasChanges) {
          return
        }

        setIsSaving(true)

        try {
          await onSave({
            name: trimmedName,
            path: trimmedPath,
          })
        } catch {
          // The projects provider displays the request failure.
        } finally {
          setIsSaving(false)
        }
      }}
    >
      <TextField
        name="project-name"
        value={name}
        onChange={setName}
        isRequired
        className="grid gap-2"
      >
        <Label className="text-sm font-bold text-heading">Project name</Label>
        <Input
          autoFocus
          maxLength={120}
          className={inputStyles}
        />
        <FieldError className="text-xs text-red-500" />
        <p className="m-0 text-xs leading-5 text-muted">
          This name appears throughout the roadmap and navigation.
        </p>
      </TextField>

      <TextField
        name="project-folder"
        value={folderPath}
        onChange={setFolderPath}
        isRequired
        isInvalid={trimmedPath.length > 0 && !hasValidFolderPath}
        className="grid gap-2"
      >
        <Label className="text-sm font-bold text-heading">Project folder</Label>
        <Input
          autoComplete="off"
          spellCheck={false}
          maxLength={2048}
          className={`${inputStyles} font-mono`}
        />
        <FieldError className="text-xs text-red-500">
          Enter an absolute folder path.
        </FieldError>
        <p className="m-0 text-xs leading-5 text-muted">
          Only the absolute path is stored. No files are selected or uploaded.
        </p>
      </TextField>

      <div className="flex flex-wrap justify-end gap-3 border-t border-border pt-5">
        <Button
          type="button"
          onPress={resetForm}
          isDisabled={isSaving || !hasChanges}
          className={`${buttonStyles} border border-border bg-surface text-heading data-[hovered]:bg-surface-muted`}
        >
          Reset
        </Button>
        <Button
          type="submit"
          isDisabled={
            isSaving || !trimmedName || !hasValidFolderPath || !hasChanges
          }
          className={`${buttonStyles} bg-accent text-white data-[hovered]:bg-accent-hover`}
        >
          {isSaving ? (
            <LoaderCircle
              aria-hidden="true"
              className="motion-safe:animate-spin"
              size={17}
              strokeWidth={2.2}
            />
          ) : (
            <Save aria-hidden="true" size={17} strokeWidth={2.2} />
          )}
          {isSaving ? 'Saving…' : 'Save changes'}
        </Button>
      </div>
    </Form>
  )
}

export function ProjectSettingsPage() {
  const { projectId } = useParams()
  const { projects, isLoading, hasLoadError, updateProject } = useProjects()
  const project = projects.find(({ id }) => id === projectId)

  if (isLoading) {
    return (
      <p
        role="status"
        className="rounded-xl border border-border bg-surface p-6 text-sm text-muted shadow-sm"
      >
        Loading project settings…
      </p>
    )
  }

  if (!projectId) {
    return <Navigate to="/projects" replace />
  }

  if (!project) {
    return (
      <section className="rounded-xl border border-dashed border-border bg-surface p-10 text-center">
        <Heading level={1} className="m-0 text-xl font-bold text-heading">
          Project unavailable
        </Heading>
        <p className="mt-2 mb-0 text-sm text-muted">
          {hasLoadError
            ? 'Project settings could not be loaded. Check the API and try again.'
            : 'This project could not be found.'}
        </p>
        <Link
          to="/projects"
          className="mt-5 inline-flex min-h-10 items-center justify-center rounded-lg bg-accent px-4 text-sm font-bold text-white no-underline focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-focus"
        >
          Back to projects
        </Link>
      </section>
    )
  }

  return (
    <>
      <Link
        to={`/projects/${project.id}`}
        className="inline-flex min-h-10 items-center gap-2 rounded-lg text-sm font-bold text-muted no-underline transition-colors hover:text-heading focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-focus"
      >
        <ArrowLeft aria-hidden="true" size={17} strokeWidth={2.2} />
        Back to roadmap
      </Link>

      <header className="mt-5">
        <p className="m-0 text-xs font-bold tracking-[0.12em] text-accent uppercase">
          Project settings
        </p>
        <Heading
          level={1}
          className="mt-2 mb-0 text-3xl font-bold tracking-[-0.035em] text-heading sm:text-4xl"
        >
          {project.name}
        </Heading>
        <p className="mt-3 mb-0 max-w-2xl text-sm leading-6 text-muted sm:text-base">
          Update the project details used across its roadmap.
        </p>
      </header>

      <section
        aria-labelledby="project-details-title"
        className="mt-8 max-w-3xl rounded-xl border border-border bg-surface shadow-sm"
      >
        <header className="flex items-start gap-3 border-b border-border px-6 py-5">
          <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-surface-muted text-accent">
            <FolderCog aria-hidden="true" size={19} strokeWidth={2.2} />
          </span>
          <div>
            <Heading
              id="project-details-title"
              level={2}
              className="m-0 text-lg font-bold text-heading"
            >
              Project details
            </Heading>
            <p className="mt-1 mb-0 text-sm text-muted">
              Change the display name or local folder reference.
            </p>
          </div>
        </header>

        <div className="p-6">
          <ProjectSettingsForm
            project={project}
            onSave={(changes) => updateProject(project.id, changes)}
          />
        </div>
      </section>
    </>
  )
}
