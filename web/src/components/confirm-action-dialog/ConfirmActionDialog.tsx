import {
  AlertTriangle,
  CheckCircle2,
  LoaderCircle,
  Trash2,
} from 'lucide-react'
import { useState } from 'react'
import {
  Button,
  Dialog,
  DialogTrigger,
  Heading,
  Input,
  Label,
  Modal,
  TextField,
} from 'react-aria-components'

type ConfirmActionDialogProps = {
  triggerLabel: string
  triggerAriaLabel?: string
  title: string
  description: string
  confirmLabel: string
  onConfirm: () => Promise<void>
  tone?: 'danger' | 'primary'
  confirmationText?: string
}

const buttonStyles =
  'inline-flex min-h-9 cursor-pointer items-center justify-center gap-2 rounded-lg px-3 text-xs font-bold transition-colors data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:cursor-wait disabled:opacity-60'

export function ConfirmActionDialog({
  triggerLabel,
  triggerAriaLabel,
  title,
  description,
  confirmLabel,
  onConfirm,
  tone = 'danger',
  confirmationText,
}: ConfirmActionDialogProps) {
  const [isConfirming, setIsConfirming] = useState(false)
  const [confirmationValue, setConfirmationValue] = useState('')
  const isDanger = tone === 'danger'
  const TriggerIcon = isDanger ? Trash2 : CheckCircle2
  const DialogIcon = isDanger ? AlertTriangle : CheckCircle2

  return (
    <DialogTrigger
      onOpenChange={(isOpen) => {
        if (!isOpen) {
          setConfirmationValue('')
        }
      }}
    >
      <Button
        aria-label={triggerAriaLabel}
        className={`${buttonStyles} border ${
          isDanger
            ? 'border-red-500/40 bg-red-500/10 text-red-500 data-[hovered]:bg-red-500/20'
            : 'border-border bg-surface text-heading data-[hovered]:bg-surface-muted'
        }`}
      >
        <TriggerIcon aria-hidden="true" size={15} strokeWidth={2.2} />
        {triggerLabel}
      </Button>

      <Modal className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-slate-950/70 p-4 backdrop-blur-sm">
        <Dialog className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-2xl outline-none">
          {({ close }) => (
            <>
              <span
                className={`grid size-11 place-items-center rounded-xl ${
                  isDanger
                    ? 'bg-red-500/10 text-red-500'
                    : 'bg-accent/10 text-accent'
                }`}
              >
                <DialogIcon aria-hidden="true" size={22} strokeWidth={2.2} />
              </span>
              <Heading
                slot="title"
                className="mt-4 mb-0 text-xl font-bold tracking-[-0.025em] text-heading"
              >
                {title}
              </Heading>
              <p className="mt-2 mb-0 text-sm leading-6 text-muted">
                {description}
              </p>
              {confirmationText && (
                <TextField
                  value={confirmationValue}
                  onChange={setConfirmationValue}
                  className="mt-5 grid gap-2"
                >
                  <Label className="text-sm font-bold text-heading">
                    Type <span className="font-mono">{confirmationText}</span> to confirm
                  </Label>
                  <Input
                    autoComplete="off"
                    spellCheck={false}
                    className="w-full rounded-lg border border-border bg-surface px-3 py-2.5 font-mono text-sm text-heading outline-none data-[focused]:border-red-500 data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus"
                  />
                </TextField>
              )}

              <div className="mt-6 flex justify-end gap-3">
                <Button
                  onPress={close}
                  isDisabled={isConfirming}
                  className={`${buttonStyles} min-h-10 border border-border bg-surface px-4 text-sm text-heading data-[hovered]:bg-surface-muted`}
                >
                  Cancel
                </Button>
                <Button
                  isDisabled={
                    isConfirming ||
                    Boolean(
                      confirmationText &&
                        confirmationValue !== confirmationText,
                    )
                  }
                  onPress={async () => {
                    setIsConfirming(true)

                    try {
                      await onConfirm()
                      close()
                    } catch {
                      // The calling provider displays the request failure.
                    } finally {
                      setIsConfirming(false)
                    }
                  }}
                  className={`${buttonStyles} min-h-10 px-4 text-sm text-white ${
                    isDanger
                      ? 'bg-red-500 data-[hovered]:bg-red-600'
                      : 'bg-accent data-[hovered]:bg-accent-hover'
                  }`}
                >
                  {isConfirming && (
                    <LoaderCircle
                      aria-hidden="true"
                      className="motion-safe:animate-spin"
                      size={16}
                      strokeWidth={2.2}
                    />
                  )}
                  {isConfirming ? 'Confirming…' : confirmLabel}
                </Button>
              </div>
            </>
          )}
        </Dialog>
      </Modal>
    </DialogTrigger>
  )
}
