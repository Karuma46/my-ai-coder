import axios from 'axios'
import {
  LayoutDashboard,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Button } from 'react-aria-components'
import { Link } from 'react-router'
import { apiOriginEndpoint } from '../../utilities/apiEndpoint'
import { useApi } from '../../utilities/useApi'

type HealthStatus = 'operational' | 'degraded' | 'unavailable'

type Health = {
  status: HealthStatus
  checkedAt: string
  services: Array<{
    name: string
    status: HealthStatus
  }>
}

type TopBarProps = {
  isSidebarCollapsed: boolean
  onToggleSidebar: () => void
}

export function TopBar({
  isSidebarCollapsed,
  onToggleSidebar,
}: TopBarProps) {
  const { data: health, get } = useApi<Health>()
  const [healthRequestFailed, setHealthRequestFailed] = useState(false)

  useEffect(() => {
    const controller = new AbortController()

    void get(apiOriginEndpoint('/health'), undefined, {
      signal: controller.signal,
      retries: 2,
    }).catch((error: unknown) => {
      if (!axios.isCancel(error)) {
        setHealthRequestFailed(true)
      }
    })

    return () => controller.abort()
  }, [get])

  const healthStatus = healthRequestFailed
    ? 'unavailable'
    : health?.status
  const healthLabel =
    healthStatus === 'operational'
      ? 'All systems operational'
      : healthStatus === 'degraded'
        ? 'Systems degraded'
        : healthStatus === 'unavailable'
          ? 'Systems unavailable'
          : 'Checking systems'
  const compactHealthLabel =
    healthStatus === 'operational'
      ? 'Online'
      : healthStatus === 'degraded'
        ? 'Degraded'
        : healthStatus === 'unavailable'
          ? 'Offline'
          : 'Checking'
  const healthIndicatorStyles =
    healthStatus === 'operational'
      ? 'bg-emerald-500'
      : healthStatus === 'degraded'
        ? 'bg-amber-500'
        : healthStatus === 'unavailable'
          ? 'bg-red-500'
          : 'bg-slate-400'

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-border bg-surface px-4 sm:px-6">
      <a
        href="#dashboard-content"
        className="sr-only rounded-md bg-surface px-3 py-2 font-bold text-heading focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-30 focus:outline-3 focus:outline-offset-2 focus:outline-focus"
      >
        Skip to content
      </a>

      <div className="flex items-center gap-3">
        <Button
          aria-label={
            isSidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'
          }
          aria-controls="dashboard-sidebar"
          aria-expanded={!isSidebarCollapsed}
          onPress={onToggleSidebar}
          className="grid size-9 cursor-pointer place-items-center rounded-lg border border-border bg-surface text-muted transition-colors data-[hovered]:bg-surface-muted data-[hovered]:text-heading data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus"
        >
          {isSidebarCollapsed ? (
            <PanelLeftOpen aria-hidden="true" size={18} strokeWidth={2} />
          ) : (
            <PanelLeftClose aria-hidden="true" size={18} strokeWidth={2} />
          )}
        </Button>

        <Link
          to="/"
          className="inline-flex items-center gap-2 rounded-md font-bold tracking-[-0.02em] text-heading no-underline focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-focus"
        >
          <span className="grid size-8 place-items-center rounded-lg bg-accent text-white">
            <LayoutDashboard aria-hidden="true" size={18} strokeWidth={2.2} />
          </span>
          <span>Northstar</span>
        </Link>
      </div>

      <div className="flex items-center gap-2 text-xs font-medium text-muted">
        <span
          className={`size-2 rounded-full ${healthIndicatorStyles}`}
          aria-hidden="true"
        />
        <span className="hidden sm:inline">{healthLabel}</span>
        <span className="sm:hidden">{compactHealthLabel}</span>
      </div>
    </header>
  )
}
