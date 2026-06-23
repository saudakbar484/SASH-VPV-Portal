import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

interface GlassPanelProps {
  title?: string
  description?: string
  icon?: ReactNode
  headerExtra?: ReactNode
  children: ReactNode
  className?: string
  bodyClassName?: string
}

export function GlassPanel({
  title,
  description,
  icon,
  headerExtra,
  children,
  className,
  bodyClassName,
}: GlassPanelProps) {
  return (
    <div className={cn("glass-panel p-5", className)}>
      {(title || description || headerExtra) && (
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            {(title || icon) && (
              <div className="flex items-center gap-2">
                {icon}
                {title && (
                  <h2 className="text-lg font-semibold tracking-wide">{title}</h2>
                )}
              </div>
            )}
            {description && (
              <p className="mt-1 text-sm text-[var(--muted-foreground)]">{description}</p>
            )}
          </div>
          {headerExtra}
        </div>
      )}
      <div className={bodyClassName}>{children}</div>
    </div>
  )
}

export function LiveFeedFrame({
  children,
  hint,
}: {
  children: ReactNode
  hint?: string
}) {
  return (
    <div className="flex justify-center rounded-xl border border-white/10 bg-black/60 p-2">
      {children}
      {hint && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <p className="rounded-lg bg-black/70 px-4 py-2 text-sm text-white/80">{hint}</p>
        </div>
      )}
    </div>
  )
}
