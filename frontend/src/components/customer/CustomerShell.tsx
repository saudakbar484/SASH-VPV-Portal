import { useState } from "react"

import { Link, NavLink, Outlet, useNavigate } from "react-router-dom"

import {
  Fingerprint,
  Hand,
  HelpCircle,
  History,
  Home,
  LogOut,
  Menu,
  Settings,
  User,
  X,
} from "lucide-react"

import { PortalBackground } from "@/components/PortalBackground"
import { PalmVeinLogo } from "@/components/PalmVeinLogo"
import { CustomerThemeToggle } from "@/components/customer/CustomerThemeToggle"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/store/useAuthStore"
import { useCustomerThemeStore } from "@/store/useCustomerThemeStore"

const NAV = [
  { to: "/user/dashboard", label: "Home", icon: Home, end: true },
  { to: "/user/enroll", label: "Enroll palm", icon: Hand },
  { to: "/user/scan", label: "Scan", icon: Fingerprint },
  { to: "/user/access", label: "My Access", icon: History },
  { to: "/user/profile", label: "Profile", icon: User },
  { to: "/user/settings", label: "Settings", icon: Settings },
  { to: "/user/support", label: "Support", icon: HelpCircle },
]

export function CustomerShell() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const theme = useCustomerThemeStore((s) => s.theme)
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)
  const isLight = theme === "light"

  const handleSignOut = async () => {
    await logout()
    navigate("/")
  }

  return (
    <div
      className={cn(
        "customer-portal relative flex min-h-screen flex-col",
        isLight ? "customer-theme-light" : "customer-theme-dark",
      )}
    >
      <PortalBackground variant={isLight ? "light" : "dark"} />
      <div className="relative z-10 flex min-h-screen flex-col">
        <header className="customer-sidebar sticky top-0 z-40 border-b">
          <div className="mx-auto flex h-14 max-w-6xl items-center gap-2 px-4 sm:h-16 sm:px-6">
            <Link to="/user/dashboard">
              <PalmVeinLogo variant="header" size={28} subtitle="Member Portal" />
            </Link>
            <nav className="hidden min-w-0 flex-1 items-center gap-0.5 overflow-x-auto md:flex">
              {NAV.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-sm font-medium whitespace-nowrap",
                      isActive
                        ? "nav-pill-active"
                        : "text-[var(--muted-foreground)] hover:bg-[var(--accent)]",
                    )
                  }
                >
                  <Icon className="size-4" />
                  <span className="hidden lg:inline">{label}</span>
                </NavLink>
              ))}
            </nav>
            <div className="ml-auto flex items-center gap-2">
              <CustomerThemeToggle />
              <span className="hidden max-w-[140px] truncate text-xs sm:block">{user?.full_name}</span>
              <Button variant="outline" size="sm" onClick={() => void handleSignOut()}>
                <LogOut className="size-4" />
                <span className="hidden sm:inline">Sign out</span>
              </Button>
              <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setMobileOpen(true)}>
                <Menu className="size-5" />
              </Button>
            </div>
          </div>
        </header>

        {mobileOpen && (
          <div className="fixed inset-0 z-50 md:hidden">
            <button type="button" className="absolute inset-0 bg-black/40" onClick={() => setMobileOpen(false)} />
            <aside className="customer-sidebar absolute inset-y-0 right-0 w-72 border-l p-4">
              <div className="flex justify-end">
                <Button variant="ghost" size="icon" onClick={() => setMobileOpen(false)}>
                  <X />
                </Button>
              </div>
              <nav className="mt-2 flex flex-col gap-1">
                {NAV.map(({ to, label, icon: Icon, end }) => (
                  <NavLink
                    key={to}
                    to={to}
                    end={end}
                    onClick={() => setMobileOpen(false)}
                    className={({ isActive }) =>
                      cn("rounded-lg px-3 py-2 text-sm", isActive ? "nav-pill-active" : "")
                    }
                  >
                    <Icon className="mr-2 inline size-4" />
                    {label}
                  </NavLink>
                ))}
              </nav>
            </aside>
          </div>
        )}

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 pb-20 sm:px-6 md:pb-6">
          <Outlet />
        </main>

        <nav className="customer-sidebar fixed inset-x-0 bottom-0 z-40 flex border-t md:hidden">
          {NAV.slice(0, 4).map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex flex-1 flex-col items-center py-2 text-[10px]",
                  isActive ? "text-[var(--primary)]" : "text-[var(--muted-foreground)]",
                )
              }
            >
              <Icon className="size-5" />
              {label.split(" ")[0]}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  )
}
