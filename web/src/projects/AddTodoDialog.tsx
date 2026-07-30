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
import type { NewTodo } from './types'

type AddTodoDialogProps = {
  versionName: string
  onAddTodo: (todo: NewTodo) => Promise<void>
}

const buttonStyles =
  'inline-flex min-h-9 cursor-pointer items-center justify-center gap-2 rounded-lg px-3 text-xs font-bold transition-colors data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:cursor-not-allowed disabled:opacity-50'

export function AddTodoDialog({
  versionName,
  onAddTodo,
}: AddTodoDialogProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const resetForm = () => {
    setTitle('')
    setDescription('')
  }

  return (
    <DialogTrigger>
      <Button
        className={`${buttonStyles} border border-border bg-surface text-heading data-[hovered]:bg-surface-muted`}
      >
        <Plus aria-hidden="true" size={15} strokeWidth={2.2} />
        Add todo
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
                  Add a todo
                </Heading>
                <p className="mt-2 mb-6 text-sm leading-6 text-muted">
                  Create a draft GitHub issue-style todo for {versionName}.
                </p>

                <Form
                  className="grid gap-5"
                  onSubmit={async (event) => {
                    event.preventDefault()

                    if (!title.trim() || !description.trim()) {
                      return
                    }

                    setIsSubmitting(true)

                    try {
                      await onAddTodo({
                        title: title.trim(),
                        description: description.trim(),
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
                    name="todo-title"
                    value={title}
                    onChange={setTitle}
                    isRequired
                    className="grid gap-2"
                  >
                    <Label className="text-sm font-bold text-heading">
                      Title
                    </Label>
                    <Input
                      autoFocus
                      placeholder="Summarize the issue"
                      className="w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-heading outline-none data-[focused]:border-accent data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus"
                    />
                    <FieldError className="text-xs text-red-500" />
                  </TextField>

                  <TextField
                    name="todo-description"
                    value={description}
                    onChange={setDescription}
                    isRequired
                    className="grid gap-2"
                  >
                    <Label className="text-sm font-bold text-heading">
                      Description
                    </Label>
                    <TextArea
                      rows={5}
                      placeholder="Add context, acceptance criteria, or implementation notes."
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
                        isSubmitting ||
                        !title.trim() ||
                        !description.trim()
                      }
                      className={`${buttonStyles} bg-accent px-4 text-white data-[hovered]:bg-accent-hover`}
                    >
                      {isSubmitting ? 'Adding…' : 'Add todo'}
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
