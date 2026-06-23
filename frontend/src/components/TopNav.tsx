import { NavLink, Link, useNavigate } from "react-router-dom"
import { Activity, Briefcase, ClipboardList, Hand, LogOut, ScanFace, Settings, Shield, UserCircle, Users } from "lucide-react"
import { Button } from "@/components/ui/button"
import { PalmVeinLogo } from "@/components/PalmVeinLogo"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/store/useAuthStore"

const TABS = [
  { to: "/dashboard", label: "Dashboard", icon: Activity, end: true },
  { to: "/enroll", label: "Enrollment", icon: Hand },
  { to: "/recognize", label: "Recognition", icon: ScanFace },
  { to: "/identities", label: "Identities", icon: Users },
  { to: "/employees", label: "Employees", icon: Briefcase },
  { to: "/customers", label: "Customers", icon: UserCircle },
  { to: "/logs", label: "Logs", icon: ClipboardList },
  { to: "/settings", label: "Settings", icon: Settings },
]

export function TopNav() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const navigate = useNavigate()

  return (
    <header className="admin-header sticky top-0 z-40 border-b backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-[1400px] items-center justify-between gap-4 px-6">
        <Link to="/dashboard" className="shrink-0 rounded-md transition-opacity hover:opacity-90">
          <PalmVeinLogo variant="header" size={32} />
        </Link>

        <nav className="hidden items-center gap-1 lg:flex">
          {TABS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "admin-nav-link flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition",
                  isActive
                    ? "admin-nav-link-active nav-pill-active"
                    : "text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--foreground)]",
                )
              }
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <div className="hidden text-right sm:block">
            <div className="flex items-center justify-end gap-1.5">
              <Shield className="size-3.5 text-emerald-400" />
              <span className="text-sm font-semibold">{user?.full_name ?? "Admin"}</span>
            </div>
            <div className="flex items-center justify-end gap-1 text-xs text-emerald-400">
              <span className="size-1.5 rounded-full bg-emerald-400" />
              Administrator
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="border-[var(--border)] bg-[var(--accent)]/30"
            onClick={async () => {
              await logout()
              navigate("/login")
            }}
          >
            <LogOut className="size-4" />
            Sign Out
          </Button>
        </div>
      </div>
    </header>
  )
}
