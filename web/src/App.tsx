import axios from 'axios'
import {
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  FolderKanban,
  Users,
  type LucideIcon,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Heading } from 'react-aria-components'
import {
  Navigate,
  Route,
  Routes,
  useLocation,
} from 'react-router'
import {
  AccountProvider,
  AccountSettingsPage,
  useAccount,
} from './account'
import { SignInPage } from './auth'
import { CompanySettingsPage } from './companies'
import { DashboardLayout } from './components/layout'
import { LocalAgentsPage } from './local-agents'
import { OnboardingPage } from './onboarding'
import {
  ProjectSettingsPage,
  ProjectsPage,
  ProjectsProvider,
} from './projects'
import { useAlerts } from './utilities/alerts'
import { apiEndpoint } from './utilities/apiEndpoint'
import { useApi } from './utilities/useApi'

type MetricKey =
  | 'activeProjects'
  | 'teamMembers'
  | 'tasksCompleted'
  | 'hoursTracked'

type DashboardMetric = {
  key: MetricKey
  label: string
  value: number
  detail: string
  trend: 'up' | 'down' | 'neutral'
}

type ActivityItem = {
  id: string
  type: string
  title: string
  actorName: string
  occurredAt: string
}

type DashboardResponse = {
  metrics: DashboardMetric[]
  recentActivity: ActivityItem[]
}

type DeliveryReport = {
  from: string
  to: string
  periods: Array<{
    label: string
    value: number
  }>
}

const metricIcons: Record<MetricKey, LucideIcon> = {
  activeProjects: FolderKanban,
  teamMembers: Users,
  tasksCompleted: CheckCircle2,
  hoursTracked: Clock3,
}

const activityDateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
})

function PageHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string
  title: string
  description: string
}) {
  return (
    <header>
      <p className="m-0 text-xs font-bold tracking-[0.12em] text-accent uppercase">
        {eyebrow}
      </p>
      <Heading
        level={1}
        className="mt-2 mb-0 text-3xl font-bold tracking-[-0.035em] text-heading sm:text-4xl"
      >
        {title}
      </Heading>
      <p className="mt-3 mb-0 max-w-2xl text-sm leading-6 text-muted sm:text-base">
        {description}
      </p>
    </header>
  )
}

function OverviewPage() {
  const { user } = useAccount()
  const { showAlert } = useAlerts()
  const { data: dashboard, get } = useApi<DashboardResponse>()
  const [dashboardRequestFailed, setDashboardRequestFailed] = useState(false)

  useEffect(() => {
    const controller = new AbortController()

    void get(apiEndpoint('/dashboard'), undefined, {
      signal: controller.signal,
      retries: 2,
    }).catch((error: unknown) => {
      if (axios.isCancel(error)) {
        return
      }

      setDashboardRequestFailed(true)
      showAlert({
        title: 'Dashboard unavailable',
        description: 'Dashboard metrics could not be loaded. Try again.',
        variant: 'error',
      })
    })

    return () => controller.abort()
  }, [get, showAlert])

  const firstName = user?.name.split(/\s+/)[0]

  return (
    <>
      <PageHeading
        eyebrow="Dashboard"
        title={firstName ? `Good morning, ${firstName}.` : 'Good morning.'}
        description="Here is a concise view of your workspace performance and the activity that needs your attention."
      />

      {dashboard ? (
        <section
          aria-label="Workspace metrics"
          className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
        >
          {dashboard.metrics.map(({ key, label, value, detail, trend }) => {
            const Icon = metricIcons[key]

            return (
              <article
                key={key}
                className="rounded-xl border border-border bg-surface p-5 shadow-sm"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="m-0 text-sm font-medium text-muted">{label}</p>
                  <span className="grid size-9 place-items-center rounded-lg bg-surface-muted text-accent">
                    <Icon aria-hidden="true" size={18} strokeWidth={2} />
                  </span>
                </div>
                <p className="mt-4 mb-1 text-3xl font-bold tracking-[-0.04em] text-heading">
                  {value.toLocaleString()}
                </p>
                <p className="m-0 flex items-center gap-1 text-xs text-muted">
                  <ArrowUpRight
                    aria-hidden="true"
                    className={
                      trend === 'down'
                        ? 'rotate-90 text-red-500'
                        : trend === 'up'
                          ? 'text-emerald-500'
                          : 'text-muted'
                    }
                    size={14}
                  />
                  {detail}
                </p>
              </article>
            )
          })}
        </section>
      ) : (
        <p
          role="status"
          className="mt-8 rounded-xl border border-border bg-surface p-6 text-sm text-muted shadow-sm"
        >
          {dashboardRequestFailed
            ? 'Dashboard metrics are unavailable.'
            : 'Loading dashboard metrics…'}
        </p>
      )}

      <section
        aria-labelledby="activity-title"
        className="mt-6 rounded-xl border border-border bg-surface shadow-sm"
      >
        <div className="border-b border-border px-5 py-4">
          <Heading
            id="activity-title"
            level={2}
            className="m-0 text-base font-bold text-heading"
          >
            Recent activity
          </Heading>
        </div>
        {dashboard?.recentActivity.length ? (
          <ul className="m-0 list-none divide-y divide-border p-0">
            {dashboard.recentActivity.map(
              ({ id, title, actorName, occurredAt }) => (
                <li key={id} className="flex items-start gap-3 px-5 py-4">
                  <span
                    className="mt-1.5 size-2 shrink-0 rounded-full bg-accent"
                    aria-hidden="true"
                  />
                  <div>
                    <p className="m-0 text-sm font-semibold text-heading">
                      {title}
                    </p>
                    <p className="mt-1 mb-0 text-xs text-muted">
                      {actorName} ·{' '}
                      {activityDateFormatter.format(new Date(occurredAt))}
                    </p>
                  </div>
                </li>
              ),
            )}
          </ul>
        ) : (
          <p className="m-0 px-5 py-6 text-sm text-muted">
            {dashboard
              ? 'No recent activity.'
              : dashboardRequestFailed
                ? 'Recent activity is unavailable.'
                : 'Loading recent activity…'}
          </p>
        )}
      </section>
    </>
  )
}

function ReportsPage() {
  const { showAlert } = useAlerts()
  const { data: report, get } = useApi<DeliveryReport>()
  const [reportRequestFailed, setReportRequestFailed] = useState(false)

  useEffect(() => {
    const controller = new AbortController()

    void get(apiEndpoint('/reports/delivery'), undefined, {
      signal: controller.signal,
      retries: 2,
    }).catch((error: unknown) => {
      if (axios.isCancel(error)) {
        return
      }

      setReportRequestFailed(true)
      showAlert({
        title: 'Report unavailable',
        description: 'Delivery data could not be loaded. Try again.',
        variant: 'error',
      })
    })

    return () => controller.abort()
  }, [get, showAlert])

  const periods = report?.periods ?? []
  const reportColumns = {
    gridTemplateColumns: `repeat(${Math.max(periods.length, 1)}, minmax(0, 1fr))`,
  }

  return (
    <>
      <PageHeading
        eyebrow="Analytics"
        title="Reports"
        description="Monitor delivery health and identify where your team is making the most progress."
      />

      <section
        aria-labelledby="delivery-title"
        className="mt-8 rounded-xl border border-border bg-surface p-5 shadow-sm"
      >
        <Heading
          id="delivery-title"
          level={2}
          className="m-0 text-base font-bold text-heading"
        >
          Delivery by quarter
        </Heading>
        {report ? (
          <>
            <div
              className="mt-6 grid h-56 items-end gap-3 border-b border-border"
              style={reportColumns}
            >
              {periods.map(({ label, value }) => (
                <div
                  key={label}
                  className="flex h-full items-end"
                  aria-label={`${label}: ${value}%`}
                >
                  <div
                    className="w-full rounded-t-md bg-accent"
                    style={{ height: `${Math.min(value, 100)}%` }}
                  />
                </div>
              ))}
            </div>
            <div
              className="mt-3 grid gap-3 text-center text-xs text-muted"
              style={reportColumns}
              aria-hidden="true"
            >
              {periods.map(({ label }) => (
                <span key={label}>{label}</span>
              ))}
            </div>
          </>
        ) : (
          <p role="status" className="mt-6 mb-0 text-sm text-muted">
            {reportRequestFailed
              ? 'Delivery report is unavailable.'
              : 'Loading delivery report…'}
          </p>
        )}
      </section>
    </>
  )
}

function AboutPage() {
  return (
    <>
      <PageHeading
        eyebrow="Workspace"
        title="About Northstar"
        description="Northstar is a focused dashboard starter built with accessible components, typed routes, and a responsive application shell."
      />

      <section className="mt-8 grid gap-4 sm:grid-cols-2">
        <article className="rounded-xl border border-border bg-surface p-5 shadow-sm">
          <Heading level={2} className="m-0 text-base font-bold text-heading">
            Accessible by default
          </Heading>
          <p className="mt-3 mb-0 text-sm leading-6 text-muted">
            Semantic regions, visible focus, keyboard navigation, and clear
            accessible names are part of the layout structure.
          </p>
        </article>
        <article className="rounded-xl border border-border bg-surface p-5 shadow-sm">
          <Heading level={2} className="m-0 text-base font-bold text-heading">
            Ready to extend
          </Heading>
          <p className="mt-3 mb-0 text-sm leading-6 text-muted">
            Nested React Router routes render inside the shared dashboard
            outlet without duplicating navigation or account UI.
          </p>
        </article>
      </section>
    </>
  )
}

function AuthenticatedDashboard() {
  const { user, isLoading } = useAccount()
  const location = useLocation()

  if (isLoading) {
    return (
      <main className="grid min-h-dvh place-items-center bg-canvas p-6">
        <p
          role="status"
          className="m-0 rounded-xl border border-border bg-surface px-5 py-4 text-sm text-muted shadow-sm"
        >
          Loading your workspace…
        </p>
      </main>
    )
  }

  if (!user) {
    return (
      <Navigate
        to="/sign-in"
        replace
        state={{ from: `${location.pathname}${location.search}` }}
      />
    )
  }

  return (
    <ProjectsProvider>
      <DashboardLayout />
    </ProjectsProvider>
  )
}

function App() {
  return (
    <AccountProvider>
      <Routes>
        <Route path="sign-in" element={<SignInPage />} />
        <Route path="onboarding" element={<OnboardingPage />} />
        <Route element={<AuthenticatedDashboard />}>
          <Route index element={<OverviewPage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="projects/:projectId" element={<ProjectsPage />} />
          <Route
            path="projects/:projectId/settings"
            element={<ProjectSettingsPage />}
          />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route
            path="settings/account"
            element={<AccountSettingsPage />}
          />
          <Route
            path="settings/company"
            element={<CompanySettingsPage />}
          />
          <Route
            path="settings/local-agents"
            element={<LocalAgentsPage />}
          />
          <Route
            path="settings/local-llms"
            element={<Navigate to="/settings/local-agents" replace />}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </AccountProvider>
  )
}

export default App
