import axios from 'axios'
import {
  ArrowRight,
  Building2,
  Check,
  FolderKanban,
  LoaderCircle,
  UserRoundPlus,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  Button,
  FieldError,
  Form,
  Input,
  Label,
  TextField,
} from 'react-aria-components'
import { Link, useNavigate } from 'react-router'
import type { Company, TokenResponse } from '../account'
import { useAccount } from '../account'
import { AuthShell } from '../components/auth-shell'
import type { Project } from '../projects/types'
import { useAlerts } from '../utilities/alerts'
import { apiEndpoint } from '../utilities/apiEndpoint'
import { isAbsoluteFolderPath } from '../utilities/isAbsoluteFolderPath'
import { useApi } from '../utilities/useApi'

type OnboardingStep = 'account' | 'company' | 'project'

const steps: Array<{
  id: OnboardingStep
  label: string
}> = [
  { id: 'account', label: 'Account' },
  { id: 'company', label: 'Company' },
  { id: 'project', label: 'First project' },
]

const inputStyles =
  'w-full rounded-xl border border-border bg-surface px-3 py-3 text-sm text-heading outline-none data-[focused]:border-accent data-[invalid]:border-red-500 data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus'

const submitStyles =
  'inline-flex min-h-12 w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-accent px-5 text-sm font-bold text-white transition-colors data-[hovered]:bg-accent-hover data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:cursor-not-allowed disabled:opacity-60'

function StepProgress({ currentStep }: { currentStep: OnboardingStep }) {
  const currentIndex = steps.findIndex(({ id }) => id === currentStep)

  return (
    <nav aria-label="Onboarding progress" className="mb-8">
      <ol className="m-0 grid list-none grid-cols-3 gap-2 p-0">
        {steps.map(({ id, label }, index) => {
          const isComplete = index < currentIndex
          const isCurrent = id === currentStep

          return (
            <li
              key={id}
              aria-current={isCurrent ? 'step' : undefined}
              className="min-w-0"
            >
              <div
                className={`mb-2 h-1.5 rounded-full ${
                  index <= currentIndex ? 'bg-accent' : 'bg-surface-muted'
                }`}
              />
              <span
                className={`flex items-center gap-1.5 truncate text-xs font-bold ${
                  isCurrent
                    ? 'text-heading'
                    : isComplete
                      ? 'text-accent'
                      : 'text-muted'
                }`}
              >
                {isComplete && (
                  <Check aria-hidden="true" size={13} strokeWidth={3} />
                )}
                {label}
              </span>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

function FormError({ message }: { message: string | null }) {
  if (!message) {
    return null
  }

  return (
    <p
      role="alert"
      className="m-0 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-600"
    >
      {message}
    </p>
  )
}

export function OnboardingPage() {
  const {
    user,
    companies,
    isLoading: isAccountLoading,
    startSession,
    refreshCompanies,
  } = useAccount()
  const { showAlert } = useAlerts()
  const { post: register } = useApi<TokenResponse>()
  const { post: createCompany } = useApi<Company>()
  const { post: createProject } = useApi<Project>()
  const navigate = useNavigate()
  const [step, setStep] = useState<OnboardingStep>('account')
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [projectName, setProjectName] = useState('')
  const [projectPath, setProjectPath] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    if (isAccountLoading || !user || step !== 'account') {
      return
    }

    const existingCompany = companies[0]
    if (existingCompany) {
      setSelectedCompany(existingCompany)
      setStep('project')
    } else {
      setStep('company')
    }
  }, [companies, isAccountLoading, step, user])

  if (isAccountLoading) {
    return (
      <AuthShell
        eyebrow="Getting started"
        title="Preparing your workspace"
        description="Checking your account before continuing onboarding."
      >
        <p
          role="status"
          className="flex items-center gap-3 rounded-xl border border-border bg-surface p-5 text-sm text-muted"
        >
          <LoaderCircle
            aria-hidden="true"
            className="motion-safe:animate-spin"
            size={18}
          />
          Loading your account…
        </p>
      </AuthShell>
    )
  }

  const accountStep = (
    <Form
      className="grid gap-5"
      onSubmit={async (event) => {
        event.preventDefault()
        setFormError(null)

        if (password !== passwordConfirmation) {
          setFormError('The passwords do not match.')
          return
        }

        setIsSubmitting(true)

        try {
          const { data: session } = await register<{
            name: string
            email: string
            password: string
          }>(
            apiEndpoint('/auth/register'),
            {
              name: name.trim(),
              email: email.trim().toLowerCase(),
              password,
            },
            { retries: 0 },
          )
          startSession(session.accessToken, session.user)
          setStep('company')
          showAlert({
            title: 'Account created',
            description: 'Now create the company that will own your projects.',
            variant: 'success',
          })
        } catch (error) {
          if (
            axios.isAxiosError(error) &&
            error.response?.status === 409
          ) {
            setFormError('An account already exists for this email.')
          } else {
            showAlert({
              title: 'Account could not be created',
              description: 'Check your details and try again.',
              variant: 'error',
            })
          }
        } finally {
          setIsSubmitting(false)
        }
      }}
    >
      <TextField
        name="name"
        value={name}
        onChange={setName}
        isRequired
        className="grid gap-2"
      >
        <Label className="text-sm font-bold text-heading">Your name</Label>
        <Input
          autoFocus
          autoComplete="name"
          maxLength={120}
          placeholder="Alex Morgan"
          className={inputStyles}
        />
        <FieldError className="text-xs text-red-500" />
      </TextField>

      <TextField
        name="email"
        value={email}
        onChange={setEmail}
        isRequired
        className="grid gap-2"
      >
        <Label className="text-sm font-bold text-heading">Work email</Label>
        <Input
          type="email"
          autoComplete="email"
          placeholder="alex@company.com"
          className={inputStyles}
        />
        <FieldError className="text-xs text-red-500" />
      </TextField>

      <div className="grid gap-5 sm:grid-cols-2">
        <TextField
          name="password"
          value={password}
          onChange={setPassword}
          isRequired
          className="grid gap-2"
        >
          <Label className="text-sm font-bold text-heading">Password</Label>
          <Input
            type="password"
            autoComplete="new-password"
            minLength={8}
            className={inputStyles}
          />
          <FieldError className="text-xs text-red-500" />
        </TextField>

        <TextField
          name="password-confirmation"
          value={passwordConfirmation}
          onChange={setPasswordConfirmation}
          isRequired
          isInvalid={
            passwordConfirmation.length > 0 &&
            password !== passwordConfirmation
          }
          className="grid gap-2"
        >
          <Label className="text-sm font-bold text-heading">
            Confirm password
          </Label>
          <Input
            type="password"
            autoComplete="new-password"
            minLength={8}
            className={inputStyles}
          />
          <FieldError className="text-xs text-red-500">
            Passwords must match.
          </FieldError>
        </TextField>
      </div>

      <p className="-mt-2 mb-0 text-xs leading-5 text-muted">
        Use at least eight characters.
      </p>
      <FormError message={formError} />
      <Button
        type="submit"
        isDisabled={
          isSubmitting ||
          !name.trim() ||
          !email.trim() ||
          password.length < 8 ||
          password !== passwordConfirmation
        }
        className={submitStyles}
      >
        {isSubmitting ? (
          <LoaderCircle
            aria-hidden="true"
            className="motion-safe:animate-spin"
            size={18}
          />
        ) : (
          <UserRoundPlus aria-hidden="true" size={18} />
        )}
        {isSubmitting ? 'Creating account…' : 'Create account'}
      </Button>
    </Form>
  )

  const companyStep = (
    <Form
      className="grid gap-5"
      onSubmit={async (event) => {
        event.preventDefault()
        setFormError(null)
        setIsSubmitting(true)

        try {
          const { data: company } = await createCompany<{ name: string }>(
            apiEndpoint('/companies'),
            { name: companyName.trim() },
            { retries: 0 },
          )
          setSelectedCompany(company)
          setStep('project')
          void refreshCompanies()
          showAlert({
            title: 'Company created',
            description: 'Add the first project to finish setting up.',
            variant: 'success',
          })
        } catch {
          showAlert({
            title: 'Company could not be created',
            description: 'Check the company name and try again.',
            variant: 'error',
          })
        } finally {
          setIsSubmitting(false)
        }
      }}
    >
      <TextField
        name="company-name"
        value={companyName}
        onChange={setCompanyName}
        isRequired
        className="grid gap-2"
      >
        <Label className="text-sm font-bold text-heading">Company name</Label>
        <Input
          autoFocus
          autoComplete="organization"
          maxLength={120}
          placeholder="Northstar Labs"
          className={inputStyles}
        />
        <FieldError className="text-xs text-red-500" />
        <p className="m-0 text-xs leading-5 text-muted">
          You will be the owner and can invite teammates later.
        </p>
      </TextField>
      <FormError message={formError} />
      <Button
        type="submit"
        isDisabled={isSubmitting || !companyName.trim()}
        className={submitStyles}
      >
        {isSubmitting ? (
          <LoaderCircle
            aria-hidden="true"
            className="motion-safe:animate-spin"
            size={18}
          />
        ) : (
          <Building2 aria-hidden="true" size={18} />
        )}
        {isSubmitting ? 'Creating company…' : 'Create company'}
      </Button>
    </Form>
  )

  const projectStep = (
    <Form
      className="grid gap-5"
      onSubmit={async (event) => {
        event.preventDefault()
        setFormError(null)

        if (!selectedCompany) {
          setFormError('Create or select a company before adding a project.')
          return
        }

        setIsSubmitting(true)

        try {
          const { data: project } = await createProject<{
            companyId: string
            name: string
            path: string
          }>(
            apiEndpoint('/projects'),
            {
              companyId: selectedCompany.id,
              name: projectName.trim(),
              path: projectPath.trim(),
            },
            { retries: 0 },
          )
          showAlert({
            title: 'Workspace ready',
            description: 'Your company and first project are ready.',
            variant: 'success',
          })
          navigate(`/projects/${project.id}`, { replace: true })
        } catch (error) {
          if (
            axios.isAxiosError(error) &&
            error.response?.status === 409
          ) {
            setFormError('A project with these details already exists.')
          } else {
            showAlert({
              title: 'Project could not be created',
              description: 'Check the project details and try again.',
              variant: 'error',
            })
          }
        } finally {
          setIsSubmitting(false)
        }
      }}
    >
      <div className="rounded-xl border border-border bg-surface-muted px-4 py-3">
        <p className="m-0 text-xs font-bold tracking-[0.08em] text-muted uppercase">
          Company
        </p>
        <p className="mt-1 mb-0 text-sm font-bold text-heading">
          {selectedCompany?.name ?? 'No company selected'}
        </p>
      </div>

      <TextField
        name="project-name"
        value={projectName}
        onChange={setProjectName}
        isRequired
        className="grid gap-2"
      >
        <Label className="text-sm font-bold text-heading">Project name</Label>
        <Input
          autoFocus
          maxLength={120}
          placeholder="Web application"
          className={inputStyles}
        />
        <FieldError className="text-xs text-red-500" />
      </TextField>

      <TextField
        name="project-path"
        value={projectPath}
        onChange={setProjectPath}
        isRequired
        isInvalid={
          projectPath.trim().length > 0 &&
          !isAbsoluteFolderPath(projectPath)
        }
        className="grid gap-2"
      >
        <Label className="text-sm font-bold text-heading">
          Project folder
        </Label>
        <Input
          autoComplete="off"
          spellCheck={false}
          maxLength={2048}
          placeholder="/Users/you/Projects/web-app"
          className={`${inputStyles} font-mono`}
        />
        <FieldError className="text-xs text-red-500">
          Enter an absolute folder path.
        </FieldError>
        <p className="m-0 text-xs leading-5 text-muted">
          Only the path is submitted; no files are uploaded.
        </p>
      </TextField>

      <FormError message={formError} />
      <Button
        type="submit"
        isDisabled={
          isSubmitting ||
          !selectedCompany ||
          !projectName.trim() ||
          !isAbsoluteFolderPath(projectPath)
        }
        className={submitStyles}
      >
        {isSubmitting ? (
          <LoaderCircle
            aria-hidden="true"
            className="motion-safe:animate-spin"
            size={18}
          />
        ) : (
          <FolderKanban aria-hidden="true" size={18} />
        )}
        {isSubmitting ? 'Creating project…' : 'Create project and continue'}
        {!isSubmitting && <ArrowRight aria-hidden="true" size={17} />}
      </Button>
    </Form>
  )

  const content = {
    account: accountStep,
    company: companyStep,
    project: projectStep,
  }[step]

  const copy = {
    account: {
      eyebrow: 'Step 1 of 3',
      title: 'Create your account',
      description: 'Start with your details, then set up the company and project you will manage.',
    },
    company: {
      eyebrow: 'Step 2 of 3',
      title: 'Create your company',
      description: 'Projects and teammates are organized under a company workspace.',
    },
    project: {
      eyebrow: 'Step 3 of 3',
      title: 'Add your first project',
      description: 'Connect the local project folder that will anchor your first roadmap.',
    },
  }[step]

  return (
    <AuthShell
      eyebrow={copy.eyebrow}
      title={copy.title}
      description={copy.description}
      footer={
        step === 'account' ? (
          <p className="m-0 text-center text-sm text-muted">
            Already have an account?{' '}
            <Link
              to="/sign-in"
              className="font-bold text-accent underline-offset-4 hover:underline focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-focus"
            >
              Sign in
            </Link>
          </p>
        ) : undefined
      }
    >
      <StepProgress currentStep={step} />
      {content}
    </AuthShell>
  )
}
