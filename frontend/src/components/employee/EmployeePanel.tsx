import { cn } from "@/lib/utils"

export function EmployeePanel({
  title,
  description,
  icon,
  children,
  className,
  headerAction,
}: {
  title: string
  description?: string
  icon?: React.ReactNode
  children: React.ReactNode
  className?: string
  headerAction?: React.ReactNode
}) {
  return (
    <section className={cn("employee-card overflow-hidden", className)}>
      <div className="flex items-start justify-between gap-3 border-b border-[var(--border)] px-3.5 py-3 sm:px-4 sm:py-3.5">
        <div className="flex items-start gap-3">
          {icon && (
            <div className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)]/50 text-[var(--primary)]">
              {icon}
            </div>
          )}
          <div>
            <h2 className="text-sm font-semibold text-[var(--foreground)]">{title}</h2>
            {description && (
              <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">{description}</p>
            )}
          </div>
        </div>
        {headerAction}
      </div>
      <div className="p-3.5 sm:p-4">{children}</div>
    </section>
  )
}
