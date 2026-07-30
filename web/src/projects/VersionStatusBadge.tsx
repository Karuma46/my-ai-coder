import {
  CircleCheck,
  CircleDot,
  CirclePlay,
  Clock3,
  Rocket,
} from 'lucide-react'
import type { VersionStatus } from './types'

const statusConfig: Record<
  VersionStatus,
  {
    label: string
    className: string
    icon: typeof Clock3
  }
> = {
  pending: {
    label: 'Pending',
    className: 'bg-slate-500/10 text-slate-500',
    icon: Clock3,
  },
  ready: {
    label: 'Ready',
    className: 'bg-cyan-500/10 text-cyan-500',
    icon: CirclePlay,
  },
  'in-progress': {
    label: 'In progress',
    className: 'bg-blue-500/10 text-blue-500',
    icon: CircleDot,
  },
  complete: {
    label: 'Complete',
    className: 'bg-emerald-500/10 text-emerald-500',
    icon: CircleCheck,
  },
  released: {
    label: 'Released',
    className: 'bg-violet-500/10 text-violet-500',
    icon: Rocket,
  },
}

type VersionStatusBadgeProps = {
  status: VersionStatus
}

export function VersionStatusBadge({ status }: VersionStatusBadgeProps) {
  const statusDetails = statusConfig[status]
  const StatusIcon = statusDetails.icon

  return (
    <span
      className={`inline-flex w-fit shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ${statusDetails.className}`}
    >
      <StatusIcon aria-hidden="true" size={14} strokeWidth={2.2} />
      {statusDetails.label}
    </span>
  )
}
