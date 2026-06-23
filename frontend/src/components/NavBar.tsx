import { NavLink } from "react-router-dom"
import {
  Activity,
  Fingerprint,
  Moon,
  ScanFace,
  Sliders,
  Sun,
  Users,
  ClipboardList,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useAppStore } from "@/store/useAppStore"
import { useEffect } from "react"

interface NavItem {
  to: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  end?: boolean
}

const NAV: NavItem[] = [
  { to: "/", label: "Live Preview", icon: Activity, end: true },
  { to: "/enroll", label: "Enrollment", icon: Fingerprint },
  { to: "/recognize", label: "Recognition", icon: ScanFace },
  { to: "/identities", label: "Identities", icon: Users },
  { to: "/logs", label: "Logs", icon: ClipboardList },
  { to: "/device", label: "Device Control", icon: Sliders },
]

export function NavBar() {
  const darkMode = useAppStore((s) => s.darkMode)
  const toggleDarkMode = useAppStore((s) => s.toggleDarkMode)

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode)
  }, [darkMode])

  return (
    <aside className="flex h-full w-64 flex-col border-r border-[var(--border)] bg-[var(--card)] px-3 py-4">
      <div className="px-3 pb-4">
        <div className="flex items-center gap-2 text-lg font-semibold">
          <Fingerprint className="size-5 text-[var(--primary)]" />
          <span>Palm Vein</span>
        </div>
        <p className="mt-1 text-xs text-[var(--muted-foreground)]">
          XRTECH MagicVein Plus
        </p>
      </div>

      <nav className="flex-1 space-y-1">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-[var(--accent)] text-[var(--accent-foreground)]"
                  : "text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--accent-foreground)]",
              )
            }
          >
            <Icon className="size-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-[var(--border)] pt-3">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start"
          onClick={toggleDarkMode}
        >
          {darkMode ? <Sun className="size-4" /> : <Moon className="size-4" />}
          {darkMode ? "Light mode" : "Dark mode"}
        </Button>
      </div>
    </aside>
  )
}
