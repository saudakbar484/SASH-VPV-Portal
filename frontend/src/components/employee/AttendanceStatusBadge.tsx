import { Badge } from "@/components/ui/badge"
import { statusMeta, type AttendanceStatus } from "@/lib/employeeFormat"
import { cn } from "@/lib/utils"

export function AttendanceStatusBadge({ status, className }: { status: AttendanceStatus; className?: string }) {
  const { label, tone } = statusMeta(status)
  const cls = {
    success: "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
    warning: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300",
    info: "border-sky-500/40 bg-sky-500/10 text-sky-700 dark:text-sky-300",
    danger: "border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-300",
    muted: "border-[var(--border)] bg-[var(--muted)]/30 text-[var(--muted-foreground)]",
  }[tone]

  return (
    <Badge variant="outline" className={cn("capitalize font-medium", cls, className)}>
      {label}
    </Badge>
  )
}
