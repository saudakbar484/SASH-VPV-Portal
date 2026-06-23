import { useState, type ReactNode } from "react"

import { Link, NavLink } from "react-router-dom"

import { LogOut, Menu, X, type LucideIcon } from "lucide-react"

import { PalmVeinLogo } from "@/components/PalmVeinLogo"
import { PortalBackground } from "@/components/PortalBackground"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export type SidebarNavItem = {
  to: string
  label: string
  icon: LucideIcon
  end?: boolean
  subtitle?: string
}

type SidebarLayoutProps = {
  navItems: SidebarNavItem[]
  logoLink: string
  logoSubtitle?: string
  portalClassName: string
  themeClassName?: string
  backgroundVariant?: "light" | "dark"
  sidebarClassName?: string
  headerClassName?: string
  mainClassName?: string
  userName?: string | null
  userMeta?: string | null
  onSignOut?: () => void
  signOutLabel?: string
  headerEnd?: ReactNode
  /** Horizontal tabs in the top bar (e.g. member Enrollment / Recognition). */
  headerNavItems?: SidebarNavItem[]
  /** Sticky strip below header (e.g. weekly training reminder). */
  topBanner?: ReactNode
  /** When true, hide the hamburger sidebar entirely. */
  hideSidebar?: boolean
  children: ReactNode
  defaultSidebarOpen?: boolean
}

export function SidebarLayout({
  navItems,
  logoLink,
  logoSubtitle,
  portalClassName,
  themeClassName,
  backgroundVariant = "dark",
  sidebarClassName = "",
  headerClassName = "",
  mainClassName = "",
  userName,
  userMeta,
  onSignOut,
  signOutLabel = "Sign out",
  headerEnd,
  headerNavItems,
  topBanner,
  hideSidebar = false,
  children,
  defaultSidebarOpen = false,
}: SidebarLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(defaultSidebarOpen)
  const closeSidebar = () => setSidebarOpen(false)
  const toggleSidebar = () => setSidebarOpen((o) => !o)
  const showSidebar = !hideSidebar

  return (
    <div className={cn("relative flex min-h-screen w-full", portalClassName, themeClassName)}>
      <PortalBackground variant={backgroundVariant} />

      {showSidebar && (
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-[min(100%,280px)] flex-col border-r shadow-xl transition-transform duration-200",
          sidebarClassName,
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-14 items-center justify-between border-b px-4 lg:h-16">
          <Link to={logoLink} className="min-w-0">
            <PalmVeinLogo variant="header" size={26} subtitle={logoSubtitle} />
          </Link>
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0"
            onClick={closeSidebar}
            aria-label="Close navigation"
          >
            <X className="size-5" />
          </Button>
        </div>

        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
          {navItems.map(({ to, label, icon: Icon, end, subtitle }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "sidebar-nav-link group flex items-start gap-3 rounded-xl px-3 py-2.5 transition-all duration-200",
                  isActive
                    ? "nav-pill-active shadow-md"
                    : "text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--foreground)]",
                )
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={cn(
                      "mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg border transition-all duration-200",
                      isActive
                        ? "border-white/25 bg-white/15"
                        : "border-[var(--border)] bg-[color-mix(in_srgb,var(--accent)_60%,transparent)] group-hover:border-[color-mix(in_srgb,var(--primary)_35%,transparent)] group-hover:shadow-sm",
                    )}
                  >
                    <Icon className="size-4 shrink-0" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-semibold leading-tight">{label}</span>
                    {subtitle && (
                      <span
                        className={cn(
                          "mt-0.5 block text-[11px] leading-snug",
                          isActive ? "text-white/85" : "opacity-70",
                        )}
                      >
                        {subtitle}
                      </span>
                    )}
                  </span>
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </aside>
      )}

      <div
        className={cn(
          "relative z-10 flex min-h-screen w-full flex-1 flex-col transition-[margin] duration-200",
          showSidebar && sidebarOpen && "ml-[min(100%,280px)]",
        )}
      >
        <header
          className={cn(
            "sticky top-0 z-30 flex h-14 shrink-0 items-center gap-3 border-b px-3 sm:px-5 lg:h-16 lg:px-6",
            headerClassName,
          )}
        >
          {showSidebar ? (
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleSidebar}
              aria-label={sidebarOpen ? "Close navigation" : "Open navigation"}
              aria-expanded={sidebarOpen}
            >
              <Menu className="size-5" />
            </Button>
          ) : null}

          <Link to={logoLink} className={cn("min-w-0", showSidebar && "lg:hidden")}>
            <PalmVeinLogo variant="header" size={24} subtitle={logoSubtitle} />
          </Link>

          {headerNavItems && headerNavItems.length > 0 && (
            <nav
              className="flex min-w-0 flex-1 items-center justify-center gap-1 sm:justify-start sm:pl-2"
              aria-label="Member navigation"
            >
              {headerNavItems.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    cn(
                      "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition-colors",
                      isActive
                        ? "nav-pill-active shadow-sm"
                        : "text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--foreground)]",
                    )
                  }
                >
                  <Icon className="size-4 shrink-0" />
                  <span>{label}</span>
                </NavLink>
              ))}
            </nav>
          )}

          <div className={cn("ml-auto flex shrink-0 items-center gap-2 sm:gap-3")}>
            {headerEnd}
            {(userName || userMeta) && (
              <div className="hidden min-w-0 text-right sm:block">
                {userName && (
                  <div className="max-w-[160px] truncate text-sm font-semibold leading-tight lg:max-w-[200px]">
                    {userName}
                  </div>
                )}
                {userMeta && (
                  <div className="max-w-[160px] truncate text-[11px] text-[var(--muted-foreground)] lg:max-w-[220px]">
                    {userMeta}
                  </div>
                )}
              </div>
            )}
            {onSignOut && (
              <Button variant="outline" size="sm" className="gap-1.5" onClick={onSignOut}>
                <LogOut className="size-4" />
                <span className="hidden sm:inline">{signOutLabel}</span>
              </Button>
            )}
          </div>
        </header>

        {topBanner}

        <main className={cn("w-full flex-1 px-3 py-4 sm:px-5 sm:py-6 lg:px-8 lg:py-7", mainClassName)}>
          {children}
        </main>
      </div>
    </div>
  )
}
