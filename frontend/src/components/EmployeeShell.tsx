import { useState } from "react"

import { Outlet, useNavigate } from "react-router-dom"

import { CalendarDays, ClipboardList, Home, Settings } from "lucide-react"

import { PalmLogoutDialog } from "@/components/PalmLogoutDialog"
import { SidebarLayout, type SidebarNavItem } from "@/components/SidebarLayout"
import { EmployeeThemeToggle } from "@/components/employee/EmployeeThemeToggle"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/store/useAuthStore"
import { useEmployeeThemeStore } from "@/store/useEmployeeThemeStore"

const NAV: SidebarNavItem[] = [
  { to: "/employee/dashboard", label: "Overview", icon: Home, end: true, subtitle: "Today's summary" },
  { to: "/employee/attendance", label: "Attendance", icon: CalendarDays, subtitle: "Hours & calendar" },
  { to: "/employee/activity", label: "Activity", icon: ClipboardList, subtitle: "Recent events" },
  { to: "/employee/settings", label: "Settings", icon: Settings, subtitle: "Profile & security" },
]

export function EmployeeShell() {
  const user = useAuthStore((s) => s.user)
  const isAdmin = useAuthStore((s) => s.isAdmin())
  const theme = useEmployeeThemeStore((s) => s.theme)
  const navigate = useNavigate()
  const [logoutOpen, setLogoutOpen] = useState(false)
  const isLight = theme === "light"

  const handleLoggedOut = () => navigate("/employee/login")

  const handleSignOut = () => {
    if (isAdmin) {
      void useAuthStore.getState().logout().then(() => navigate("/login"))
    } else {
      setLogoutOpen(true)
    }
  }

  return (
    <>
      <SidebarLayout
        navItems={NAV}
        logoLink="/employee/dashboard"
        logoSubtitle="Workplace"
        portalClassName="employee-portal"
        themeClassName={cn(isLight ? "employee-theme-light" : "employee-theme-dark")}
        backgroundVariant={isLight ? "light" : "dark"}
        sidebarClassName="employee-sidebar border-[var(--emp-sidebar-border)]"
        headerClassName="employee-sidebar border-[var(--emp-sidebar-border)]"
        userName={user?.full_name}
        userMeta={user?.email ?? undefined}
        onSignOut={handleSignOut}
        headerEnd={<EmployeeThemeToggle />}
      >
        <Outlet />
      </SidebarLayout>

      <PalmLogoutDialog open={logoutOpen} onOpenChange={setLogoutOpen} onLoggedOut={handleLoggedOut} />
    </>
  )
}
