import { Moon, Sun } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useEmployeeThemeStore } from "@/store/useEmployeeThemeStore"

export function EmployeeThemeToggle({ className }: { className?: string }) {
  const theme = useEmployeeThemeStore((s) => s.theme)
  const toggleTheme = useEmployeeThemeStore((s) => s.toggleTheme)
  const isLight = theme === "light"

  return (
    <Button
      type="button"
      variant="outline"
      size="icon"
      className={cn("shrink-0 border-[var(--border)] bg-[color-mix(in_srgb,var(--card)_80%,transparent)]", className)}
      onClick={toggleTheme}
      aria-label={isLight ? "Switch to dark theme" : "Switch to light theme"}
    >
      {isLight ? <Moon className="size-4" /> : <Sun className="size-4" />}
    </Button>
  )
}
