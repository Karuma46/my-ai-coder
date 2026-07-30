import {
  Bot,
  Building2,
  ChevronUp,
  LogOut,
  UserRoundCog,
} from 'lucide-react'
import {
  Button,
  Menu,
  MenuItem,
  MenuTrigger,
  Popover,
  Separator,
} from 'react-aria-components'
import { useNavigate } from 'react-router'
import { useAccount } from '../../account'

type AccountMenuProps = {
  isCollapsed: boolean
}

const menuItemStyles =
  'flex min-h-10 cursor-default items-center gap-3 rounded-md px-3 text-sm font-semibold text-heading outline-none data-[focused]:bg-surface-muted data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-[-2px] data-[focus-visible]:outline-focus'

export function AccountMenu({ isCollapsed }: AccountMenuProps) {
  const { user, isLoading, signOut } = useAccount()
  const navigate = useNavigate()

  const handleAction = (key: React.Key) => {
    if (key === 'logout') {
      signOut()
      navigate('/sign-in', { replace: true })
      return
    }

    navigate(
      key === 'company'
        ? '/settings/company'
        : key === 'agents'
          ? '/settings/local-agents'
          : '/settings/account',
    )
  }

  return (
    <MenuTrigger>
      <Button
        aria-label={
          user ? `Open account menu for ${user.name}` : 'Open account menu'
        }
        className={`flex min-h-12 w-full cursor-pointer items-center gap-3 rounded-lg p-1 text-left outline-none transition-colors data-[hovered]:bg-surface-muted data-[pressed]:bg-surface-muted data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus ${
          isCollapsed ? 'justify-center' : 'justify-center md:justify-start'
        }`}
      >
        {user?.avatarUrl ? (
          <img
            src={user.avatarUrl}
            alt=""
            className="size-10 shrink-0 rounded-full object-cover ring-1 ring-border"
          />
        ) : (
          <span
            className="grid size-10 shrink-0 place-items-center rounded-full bg-surface-muted text-sm font-bold text-heading ring-1 ring-border"
            aria-hidden="true"
          >
            {user?.initials ?? (isLoading ? '…' : '?')}
          </span>
        )}
        <span
          className={
            isCollapsed
              ? 'hidden'
              : 'hidden min-w-0 flex-1 text-left md:block'
          }
        >
          <span className="block truncate text-sm font-bold text-heading">
            {user?.name ??
              (isLoading ? 'Loading account…' : 'Account unavailable')}
          </span>
          {user && (
            <span className="block truncate text-xs text-muted">
              {user.email}
            </span>
          )}
        </span>
        {!isCollapsed && (
          <ChevronUp
            aria-hidden="true"
            className="hidden shrink-0 text-muted md:block"
            size={16}
          />
        )}
      </Button>

      <Popover
        placement="top start"
        offset={8}
        className="w-60 rounded-xl border border-border bg-surface p-1.5 shadow-xl outline-none data-[entering]:animate-in data-[exiting]:animate-out"
      >
        <Menu
          aria-label="Account actions"
          onAction={handleAction}
          className="outline-none"
        >
          <MenuItem id="account" className={menuItemStyles}>
            <UserRoundCog aria-hidden="true" size={18} />
            Account Settings
          </MenuItem>
          <MenuItem id="company" className={menuItemStyles}>
            <Building2 aria-hidden="true" size={18} />
            Company
          </MenuItem>
          <MenuItem id="agents" className={menuItemStyles}>
            <Bot aria-hidden="true" size={18} />
            Local Agents
          </MenuItem>
          <Separator className="my-1 h-px bg-border" />
          <MenuItem
            id="logout"
            className={`${menuItemStyles} text-red-600 dark:text-red-400`}
          >
            <LogOut aria-hidden="true" size={18} />
            Logout
          </MenuItem>
        </Menu>
      </Popover>
    </MenuTrigger>
  )
}
