import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { useLocation } from 'react-router'
import { Alerts } from '../../components/alerts'
import { apiWebSocketEndpoint } from '../apiEndpoint'
import { getAccessToken } from '../authToken'
import {
  AlertsContext,
  type AlertMessage,
  type ShowAlertOptions,
} from './context'

type AlertsProviderProps = {
  children: ReactNode
}

const DEFAULT_ALERT_DURATION = 5_000
const INITIAL_RECONNECT_DELAY = 1_000
const MAX_RECONNECT_DELAY = 30_000
const MAX_TRACKED_RUNS = 100

let alertSequence = 0

type AgentRunCompletedEvent = {
  type: 'agent-run.completed'
  runId: string
  projectId: string
  todoId: string
  status: 'succeeded' | 'failed'
  completedAt: string
  error: string | null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function parseAgentRunCompletedEvent(
  message: unknown,
): AgentRunCompletedEvent | null {
  if (typeof message !== 'string') {
    return null
  }

  let value: unknown

  try {
    value = JSON.parse(message)
  } catch {
    return null
  }

  if (
    !isRecord(value) ||
    value.type !== 'agent-run.completed' ||
    typeof value.runId !== 'string' ||
    typeof value.projectId !== 'string' ||
    typeof value.todoId !== 'string' ||
    (value.status !== 'succeeded' && value.status !== 'failed') ||
    typeof value.completedAt !== 'string' ||
    (value.error !== null && typeof value.error !== 'string')
  ) {
    return null
  }

  return {
    type: value.type,
    runId: value.runId,
    projectId: value.projectId,
    todoId: value.todoId,
    status: value.status,
    completedAt: value.completedAt,
    error: value.error,
  }
}

export function AlertsProvider({ children }: AlertsProviderProps) {
  const { pathname } = useLocation()
  const [alerts, setAlerts] = useState<AlertMessage[]>([])
  const [dataRefreshVersion, setDataRefreshVersion] = useState(0)
  const timers = useRef(new Map<string, number>())
  const processedRuns = useRef(new Set<string>())

  const dismissAlert = useCallback((alertId: string) => {
    const timer = timers.current.get(alertId)

    if (timer !== undefined) {
      window.clearTimeout(timer)
      timers.current.delete(alertId)
    }

    setAlerts((currentAlerts) =>
      currentAlerts.filter((alert) => alert.id !== alertId),
    )
  }, [])

  const clearAlerts = useCallback(() => {
    timers.current.forEach((timer) => window.clearTimeout(timer))
    timers.current.clear()
    setAlerts([])
  }, [])

  const showAlert = useCallback(
    ({
      title,
      description,
      variant = 'info',
      duration = DEFAULT_ALERT_DURATION,
    }: ShowAlertOptions) => {
      alertSequence += 1
      const alertId = `alert-${Date.now()}-${alertSequence}`
      const alert: AlertMessage = {
        id: alertId,
        title,
        description,
        variant,
      }

      setAlerts((currentAlerts) => [...currentAlerts, alert])

      if (Number.isFinite(duration) && duration > 0) {
        const timer = window.setTimeout(
          () => dismissAlert(alertId),
          duration,
        )
        timers.current.set(alertId, timer)
      }

      return alertId
    },
    [dismissAlert],
  )

  useEffect(
    () => () => {
      timers.current.forEach((timer) => window.clearTimeout(timer))
      timers.current.clear()
    },
    [],
  )

  useEffect(() => {
    let socket: WebSocket | null = null
    let reconnectTimer: number | undefined
    let reconnectAttempts = 0
    let isDisposed = false

    const connect = () => {
      if (isDisposed) {
        return
      }

      const accessToken = getAccessToken()
      const projectPathMatch = pathname.match(/^\/projects\/([^/]+)/)

      if (!accessToken || !projectPathMatch) {
        return
      }

      const socketUrl = new URL(apiWebSocketEndpoint('/agent-runs/events'))
      socketUrl.searchParams.set(
        'projectId',
        decodeURIComponent(projectPathMatch[1]),
      )
      socketUrl.searchParams.set('token', accessToken)
      const currentSocket = new WebSocket(socketUrl)
      socket = currentSocket

      currentSocket.addEventListener('message', ({ data }) => {
        const event = parseAgentRunCompletedEvent(data)

        if (!event || processedRuns.current.has(event.runId)) {
          return
        }

        processedRuns.current.add(event.runId)
        if (processedRuns.current.size > MAX_TRACKED_RUNS) {
          const oldestRunId = processedRuns.current.values().next().value

          if (oldestRunId !== undefined) {
            processedRuns.current.delete(oldestRunId)
          }
        }

        reconnectAttempts = 0
        showAlert({
          title:
            event.status === 'succeeded'
              ? 'Agent run completed'
              : 'Agent run failed',
          description:
            event.status === 'succeeded'
              ? 'The completed todo and project roadmap have been refreshed.'
              : 'The todo was refreshed. Review it before running the agent again.',
          variant: event.status === 'succeeded' ? 'success' : 'error',
        })
        setDataRefreshVersion((currentVersion) => currentVersion + 1)
      })

      currentSocket.addEventListener('error', () => {
        currentSocket.close()
      })

      currentSocket.addEventListener('close', () => {
        if (isDisposed) {
          return
        }

        const reconnectDelay = Math.min(
          INITIAL_RECONNECT_DELAY * 2 ** reconnectAttempts,
          MAX_RECONNECT_DELAY,
        )
        reconnectAttempts = Math.min(reconnectAttempts + 1, 5)
        reconnectTimer = window.setTimeout(connect, reconnectDelay)
      })
    }

    connect()

    return () => {
      isDisposed = true

      if (reconnectTimer !== undefined) {
        window.clearTimeout(reconnectTimer)
      }

      socket?.close()
    }
  }, [pathname, showAlert])

  const value = useMemo(
    () => ({
      alerts,
      dataRefreshVersion,
      showAlert,
      dismissAlert,
      clearAlerts,
    }),
    [
      alerts,
      clearAlerts,
      dataRefreshVersion,
      dismissAlert,
      showAlert,
    ],
  )

  return (
    <AlertsContext.Provider value={value}>
      {children}
      <Alerts alerts={alerts} onDismiss={dismissAlert} />
    </AlertsContext.Provider>
  )
}
