import { Building2, LoaderCircle, Save } from 'lucide-react'
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
import { useAccount } from '../account'

const inputStyles =
  'w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-heading outline-none data-[focused]:border-accent data-[invalid]:border-red-500 data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-muted'

const buttonStyles =
  'inline-flex min-h-10 cursor-pointer items-center justify-center gap-2 rounded-lg bg-accent px-4 text-sm font-bold text-white transition-colors data-[hovered]:bg-accent-hover data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:cursor-not-allowed disabled:opacity-50'

export function CompanySettingsPage() {
  const { companies, updateCompany } = useAccount()
  const [companyId, setCompanyId] = useState(companies[0]?.id ?? '')
  const company =
    companies.find(({ id }) => id === companyId) ?? companies[0]
  const [name, setName] = useState(company?.name ?? '')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (company) {
      setCompanyId(company.id)
      setName(company.name)
    }
  }, [company])

  if (!company) {
    return (
      <section className="rounded-xl border border-dashed border-border bg-surface p-10 text-center">
        <Heading level={1} className="m-0 text-xl font-bold text-heading">
          No company available
        </Heading>
        <p className="mt-2 mb-0 text-sm text-muted">
          Create a company during onboarding to manage its settings.
        </p>
      </section>
    )
  }

  const trimmedName = name.trim()
  const isOwner = company.role === 'owner'
  const hasChanges = trimmedName !== company.name

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
          Company
        </Heading>
        <p className="mt-3 mb-0 max-w-2xl text-sm leading-6 text-muted sm:text-base">
          Manage company details and review workspace membership.
        </p>
      </header>

      <section
        aria-labelledby="company-details-title"
        className="mt-8 max-w-3xl rounded-xl border border-border bg-surface shadow-sm"
      >
        <header className="flex items-start gap-3 border-b border-border px-6 py-5">
          <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-surface-muted text-accent">
            <Building2 aria-hidden="true" size={19} strokeWidth={2.2} />
          </span>
          <div>
            <Heading
              id="company-details-title"
              level={2}
              className="m-0 text-lg font-bold text-heading"
            >
              Company details
            </Heading>
            <p className="mt-1 mb-0 text-sm text-muted">
              Owners can update the company name.
            </p>
          </div>
        </header>

        <Form
          className="grid gap-6 p-6"
          onSubmit={async (event) => {
            event.preventDefault()
            if (!isOwner || !trimmedName || !hasChanges) {
              return
            }

            setIsSaving(true)
            try {
              await updateCompany(company.id, { name: trimmedName })
            } catch {
              // The account provider displays request feedback.
            } finally {
              setIsSaving(false)
            }
          }}
        >
          {companies.length > 1 && (
            <div className="grid gap-2">
              <label
                htmlFor="company-selector"
                className="text-sm font-bold text-heading"
              >
                Company
              </label>
              <select
                id="company-selector"
                value={company.id}
                onChange={(event) => setCompanyId(event.target.value)}
                className="min-h-11 w-full rounded-lg border border-border bg-surface px-3 text-sm text-heading outline-none focus-visible:border-accent focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-focus"
              >
                {companies.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <TextField
            name="company-name"
            value={name}
            onChange={setName}
            isReadOnly={!isOwner}
            isRequired
            className="grid gap-2"
          >
            <Label className="text-sm font-bold text-heading">
              Company name
            </Label>
            <Input maxLength={120} className={inputStyles} />
            <FieldError className="text-xs text-red-500" />
            {!isOwner && (
              <p className="m-0 text-xs leading-5 text-muted">
                Only a company owner can change these details.
              </p>
            )}
          </TextField>

          <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-lg bg-surface-muted p-4">
              <dt className="text-xs font-bold tracking-wide text-muted uppercase">
                Your role
              </dt>
              <dd className="mt-1 ml-0 text-sm font-bold text-heading capitalize">
                {company.role}
              </dd>
            </div>
            <div className="rounded-lg bg-surface-muted p-4">
              <dt className="text-xs font-bold tracking-wide text-muted uppercase">
                Members
              </dt>
              <dd className="mt-1 ml-0 text-sm font-bold text-heading">
                {company.memberCount}
              </dd>
            </div>
            <div className="rounded-lg bg-surface-muted p-4">
              <dt className="text-xs font-bold tracking-wide text-muted uppercase">
                Projects
              </dt>
              <dd className="mt-1 ml-0 text-sm font-bold text-heading">
                {company.projectCount}
              </dd>
            </div>
          </dl>

          {isOwner && (
            <div className="flex justify-end border-t border-border pt-5">
              <Button
                type="submit"
                isDisabled={isSaving || !trimmedName || !hasChanges}
                className={buttonStyles}
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
          )}
        </Form>
      </section>
    </>
  )
}
