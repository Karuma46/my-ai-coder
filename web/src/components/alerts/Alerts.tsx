import {
  CheckCircle2,
  CircleAlert,
  Info,
  TriangleAlert,
  X,
  type LucideIcon,
} from 'lucide-react'
import { Button } from 'react-aria-components'
import type {
  AlertMessage,
  AlertVariant,
} from '../../utilities/alerts/context'

type AlertStyle = {
  icon: LucideIcon
  iconClassName: string
}

const alertStyles: Record<AlertVariant, AlertStyle> = {
  success: {
    icon: CheckCircle2,
    iconClassName: 'bg-emerald-500/10 text-emerald-500',
  },
  error: {
    icon: CircleAlert,
    iconClassName: 'bg-red-500/10 text-red-500',
  },
  warning: {
    icon: TriangleAlert,
    iconClassName: 'bg-amber-500/10 text-amber-500',
  },
  info: {
    icon: Info,
    iconClassName: 'bg-blue-500/10 text-blue-500',
  },
}

type AlertsProps = {
  alerts: AlertMessage[]
  onDismiss: (alertId: string) => void
}

export function Alerts({ alerts, onDismiss }: AlertsProps) {
  if (alerts.length === 0) {
    return null
  }

  return (
    <section
      aria-label="Notifications"
      className="pointer-events-none fixed top-18 right-4 z-[70] w-[min(24rem,calc(100vw-2rem))] sm:right-6"
    >
      <ol className="m-0 grid list-none gap-3 p-0">
        {alerts.map((alert) => {
          const style = alertStyles[alert.variant]
          const AlertIcon = style.icon

          return (
            <li
              key={alert.id}
              className="pointer-events-auto rounded-xl border border-border bg-surface p-4 shadow-2xl"
            >
              <div
                role={alert.variant === 'error' ? 'alert' : 'status'}
                aria-atomic="true"
                className="flex items-start gap-3"
              >
                <span
                  className={`grid size-9 shrink-0 place-items-center rounded-lg ${style.iconClassName}`}
                >
                  <AlertIcon aria-hidden="true" size={18} strokeWidth={2.2} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="m-0 text-sm font-bold text-heading">
                    {alert.title}
                  </p>
                  {alert.description && (
                    <p className="mt-1 mb-0 text-xs leading-5 text-muted">
                      {alert.description}
                    </p>
                  )}
                </div>
                <Button
                  aria-label={`Dismiss ${alert.title}`}
                  onPress={() => onDismiss(alert.id)}
                  className="grid size-8 shrink-0 cursor-pointer place-items-center rounded-lg text-muted transition-colors data-[hovered]:bg-surface-muted data-[hovered]:text-heading data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus"
                >
                  <X aria-hidden="true" size={16} strokeWidth={2.2} />
                </Button>
              </div>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
