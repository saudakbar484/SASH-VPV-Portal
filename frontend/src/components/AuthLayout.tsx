import { Link } from "react-router-dom"

import { AdminThemeToggle } from "@/components/admin/AdminThemeToggle"
import { CustomerThemeToggle } from "@/components/customer/CustomerThemeToggle"
import { EmployeeThemeToggle } from "@/components/employee/EmployeeThemeToggle"
import { PalmVeinLogo } from "@/components/PalmVeinLogo"
import { PortalBackground } from "@/components/PortalBackground"
import { cn } from "@/lib/utils"
import { useAdminThemeStore } from "@/store/useAdminThemeStore"
import { useCustomerThemeStore } from "@/store/useCustomerThemeStore"
import { useEmployeeThemeStore } from "@/store/useEmployeeThemeStore"

export type AuthThemePortal = "admin" | "employee" | "customer"

type AuthLayoutProps = {
  children: React.ReactNode
  className?: string
  /** Which portal theme and toggle to use in the top bar. */
  themePortal?: AuthThemePortal
  logoSubtitle?: string
}

function AuthThemeToggle({ portal }: { portal: AuthThemePortal }) {
  if (portal === "admin") return <AdminThemeToggle />
  if (portal === "employee") return <EmployeeThemeToggle />
  return <CustomerThemeToggle />
}

/** Full-screen auth layout with top bar theme toggle and animated backdrop. */
export function AuthLayout({
  children,
  className,
  themePortal = "admin",
  logoSubtitle,
}: AuthLayoutProps) {
  const adminTheme = useAdminThemeStore((s) => s.theme)
  const employeeTheme = useEmployeeThemeStore((s) => s.theme)
  const customerTheme = useCustomerThemeStore((s) => s.theme)

  const activeTheme =
    themePortal === "admin" ? adminTheme : themePortal === "employee" ? employeeTheme : customerTheme
  const isLight = activeTheme === "light"

  const portalClass =
    themePortal === "admin"
      ? "admin-portal"
      : themePortal === "employee"
        ? "employee-portal"
        : "customer-portal"

  const themeClass =
    themePortal === "admin"
      ? isLight
        ? "admin-theme-light"
        : "admin-theme-dark"
      : themePortal === "employee"
        ? isLight
          ? "employee-theme-light"
          : "employee-theme-dark"
        : isLight
          ? "customer-theme-light"
          : "customer-theme-dark"

  const defaultSubtitle =
    themePortal === "admin" ? "Admin" : themePortal === "employee" ? "Employee portal" : "Member portal"

  return (
    <div
      className={cn(
        "auth-bg relative flex min-h-screen min-h-dvh w-full flex-col",
        portalClass,
        themeClass,
      )}
    >
      <PortalBackground variant={isLight ? "light" : "dark"} />
      <header className="relative z-30 flex h-14 shrink-0 items-center gap-3 border-b border-[var(--border)] bg-[color-mix(in_srgb,var(--background)_88%,transparent)] px-4 backdrop-blur-xl sm:h-16 sm:px-6">
        <Link to="/" className="min-w-0">
          <PalmVeinLogo variant="header" size={26} subtitle={logoSubtitle ?? defaultSubtitle} />
        </Link>
        <div className="ml-auto flex items-center gap-2">
          <AuthThemeToggle portal={themePortal} />
        </div>
      </header>
      <div
        className={cn(
          "relative z-10 flex w-full flex-1 flex-col items-center justify-center p-6",
          className,
        )}
      >
        {children}
      </div>
    </div>
  )
}
