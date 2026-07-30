import { ArrowRightToLine } from 'lucide-react'
import { useState } from 'react'
import {
  Button,
  Dialog,
  DialogTrigger,
  Form,
  Heading,
  Modal,
} from 'react-aria-components'
import type { ProjectVersion } from './types'

type AssignTodoDialogProps = {
  todoId: string
  todoTitle: string
  versions: Pick<ProjectVersion, 'id' | 'name'>[]
  onAssign: (todoId: string, versionId: string) => Promise<void>
}

const buttonStyles =
  'inline-flex min-h-9 cursor-pointer items-center justify-center gap-2 rounded-lg px-3 text-xs font-bold transition-colors data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:cursor-not-allowed disabled:opacity-50'

export function AssignTodoDialog({
  todoId,
  todoTitle,
  versions,
  onAssign,
}: AssignTodoDialogProps) {
  const [selectedVersionId, setSelectedVersionId] = useState(
    versions[0]?.id ?? '',
  )
  const [isSubmitting, setIsSubmitting] = useState(false)
  const activeVersionId = versions.some(
    (version) => version.id === selectedVersionId,
  )
    ? selectedVersionId
    : (versions[0]?.id ?? '')

  return (
    <DialogTrigger>
      <Button
        isDisabled={versions.length === 0}
        aria-label={`Assign ${todoTitle} to a version`}
        aria-description={
          versions.length === 0
            ? 'No pending or in-progress versions are available.'
            : undefined
        }
        className={`${buttonStyles} border border-accent bg-accent text-white data-[hovered]:bg-accent-hover`}
      >
        <ArrowRightToLine aria-hidden="true" size={15} strokeWidth={2.2} />
        Assign
      </Button>

      <Modal className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-slate-950/70 p-4 backdrop-blur-sm">
        <Dialog className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl outline-none">
          {({ close }) => (
            <>
              <Heading
                slot="title"
                className="m-0 text-2xl font-bold tracking-[-0.03em] text-heading"
              >
                Assign todo
              </Heading>
              <p className="mt-2 mb-6 text-sm leading-6 text-muted">
                Move <span className="font-bold text-heading">{todoTitle}</span>{' '}
                into an active version.
              </p>

              <Form
                className="grid gap-5"
                onSubmit={async (event) => {
                  event.preventDefault()

                  if (!activeVersionId) {
                    return
                  }

                  setIsSubmitting(true)

                  try {
                    await onAssign(todoId, activeVersionId)
                    close()
                  } catch {
                    // The projects provider displays the request failure.
                  } finally {
                    setIsSubmitting(false)
                  }
                }}
              >
                <div className="grid gap-2">
                  <label
                    htmlFor={`assign-${todoId}-version`}
                    className="text-sm font-bold text-heading"
                  >
                    Version
                  </label>
                  <select
                    id={`assign-${todoId}-version`}
                    name="version"
                    value={activeVersionId}
                    onChange={(event) =>
                      setSelectedVersionId(event.target.value)
                    }
                    className="min-h-10 rounded-lg border border-border bg-surface px-3 text-sm text-heading outline-none focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-focus"
                  >
                    {versions.map((version) => (
                      <option key={version.id} value={version.id}>
                        {version.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex justify-end gap-3">
                  <Button
                    type="button"
                    onPress={close}
                    isDisabled={isSubmitting}
                    className={`${buttonStyles} border border-border bg-surface text-heading data-[hovered]:bg-surface-muted`}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    isDisabled={isSubmitting}
                    className={`${buttonStyles} bg-accent px-4 text-white data-[hovered]:bg-accent-hover`}
                  >
                    {isSubmitting ? 'Assigning…' : 'Assign'}
                  </Button>
                </div>
              </Form>
            </>
          )}
        </Dialog>
      </Modal>
    </DialogTrigger>
  )
}
