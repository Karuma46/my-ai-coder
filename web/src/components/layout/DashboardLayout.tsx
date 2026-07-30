import { useState } from 'react'
import { Outlet } from 'react-router'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'

export function DashboardLayout() {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)

  return (
    <div className="min-h-dvh bg-surface-muted">
      <TopBar
        isSidebarCollapsed={isSidebarCollapsed}
        onToggleSidebar={() =>
          setIsSidebarCollapsed((isCollapsed) => !isCollapsed)
        }
      />
      <div className="flex min-h-[calc(100dvh-3.5rem)]">
        <Sidebar isCollapsed={isSidebarCollapsed} />
        <main
          id="dashboard-content"
          tabIndex={-1}
          className="min-w-0 flex-1 p-4 focus:outline-none sm:p-6 lg:p-10"
        >
          <div className="w-full">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
