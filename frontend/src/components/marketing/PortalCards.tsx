import { Link } from "react-router-dom"

import {
  ArrowRight,
  Briefcase,
  LayoutDashboard,
  LogIn,
  Monitor,
  UserPlus,
  Users,
  type LucideIcon,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { useRevealOnScroll } from "@/hooks/useRevealOnScroll"
import { cn } from "@/lib/utils"

export type PortalCardItem = {
  title: string
  challenge: string
  solution: string
  icon: LucideIcon
  accent: string
  primary: { to: string; label: string; icon?: LucideIcon }
  secondary?: { to: string; label: string; icon?: LucideIcon }
}

export const PORTAL_CARDS: PortalCardItem[] = [
  {
    title: "Member access",
    challenge: "External users need secure identity without carrying cards.",
    solution: "Public home portal with palm enrollment and live recognition.",
    icon: Users,
    accent: "from-[var(--brand-orange)]/20 to-transparent",
    primary: { to: "/user/signup", label: "Register as member", icon: UserPlus },
    secondary: { to: "/user/login", label: "Sign in", icon: LogIn },
  },
  {
    title: "Workplace attendance",
    challenge: "Staff need trustworthy check-in/out with time records.",
    solution: "Employee portal with attendance calendar and palm logout.",
    icon: Briefcase,
    accent: "from-[var(--brand-peach-muted)]/30 to-transparent",
    primary: { to: "/employee/login", label: "Employee sign in", icon: LogIn },
    secondary: { to: "/employee/signup", label: "Create account", icon: UserPlus },
  },
  {
    title: "Auth kiosk",
    challenge: "Shared terminal for quick palm authentication at entrances.",
    solution: "Full-screen kiosk mode for lobbies and reception desks.",
    icon: Monitor,
    accent: "from-emerald-500/15 to-transparent",
    primary: { to: "/kiosk", label: "Open kiosk", icon: Monitor },
  },
  {
    title: "Admin operations",
    challenge: "HR and IT need policies, reports, and device control.",
    solution: "Admin console for identities, employees, customers, and logs.",
    icon: LayoutDashboard,
    accent: "from-violet-500/15 to-transparent",
    primary: { to: "/login", label: "Admin login", icon: LogIn },
    secondary: { to: "/solutions", label: "View solutions", icon: LayoutDashboard },
  },
]

type PortalCardsProps = {
  className?: string
  showHeader?: boolean
}

export function PortalCards({ className, showHeader = true }: PortalCardsProps) {
  const { ref, visible } = useRevealOnScroll<HTMLDivElement>()

  return (
    <div className={className}>
      {showHeader && (
        <div className="mb-10 text-center">
          <h2 className="text-2xl font-bold sm:text-3xl">Choose your portal</h2>
          <p className="mx-auto mt-3 max-w-xl text-[var(--muted-foreground)]">
            Pick the experience that matches your role — each portal is purpose-built for members,
            staff, kiosk terminals, or administrators.
          </p>
        </div>
      )}

      <div
        ref={ref}
        className={cn("marketing-reveal grid gap-5 sm:grid-cols-2", visible && "is-visible")}
      >
        {PORTAL_CARDS.map((card, i) => {
          const Icon = card.icon
          const PrimaryIcon = card.primary.icon ?? ArrowRight
          const SecondaryIcon = card.secondary?.icon ?? LogIn

          return (
            <article
              key={card.title}
              className="marketing-feature-card group relative flex h-full flex-col overflow-hidden p-6"
              style={{ transitionDelay: `${i * 60}ms` }}
            >
              <div
                className={cn(
                  "pointer-events-none absolute inset-0 bg-gradient-to-br opacity-80",
                  card.accent,
                )}
              />
              <div className="relative flex flex-1 flex-col">
                <div className="flex items-start gap-4">
                  <div className="marketing-icon-ring shrink-0 !p-2.5">
                    <Icon className="size-5 text-[var(--primary)]" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-lg font-bold tracking-tight">{card.title}</h3>
                  </div>
                </div>

                <p className="relative mt-4 text-sm leading-relaxed text-[var(--muted-foreground)]">
                  <span className="font-semibold text-[var(--foreground)]">Challenge: </span>
                  {card.challenge}
                </p>
                <p className="relative mt-2 text-sm leading-relaxed">
                  <span className="font-semibold text-[var(--primary)]">Solution: </span>
                  {card.solution}
                </p>

                <div className="relative mt-6 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                  <Button asChild className="btn-brand w-full sm:w-auto sm:min-w-[10rem]">
                    <Link to={card.primary.to}>
                      <PrimaryIcon className="size-4" />
                      {card.primary.label}
                      <ArrowRight className="size-3.5 opacity-80" />
                    </Link>
                  </Button>
                  {card.secondary && (
                    <Button asChild variant="outline" className="w-full sm:w-auto">
                      <Link to={card.secondary.to}>
                        <SecondaryIcon className="size-4" />
                        {card.secondary.label}
                      </Link>
                    </Button>
                  )}
                </div>
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}
