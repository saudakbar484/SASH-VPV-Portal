import { Outlet, useNavigate } from "react-router-dom"

import {
  Activity,
  Briefcase,
  ClipboardList,
  Hand,
  ScanFace,
  Settings,
  UserCircle,
  Users,
} from "lucide-react"

import { SidebarLayout, type SidebarNavItem } from "@/components/SidebarLayout"
import { AdminThemeToggle } from "@/components/admin/AdminThemeToggle"
import { TrainingReminderBanner } from "@/components/admin/TrainingReminderBanner"
import { cn } from "@/lib/utils"
import { useAdminThemeStore } from "@/store/useAdminThemeStore"
import { useAuthStore } from "@/store/useAuthStore"

const NAV: SidebarNavItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: Activity, end: true, subtitle: "Stats & quick actions" },
  { to: "/enroll", label: "Enrollment", icon: Hand, subtitle: "Capture new palms" },
  { to: "/recognize", label: "Recognition", icon: ScanFace, subtitle: "Verify & identify" },
  { to: "/identities", label: "Identities", icon: Users, subtitle: "Enrolled gallery" },
  { to: "/employees", label: "Employees", icon: Briefcase, subtitle: "Staff & attendance" },
  { to: "/customers", label: "Customers", icon: UserCircle, subtitle: "Member accounts" },
  { to: "/logs", label: "Logs", icon: ClipboardList, subtitle: "Audit history" },
  { to: "/settings", label: "Settings", icon: Settings, subtitle: "Policy & email" },
]

export function AppShell() {
  const theme = useAdminThemeStore((s) => s.theme)
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const navigate = useNavigate()
  const isLight = theme === "light"

  return (
    <SidebarLayout
      navItems={NAV}
      logoLink="/dashboard"
      logoSubtitle="Admin"
      portalClassName="admin-portal"
      themeClassName={cn(isLight ? "admin-theme-light" : "admin-theme-dark")}
      backgroundVariant={isLight ? "light" : "dark"}
      sidebarClassName="admin-header border-[var(--admin-header-border)] bg-[color-mix(in_srgb,var(--admin-header)_92%,transparent)]"
      headerClassName="admin-header border-[var(--admin-header-border)] bg-[color-mix(in_srgb,var(--admin-header)_90%,transparent)] backdrop-blur-xl"
      mainClassName="mx-auto max-w-[1400px]"
      userName={user?.full_name ?? "Admin"}
      userMeta="Administrator"
      onSignOut={() => {
        void logout().then(() => navigate("/login"))
      }}
      headerEnd={<AdminThemeToggle />}
      topBanner={<TrainingReminderBanner />}
    >
      <Outlet />
    </SidebarLayout>
  )
}
