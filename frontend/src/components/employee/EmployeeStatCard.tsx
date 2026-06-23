import { cn } from "@/lib/utils"

export function EmployeeStatCard({
  label,
  value,
  sub,
  icon,
  accent = "default",
}: {
  label: string
  value: string
  sub?: string
  icon?: React.ReactNode
  accent?: "default" | "success" | "warning" | "danger" | "info" | "purple"
}) {
  const accentCls = {
    default: "text-[var(--foreground)]",
    success: "text-emerald-600 dark:text-emerald-400",
    warning: "text-amber-600 dark:text-amber-400",
    danger: "text-red-600 dark:text-red-400",
    info: "text-sky-600 dark:text-sky-400",
    purple: "text-[var(--primary)]",
  }[accent]

  return (
    <div className="employee-card flex flex-col gap-2 p-3.5 sm:gap-2.5 sm:p-4">
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
          {label}
        </span>
        {icon && <div className="text-[var(--muted-foreground)] opacity-80">{icon}</div>}
      </div>
      <div>
        <div className={cn("text-xl font-bold tabular-nums tracking-tight sm:text-2xl", accentCls)}>{value}</div>
        {sub && <p className="mt-1 text-xs text-[var(--muted-foreground)]">{sub}</p>}
      </div>
    </div>
  )
}
