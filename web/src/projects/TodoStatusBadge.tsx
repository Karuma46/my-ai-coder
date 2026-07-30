import {
  Circle,
  CircleCheck,
  CircleDot,
  CircleX,
  FilePenLine,
} from 'lucide-react'
import type { TodoStatus } from './types'

const statusConfig: Record<
  TodoStatus,
  {
    label: string
    className: string
    icon: typeof Circle
  }
> = {
  draft: {
    label: 'Draft',
    className: 'bg-amber-500/10 text-amber-500',
    icon: FilePenLine,
  },
  planned: {
    label: 'Planned',
    className: 'bg-slate-500/10 text-slate-500',
    icon: Circle,
  },
  'in-progress': {
    label: 'In progress',
    className: 'bg-blue-500/10 text-blue-500',
    icon: CircleDot,
  },
  blocked: {
    label: 'Blocked',
    className: 'bg-red-500/10 text-red-500',
    icon: CircleX,
  },
  failed: {
    label: 'Failed',
    className: 'bg-rose-500/10 text-rose-500',
    icon: CircleX,
  },
  done: {
    label: 'Done',
    className: 'bg-emerald-500/10 text-emerald-500',
    icon: CircleCheck,
  },
}

type TodoStatusBadgeProps = {
  status: TodoStatus
}

export function TodoStatusBadge({ status }: TodoStatusBadgeProps) {
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
