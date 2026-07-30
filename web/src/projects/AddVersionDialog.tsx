import { Plus } from 'lucide-react'
import { useState } from 'react'
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
  TextArea,
  TextField,
} from 'react-aria-components'
import type { NewVersion } from './types'

type AddVersionDialogProps = {
  projectName: string
  onAddVersion: (version: NewVersion) => Promise<void>
}

const buttonStyles =
  'inline-flex min-h-10 cursor-pointer items-center justify-center gap-2 rounded-lg px-4 text-sm font-bold transition-colors data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:cursor-not-allowed disabled:opacity-50'

export function AddVersionDialog({
  projectName,
  onAddVersion,
}: AddVersionDialogProps) {
  const [name, setName] = useState('')
  const [summary, setSummary] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const resetForm = () => {
    setName('')
    setSummary('')
  }

  return (
    <DialogTrigger>
      <Button
        className={`${buttonStyles} shrink-0 border border-border bg-surface text-heading data-[hovered]:bg-surface-muted`}
      >
        <Plus aria-hidden="true" size={17} strokeWidth={2.2} />
        Add version
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
                  Add a version
                </Heading>
                <p className="mt-2 mb-6 text-sm leading-6 text-muted">
                  Create the next roadmap version for {projectName}.
                </p>

                <Form
                  className="grid gap-5"
                  onSubmit={async (event) => {
                    event.preventDefault()

                    if (!name.trim() || !summary.trim()) {
                      return
                    }

                    setIsSubmitting(true)

                    try {
                      await onAddVersion({
                        name: name.trim(),
                        summary: summary.trim(),
                      })
                      closeDialog()
                    } catch {
                      // The projects provider displays the request failure.
                    } finally {
                      setIsSubmitting(false)
                    }
                  }}
                >
                  <TextField
                    name="version-name"
                    value={name}
                    onChange={setName}
                    isRequired
                    className="grid gap-2"
                  >
                    <Label className="text-sm font-bold text-heading">
                      Version
                    </Label>
                    <Input
                      autoFocus
                      placeholder="e.g. v2.3"
                      className="w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-heading outline-none data-[focused]:border-accent data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus"
                    />
                    <FieldError className="text-xs text-red-500" />
                  </TextField>

                  <TextField
                    name="version-summary"
                    value={summary}
                    onChange={setSummary}
                    isRequired
                    className="grid gap-2"
                  >
                    <Label className="text-sm font-bold text-heading">
                      Summary
                    </Label>
                    <TextArea
                      rows={4}
                      placeholder="Describe the goal of this release."
                      className="w-full resize-y rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-heading outline-none data-[focused]:border-accent data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus"
                    />
                    <FieldError className="text-xs text-red-500" />
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
                        isSubmitting || !name.trim() || !summary.trim()
                      }
                      className={`${buttonStyles} bg-accent text-white data-[hovered]:bg-accent-hover`}
                    >
                      {isSubmitting ? 'Adding…' : 'Add version'}
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
