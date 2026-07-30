import {
  ChartNoAxesCombined,
  ChevronDown,
  ChevronRight,
  FolderKanban,
  House,
  Info,
  type LucideIcon,
} from 'lucide-react'
import { useState } from 'react'
import { Button } from 'react-aria-components'
import { NavLink, useLocation } from 'react-router'
import { useProjects } from '../../projects'
import { AccountMenu } from '../account-menu'

type NavigationItem = {
  label: string
  to: string
  end?: boolean
  icon: LucideIcon
}

const navigationItems: NavigationItem[] = [
  { label: 'Overview', to: '/', end: true, icon: House },
  { label: 'Reports', to: '/reports', icon: ChartNoAxesCombined },
  { label: 'About', to: '/about', icon: Info },
]

const linkStyles =
  'group flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-semibold no-underline transition-colors focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-focus'

type SidebarProps = {
  isCollapsed: boolean
}

export function Sidebar({ isCollapsed }: SidebarProps) {
  const { projects } = useProjects()
  const { pathname } = useLocation()
  const [areProjectsExpanded, setAreProjectsExpanded] = useState(true)
  const isProjectsRoute = pathname.startsWith('/projects')

  const navigationLink = ({
    label,
    to,
    end,
    icon: Icon,
  }: NavigationItem) => (
    <li key={to}>
      <NavLink
        to={to}
        end={end}
        aria-label={label}
        title={isCollapsed ? label : undefined}
        className={({ isActive }) =>
          `${linkStyles} ${
            isCollapsed ? 'justify-center' : 'justify-center md:justify-start'
          } ${
            isActive
              ? 'bg-accent text-white'
              : 'text-muted hover:bg-surface-muted hover:text-heading'
          }`
        }
      >
        <Icon aria-hidden="true" size={19} strokeWidth={2} />
        <span className={isCollapsed ? 'hidden' : 'hidden md:inline'}>
          {label}
        </span>
      </NavLink>
    </li>
  )

  return (
    <aside
      id="dashboard-sidebar"
      className={`sticky top-14 flex h-[calc(100dvh-3.5rem)] shrink-0 flex-col overflow-hidden border-r border-border bg-surface py-4 transition-[width,padding] duration-200 motion-reduce:transition-none ${
        isCollapsed
          ? 'w-[4.5rem] px-3'
          : 'w-[4.5rem] border-r border-border px-3 md:w-60 md:px-4'
      }`}
    >
      <nav aria-label="Dashboard navigation">
        <ul className="m-0 grid list-none gap-1 p-0">
          {navigationLink(navigationItems[0])}

          <li>
            <div
              className={`flex rounded-lg ${
                isProjectsRoute
                  ? 'bg-accent text-white'
                  : 'text-muted hover:bg-surface-muted hover:text-heading'
              }`}
            >
              <NavLink
                to="/projects"
                aria-label="Projects"
                title={isCollapsed ? 'Projects' : undefined}
                className={`${linkStyles} min-w-0 flex-1 ${
                  isCollapsed
                    ? 'justify-center'
                    : 'justify-center md:justify-start'
                }`}
              >
                <FolderKanban
                  aria-hidden="true"
                  className="shrink-0"
                  size={19}
                  strokeWidth={2}
                />
                <span className={isCollapsed ? 'hidden' : 'hidden md:inline'}>
                  Projects
                </span>
              </NavLink>
              {!isCollapsed && (
                <Button
                  aria-label={
                    areProjectsExpanded
                      ? 'Collapse project list'
                      : 'Expand project list'
                  }
                  aria-expanded={areProjectsExpanded}
                  aria-controls="sidebar-project-list"
                  onPress={() =>
                    setAreProjectsExpanded((isExpanded) => !isExpanded)
                  }
                  className="mr-1 hidden size-10 shrink-0 cursor-pointer place-items-center self-center rounded-md text-current data-[hovered]:bg-white/15 data-[focus-visible]:outline-3 data-[focus-visible]:outline-offset-2 data-[focus-visible]:outline-focus md:grid"
                >
                  {areProjectsExpanded ? (
                    <ChevronDown aria-hidden="true" size={17} />
                  ) : (
                    <ChevronRight aria-hidden="true" size={17} />
                  )}
                </Button>
              )}
            </div>

            {!isCollapsed && areProjectsExpanded && (
              <ul
                id="sidebar-project-list"
                className="mt-1 ml-7 hidden list-none gap-1 border-l border-border pl-3 md:grid"
              >
                {projects.map((project) => (
                  <li key={project.id} className="min-w-0">
                    <NavLink
                      to={`/projects/${project.id}`}
                      title={project.name}
                      className={({ isActive }) =>
                        `block min-h-9 truncate rounded-md px-3 py-2 text-sm font-medium no-underline transition-colors focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-focus ${
                          isActive
                            ? 'bg-surface-muted text-heading'
                            : 'text-muted hover:bg-surface-muted hover:text-heading'
                        }`
                      }
                    >
                      {project.name}
                    </NavLink>
                  </li>
                ))}
              </ul>
            )}
          </li>

          {navigationItems.slice(1).map(navigationLink)}
        </ul>
      </nav>

      <section
        aria-label="Account"
        className="mt-auto border-t border-border pt-3"
      >
        <AccountMenu isCollapsed={isCollapsed} />
      </section>
    </aside>
  )
}
