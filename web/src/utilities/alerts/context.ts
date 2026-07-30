import { createContext } from 'react'

export type AlertVariant = 'success' | 'error' | 'warning' | 'info'

export type AlertMessage = {
  id: string
  title: string
  description?: string
  variant: AlertVariant
}

export type ShowAlertOptions = {
  title: string
  description?: string
  variant?: AlertVariant
  duration?: number
}

export type AlertsContextValue = {
  alerts: AlertMessage[]
  dataRefreshVersion: number
  showAlert: (options: ShowAlertOptions) => string
  dismissAlert: (alertId: string) => void
  clearAlerts: () => void
}

export const AlertsContext = createContext<AlertsContextValue | null>(null)
