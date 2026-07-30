import { Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  Button,
  Dialog,
  DialogTrigger,
  FieldError,
  Form,
  Heading,
  Input,
  Label,
  Modal,
  TextField,
} from 'react-aria-components'
import type { Company } from '../account'
import { isAbsoluteFolderPath } from '../utilities/isAbsoluteFolderPath'
import type { NewProject } from './types'

type CreateProjectDialogProps = {
  companies: Company[]
  onCreate: (project: NewProject) => Promise<void>
}

const buttonStyles =
  'inline-flex min-h-10 cursor-pointer items-center justify-center gap-2 rounded-lg px-4 text-sm font-bold transition-colors data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:cursor-not-allowed disabled:opacity-50'

export function CreateProjectDialog({
  companies,
  onCreate,
}: CreateProjectDialogProps) {
  const [companyId, setCompanyId] = useState(companies[0]?.id ?? '')
  const [name, setName] = useState('')
  const [folderPath, setFolderPath] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (!companyId && companies[0]) {
      setCompanyId(companies[0].id)
    }
  }, [companies, companyId])

  const resetForm = () => {
    setCompanyId(companies[0]?.id ?? '')
    setName('')
    setFolderPath('')
  }

  const hasValidFolderPath = isAbsoluteFolderPath(folderPath)

  return (
    <DialogTrigger>
      <Button
        className={`${buttonStyles} w-full bg-accent text-white data-[hovered]:bg-accent-hover`}
      >
        <Plus aria-hidden="true" size={17} strokeWidth={2.2} />
        New project
      </Button>

      <Modal className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-slate-950/70 p-4 backdrop-blur-sm">
        <Dialog className="w-full max-w-lg rounded-2xl border border-border bg-surface p-6 shadow-2xl outline-none">
          {({ close }) => {
            const closeDialog = () => {
              resetForm()
              close()
            }

            return (
              <>
                <Heading
                  slot="title"
                  className="m-0 text-2xl font-bold tracking-[-0.03em] text-heading"
                >
                  Create a project
                </Heading>
                <p className="mt-2 mb-6 text-sm leading-6 text-muted">
                  Add a local project folder to begin planning its roadmap.
                </p>

                <Form
                  className="grid gap-5"
                  onSubmit={async (event) => {
                    event.preventDefault()

                    if (!companyId || !name.trim() || !hasValidFolderPath) {
                      return
                    }

                    setIsSubmitting(true)

                    try {
                      await onCreate({
                        companyId,
                        name: name.trim(),
                        path: folderPath.trim(),
                      })
                      closeDialog()
                    } catch {
                      // The projects provider displays the request failure.
                    } finally {
                      setIsSubmitting(false)
                    }
                  }}
                >
                  <div className="grid gap-2">
                    <label
                      htmlFor="project-company"
                      className="text-sm font-bold text-heading"
                    >
                      Company
                    </label>
                    <select
                      id="project-company"
                      name="project-company"
                      value={companyId}
                      onChange={(event) => setCompanyId(event.target.value)}
                      required
                      className="min-h-10 rounded-lg border border-border bg-surface px-3 text-sm text-heading outline-none focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-focus"
                    >
                      {companies.length === 0 && (
                        <option value="">Create a company first</option>
                      )}
                      {companies.map((company) => (
                        <option key={company.id} value={company.id}>
                          {company.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <TextField
                    name="project-name"
                    value={name}
                    onChange={setName}
                    isRequired
                    className="grid gap-2"
                  >
                    <Label className="text-sm font-bold text-heading">
                      Project name
                    </Label>
                    <Input
                      autoFocus
                      placeholder="e.g. Mobile app"
                      className="w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-heading outline-none data-[focused]:border-accent data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus"
                    />
                    <FieldError className="text-xs text-red-500" />
                  </TextField>

                  <TextField
                    name="project-folder"
                    value={folderPath}
                    onChange={setFolderPath}
                    isRequired
                    isInvalid={
                      folderPath.trim().length > 0 && !hasValidFolderPath
                    }
                    className="grid gap-2"
                  >
                    <Label className="text-sm font-bold text-heading">
                      Project folder
                    </Label>
                    <Input
                      placeholder="/Users/you/Projects/mobile-app"
                      autoComplete="off"
                      spellCheck={false}
                      maxLength={2048}
                      className="w-full rounded-lg border border-border bg-surface px-3 py-2.5 font-mono text-sm text-heading outline-none data-[focused]:border-accent data-[invalid]:border-red-500 data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus"
                    />
                    <FieldError className="text-xs text-red-500">
                      Enter an absolute folder path.
                    </FieldError>
                    <p className="m-0 text-xs leading-5 text-muted">
                      Enter the full folder path. Only the path is submitted;
                      no files are selected or uploaded.
                    </p>
                  </TextField>

                  <div className="mt-1 flex justify-end gap-3">
                    <Button
                      type="button"
                      onPress={closeDialog}
                      isDisabled={isSubmitting}
                      className={`${buttonStyles} border border-border bg-surface text-heading data-[hovered]:bg-surface-muted`}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      isDisabled={
                        isSubmitting ||
                        !companyId ||
                        !name.trim() ||
                        !hasValidFolderPath
                      }
                      className={`${buttonStyles} bg-accent text-white data-[hovered]:bg-accent-hover`}
                    >
                      {isSubmitting ? 'Creating…' : 'Create project'}
                    </Button>
                  </div>
                </Form>
              </>
            )
          }}
        </Dialog>
      </Modal>
    </DialogTrigger>
  )
}
