import type { LucideIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { useRevealOnScroll } from "@/hooks/useRevealOnScroll"

type MarketingPageHeroProps = {
  icon: LucideIcon
  eyebrow: string
  title: string
  description: string
  className?: string
}

export function MarketingPageHero({
  icon: Icon,
  eyebrow,
  title,
  description,
  className,
}: MarketingPageHeroProps) {
  const { ref, visible } = useRevealOnScroll<HTMLDivElement>()

  return (
    <div
      ref={ref}
      className={cn(
        "marketing-reveal relative overflow-hidden border-b border-[var(--border)] px-6 py-14 sm:py-16",
        visible && "is-visible",
        className,
      )}
    >
      <div className="marketing-hero-glow pointer-events-none absolute -right-20 -top-20 size-64 rounded-full opacity-40" />
      <div className="relative mx-auto max-w-4xl">
        <div className="marketing-icon-ring mb-4 inline-flex">
          <Icon className="size-6 text-[var(--primary)]" />
        </div>
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--primary)]">{eyebrow}</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">{title}</h1>
        <p className="mt-3 max-w-2xl text-base text-[var(--muted-foreground)] sm:text-lg">{description}</p>
      </div>
    </div>
  )
}
