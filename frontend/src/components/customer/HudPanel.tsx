import { cn } from "@/lib/utils"

export function HudPanel({
  children,
  title,
  className,
}: {
  children: React.ReactNode
  title?: string
  className?: string
}) {
  return (
    <div className={cn("hud-panel p-4 sm:p-5", className)}>
      {title && (
        <div className="mb-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--primary)]">
          {title}
        </div>
      )}
      {children}
    </div>
  )
}
