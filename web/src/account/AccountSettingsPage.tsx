import { LoaderCircle, Save, UserRoundCog } from 'lucide-react'
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
import { useAccount } from './useAccount'

const inputStyles =
  'w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-heading outline-none data-[focused]:border-accent data-[invalid]:border-red-500 data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-muted'

const buttonStyles =
  'inline-flex min-h-10 cursor-pointer items-center justify-center gap-2 rounded-lg px-4 text-sm font-bold transition-colors data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:cursor-not-allowed disabled:opacity-50'

export function AccountSettingsPage() {
  const { user, updateProfile } = useAccount()
  const [name, setName] = useState(user?.name ?? '')
  const [avatarUrl, setAvatarUrl] = useState(user?.avatarUrl ?? '')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    setName(user?.name ?? '')
    setAvatarUrl(user?.avatarUrl ?? '')
  }, [user])

  if (!user) {
    return null
  }

  const trimmedName = name.trim()
  const trimmedAvatarUrl = avatarUrl.trim()
  const hasChanges =
    trimmedName !== user.name ||
    trimmedAvatarUrl !== (user.avatarUrl ?? '')

  return (
    <>
      <header>
        <p className="m-0 text-xs font-bold tracking-[0.12em] text-accent uppercase">
          Settings
        </p>
        <Heading
          level={1}
          className="mt-2 mb-0 text-3xl font-bold tracking-[-0.035em] text-heading sm:text-4xl"
        >
          Account Settings
        </Heading>
        <p className="mt-3 mb-0 max-w-2xl text-sm leading-6 text-muted sm:text-base">
          Manage the profile details shown throughout your workspace.
        </p>
      </header>

      <section
        aria-labelledby="profile-details-title"
        className="mt-8 max-w-3xl rounded-xl border border-border bg-surface shadow-sm"
      >
        <header className="flex items-start gap-3 border-b border-border px-6 py-5">
          <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-surface-muted text-accent">
            <UserRoundCog aria-hidden="true" size={19} strokeWidth={2.2} />
          </span>
          <div>
            <Heading
              id="profile-details-title"
              level={2}
              className="m-0 text-lg font-bold text-heading"
            >
              Profile details
            </Heading>
            <p className="mt-1 mb-0 text-sm text-muted">
              Update your name and optional profile image.
            </p>
          </div>
        </header>

        <Form
          className="grid gap-6 p-6"
          onSubmit={async (event) => {
            event.preventDefault()
            if (!trimmedName || !hasChanges) {
              return
            }

            setIsSaving(true)
            try {
              await updateProfile({
                name: trimmedName,
                avatarUrl: trimmedAvatarUrl || null,
              })
            } catch {
              // The account provider displays request feedback.
            } finally {
              setIsSaving(false)
            }
          }}
        >
          <TextField
            name="account-name"
            value={name}
            onChange={setName}
            isRequired
            className="grid gap-2"
          >
            <Label className="text-sm font-bold text-heading">
              Full name
            </Label>
            <Input autoComplete="name" maxLength={120} className={inputStyles} />
            <FieldError className="text-xs text-red-500" />
          </TextField>

          <TextField
            name="account-email"
            value={user.email}
            isReadOnly
            className="grid gap-2"
          >
            <Label className="text-sm font-bold text-heading">
              Email address
            </Label>
            <Input
              type="email"
              autoComplete="email"
              className={inputStyles}
            />
            <p className="m-0 text-xs leading-5 text-muted">
              Your sign-in email cannot be changed here.
            </p>
          </TextField>

          <TextField
            name="account-avatar"
            value={avatarUrl}
            onChange={setAvatarUrl}
            type="url"
            className="grid gap-2"
          >
            <Label className="text-sm font-bold text-heading">
              Profile image URL
            </Label>
            <Input
              type="url"
              autoComplete="url"
              placeholder="https://example.com/avatar.jpg"
              className={inputStyles}
            />
            <FieldError className="text-xs text-red-500" />
            <p className="m-0 text-xs leading-5 text-muted">
              Leave this blank to use your initials.
            </p>
          </TextField>

          <div className="flex flex-wrap justify-end gap-3 border-t border-border pt-5">
            <Button
              type="button"
              onPress={() => {
                setName(user.name)
                setAvatarUrl(user.avatarUrl ?? '')
              }}
              isDisabled={isSaving || !hasChanges}
              className={`${buttonStyles} border border-border bg-surface text-heading data-[hovered]:bg-surface-muted`}
            >
              Reset
            </Button>
            <Button
              type="submit"
              isDisabled={isSaving || !trimmedName || !hasChanges}
              className={`${buttonStyles} bg-accent text-white data-[hovered]:bg-accent-hover`}
            >
              {isSaving ? (
                <LoaderCircle
                  aria-hidden="true"
                  className="motion-safe:animate-spin"
                  size={17}
                />
              ) : (
                <Save aria-hidden="true" size={17} />
              )}
              {isSaving ? 'Saving…' : 'Save changes'}
            </Button>
          </div>
        </Form>
      </section>
    </>
  )
}
