import axios from 'axios'
import { Eye, EyeOff, LoaderCircle, LogIn } from 'lucide-react'
import { useState } from 'react'
import {
  Button,
  FieldError,
  Form,
  Input,
  Label,
  TextField,
} from 'react-aria-components'
import {
  Link,
  Navigate,
  useLocation,
  useNavigate,
} from 'react-router'
import type { TokenResponse } from '../account'
import { useAccount } from '../account'
import { AuthShell } from '../components/auth-shell'
import { useAlerts } from '../utilities/alerts'
import { apiEndpoint } from '../utilities/apiEndpoint'
import { useApi } from '../utilities/useApi'

type SignInLocationState = {
  from?: string
}

const inputStyles =
  'w-full rounded-xl border border-border bg-surface px-3 py-3 text-sm text-heading outline-none data-[focused]:border-accent data-[invalid]:border-red-500 data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus'

export function SignInPage() {
  const {
    user,
    companies,
    isLoading: isAccountLoading,
    startSession,
    refreshCompanies,
  } = useAccount()
  const { showAlert } = useAlerts()
  const { post } = useApi<TokenResponse>()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  if (!isAccountLoading && user && !isSubmitting) {
    return <Navigate to={companies.length > 0 ? '/' : '/onboarding'} replace />
  }

  return (
    <AuthShell
      eyebrow="Welcome back"
      title="Sign in to your workspace"
      description="Continue planning roadmaps, coordinating todos, and shipping releases."
      footer={
        <p className="m-0 text-center text-sm text-muted">
          New to Northstar?{' '}
          <Link
            to="/onboarding"
            className="font-bold text-accent underline-offset-4 hover:underline focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-focus"
          >
            Create an account
          </Link>
        </p>
      }
    >
      <Form
        className="grid gap-5"
        onSubmit={async (event) => {
          event.preventDefault()
          setFormError(null)
          setIsSubmitting(true)

          try {
            const { data: session } = await post<{
              email: string
              password: string
            }>(
              apiEndpoint('/auth/login'),
              {
                email: email.trim().toLowerCase(),
                password,
              },
              { retries: 0 },
            )
            startSession(session.accessToken, session.user)
            let memberships

            try {
              memberships = await refreshCompanies()
            } catch {
              showAlert({
                title: 'Workspace list unavailable',
                description:
                  'You are signed in, but your companies could not be loaded.',
                variant: 'warning',
              })
              navigate('/', { replace: true })
              return
            }
            const requestedPath = (
              location.state as SignInLocationState | null
            )?.from

            navigate(
              memberships.length === 0
                ? '/onboarding'
                : requestedPath?.startsWith('/')
                  ? requestedPath
                  : '/',
              { replace: true },
            )
          } catch (error) {
            if (
              axios.isAxiosError(error) &&
              error.response?.status === 401
            ) {
              setFormError('The email or password is incorrect.')
            } else {
              showAlert({
                title: 'Sign in failed',
                description: 'Check your connection and try again.',
                variant: 'error',
              })
            }
          } finally {
            setIsSubmitting(false)
          }
        }}
      >
        <TextField
          name="email"
          value={email}
          onChange={setEmail}
          type="email"
          isRequired
          className="grid gap-2"
        >
          <Label className="text-sm font-bold text-heading">Email address</Label>
          <Input
            autoFocus
            autoComplete="email"
            placeholder="you@company.com"
            className={inputStyles}
          />
          <FieldError className="text-xs text-red-500" />
        </TextField>

        <TextField
          name="password"
          value={password}
          onChange={setPassword}
          type={showPassword ? 'text' : 'password'}
          isRequired
          className="grid gap-2"
        >
          <Label className="text-sm font-bold text-heading">Password</Label>
          <div className="relative">
            <Input
              autoComplete="current-password"
              className={`${inputStyles} pr-12`}
            />
            <Button
              type="button"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              onPress={() => setShowPassword((isVisible) => !isVisible)}
              className="absolute inset-y-1 right-1 grid aspect-square cursor-pointer place-items-center rounded-lg text-muted data-[hovered]:bg-surface-muted data-[hovered]:text-heading data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus"
            >
              {showPassword ? (
                <EyeOff aria-hidden="true" size={18} />
              ) : (
                <Eye aria-hidden="true" size={18} />
              )}
            </Button>
          </div>
          <FieldError className="text-xs text-red-500" />
        </TextField>

        {formError && (
          <p
            role="alert"
            className="m-0 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-600"
          >
            {formError}
          </p>
        )}

        <Button
          type="submit"
          isDisabled={isSubmitting || !email.trim() || !password}
          className="inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-xl bg-accent px-5 text-sm font-bold text-white transition-colors data-[hovered]:bg-accent-hover data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? (
            <LoaderCircle
              aria-hidden="true"
              className="motion-safe:animate-spin"
              size={18}
            />
          ) : (
            <LogIn aria-hidden="true" size={18} />
          )}
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </Button>
      </Form>
    </AuthShell>
  )
}
