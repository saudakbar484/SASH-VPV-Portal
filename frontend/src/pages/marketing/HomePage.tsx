import { Link } from "react-router-dom"

import type { ReactNode } from "react"

import { useQuery } from "@tanstack/react-query"

import {
  ArrowRight,
  Brain,
  Building2,
  Fingerprint,
  Lock,
  Scan,
  Shield,
  Sparkles,
  Users,
  Zap,
} from "lucide-react"

import { PalmScanDemo } from "@/components/customer/PalmScanDemo"
import { HomeFaqSection } from "@/components/marketing/HomeFaqSection"
import { PortalCards } from "@/components/marketing/PortalCards"
import { SashVpvDatasetSection } from "@/components/marketing/SashVpvDatasetSection"
import { Button } from "@/components/ui/button"
import { useRevealOnScroll } from "@/hooks/useRevealOnScroll"
import { endpoints } from "@/lib/api"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/store/useAuthStore"

const FEATURES = [
  {
    icon: Fingerprint,
    title: "Dual-hand enrollment",
    desc: "Guided NIR capture — 10 frames per palm — builds robust 512-d vein templates.",
    to: "/how-it-works",
    cta: "See the journey",
  },
  {
    icon: Brain,
    title: "Deep learning matcher",
    desc: "EfficientNet-B0 + CBAM + ArcFace training for discriminative vein embeddings.",
    to: "/technology",
    cta: "Explore tech",
  },
  {
    icon: Scan,
    title: "1:1 & 1:N recognition",
    desc: "Verify a claimed identity or search the gallery in milliseconds on live capture.",
    to: "/member/recognition",
    cta: "Try recognition",
    memberOnly: true,
  },
  {
    icon: Shield,
    title: "Enterprise security",
    desc: "Role-isolated portals, audit logs, margin checks, and encrypted template storage.",
    to: "/security",
    cta: "Security model",
  },
  {
    icon: Building2,
    title: "Multi-portal access",
    desc: "Dedicated experiences for members, employees, and administrators.",
    to: "/solutions",
    cta: "View solutions",
  },
  {
    icon: Zap,
    title: "Live sensor integration",
    desc: "XRTECH NIR scanner with real-time preview, quality gates, and auto-healing capture.",
    to: "/technology",
    cta: "Hardware stack",
  },
]

const PIPELINE = [
  "NIR capture",
  "ROI & landmarks",
  "Vein enhancement",
  "Neural embedding",
  "Cosine match",
  "Access granted",
]

function RevealSection({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode
  className?: string
  delay?: number
}) {
  const { ref, visible } = useRevealOnScroll<HTMLDivElement>()
  return (
    <div
      ref={ref}
      className={cn("marketing-reveal", visible && "is-visible", className)}
      style={{ transitionDelay: visible ? `${delay}ms` : undefined }}
    >
      {children}
    </div>
  )
}

export function HomePage() {
  const token = useAuthStore((s) => s.token)
  const isCustomer = useAuthStore((s) => s.isCustomer())
  const user = useAuthStore((s) => s.user)

  const stats = useQuery({
    queryKey: ["public-stats"],
    queryFn: endpoints.public.stats,
  })

  const primaryCta = isCustomer && token ? "/member/enrollment" : "/user/signup"
  const primaryLabel = isCustomer && token ? "Enroll your palm" : "Get started free"
  const secondaryCta = isCustomer && token ? "/member/recognition" : "/how-it-works"
  const secondaryLabel = isCustomer && token ? "Run recognition" : "See how it works"

  return (
    <div className="relative overflow-hidden">
      <div
        className="marketing-orb left-[10%] top-20 size-72 bg-[var(--brand-orange)] opacity-30"
        aria-hidden
      />
      <div
        className="marketing-orb bottom-32 right-[5%] size-96 bg-[var(--brand-peach-muted)] opacity-20"
        style={{ animationDelay: "2s" }}
        aria-hidden
      />

      {/* Hero */}
      <section className="relative mx-auto max-w-6xl px-6 py-16 sm:py-24">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          <RevealSection>
            {isCustomer && token && user && (
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-[var(--primary)]/30 bg-[color-mix(in_srgb,var(--primary)_12%,transparent)] px-4 py-1.5 text-xs font-medium text-[var(--primary)]">
                <Sparkles className="size-3.5" />
                Welcome back, {user.full_name.split(" ")[0]}
              </div>
            )}
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--primary)]">
              NIR Palm Vein Biometrics
            </p>
            <h1 className="mt-3 text-4xl font-bold leading-[1.1] tracking-tight sm:text-5xl lg:text-[3.25rem]">
              Contactless identity.
              <span className="marketing-gradient-text mt-1 block">Verified by your palm.</span>
            </h1>
            <p className="mt-5 max-w-lg text-lg leading-relaxed text-[var(--muted-foreground)]">
              Enterprise-grade authentication powered by subsurface vein patterns — private,
              spoof-resistant, and impossible to leave behind like a card or password.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg" className="btn-brand group shadow-lg shadow-[var(--brand-orange)]/20">
                <Link to={primaryCta}>
                  {primaryLabel}
                  <ArrowRight className="ml-1 size-4 transition-transform group-hover:translate-x-0.5" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline" className="backdrop-blur-sm">
                <Link to={secondaryCta}>{secondaryLabel}</Link>
              </Button>
            </div>
            <div className="mt-8 flex flex-wrap gap-2">
              {["Liveness-safe", "512-d embeddings", "Audit trail", "GPU-ready"].map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-[var(--border)] bg-[color-mix(in_srgb,var(--card)_80%,transparent)] px-3 py-1 text-[11px] font-medium uppercase tracking-wider text-[var(--muted-foreground)]"
                >
                  {tag}
                </span>
              ))}
            </div>
          </RevealSection>

          <RevealSection delay={120} className="flex justify-center">
            <div className="relative" style={{ animation: "marketing-float 6s ease-in-out infinite" }}>
              <div className="absolute -inset-4 rounded-3xl bg-[radial-gradient(circle,color-mix(in_srgb,var(--primary)_25%,transparent),transparent_70%)]" />
              <PalmScanDemo />
            </div>
          </RevealSection>
        </div>
      </section>

      {/* Pipeline strip */}
      <section className="border-y border-[var(--border)] bg-[color-mix(in_srgb,var(--accent)_45%,transparent)]">
        <RevealSection className="mx-auto max-w-6xl px-6 py-10">
          <p className="text-center text-xs font-semibold uppercase tracking-[0.2em] text-[var(--primary)]">
            End-to-end pipeline
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-2 sm:gap-0">
            {PIPELINE.map((step, i) => (
              <div key={step} className="flex items-center">
                <span className="rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-xs font-medium shadow-sm sm:text-sm">
                  {step}
                </span>
                {i < PIPELINE.length - 1 && (
                  <ArrowRight className="mx-1 hidden size-4 text-[var(--muted-foreground)] sm:block" />
                )}
              </div>
            ))}
          </div>
          <p className="mx-auto mt-4 max-w-2xl text-center text-sm text-[var(--muted-foreground)]">
            From scanner frame to access decision in under a second — with quality gates that reject
            partial or obstructed palms before they reach the model.
          </p>
        </RevealSection>
      </section>

      {/* SASH-VPV dataset contribution */}
      <section className="mx-auto max-w-6xl px-6 pb-4">
        <RevealSection>
          <SashVpvDatasetSection />
        </RevealSection>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <RevealSection className="text-center">
          <h2 className="text-2xl font-bold sm:text-3xl">Built for real-world biometrics</h2>
          <p className="mx-auto mt-3 max-w-xl text-[var(--muted-foreground)]">
            Every layer — optics, preprocessing, neural network, and policy — is designed for
            accurate matching and clear operator workflows.
          </p>
        </RevealSection>
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => {
            const Icon = f.icon
            const href = f.memberOnly && !(isCustomer && token) ? "/user/signup" : f.to
            return (
              <RevealSection key={f.title} delay={i * 60}>
                <Link to={href} className="marketing-feature-card block h-full p-6">
                  <div className="marketing-icon-ring mb-4">
                    <Icon className="size-5 text-[var(--primary)]" />
                  </div>
                  <h3 className="font-semibold">{f.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-[var(--muted-foreground)]">{f.desc}</p>
                  <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-[var(--primary)]">
                    {f.cta}
                    <ArrowRight className="size-3.5" />
                  </span>
                </Link>
              </RevealSection>
            )
          })}
        </div>
      </section>

      {/* Live stats */}
      {stats.data && (
        <section className="border-y border-[var(--border)] bg-[color-mix(in_srgb,var(--card)_50%,transparent)]">
          <div className="mx-auto max-w-6xl px-6 py-14">
            <RevealSection className="mb-8 text-center">
              <h2 className="text-2xl font-bold">Platform at a glance</h2>
              <p className="mt-2 text-sm text-[var(--muted-foreground)]">
                Live counts from your deployed instance
              </p>
            </RevealSection>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                { label: "Registered members", value: stats.data.total_customers, icon: Users },
                { label: "Employees", value: stats.data.total_employees, icon: Building2 },
                { label: "Enrolled hands", value: stats.data.enrolled_identities, icon: Fingerprint },
                { label: "Match threshold", value: stats.data.match_threshold.toFixed(3), icon: Lock },
              ].map((s, i) => {
                const Icon = s.icon
                return (
                  <RevealSection key={s.label} delay={i * 80}>
                    <div className="customer-card marketing-stat-card p-5 text-center">
                      <Icon className="mx-auto size-5 text-[var(--primary)]" />
                      <div className="mt-3 text-3xl font-bold tabular-nums text-[var(--primary)]">
                        {s.value}
                      </div>
                      <div className="mt-1 text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
                        {s.label}
                      </div>
                    </div>
                  </RevealSection>
                )
              })}
            </div>
          </div>
        </section>
      )}

      {/* Portals */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <PortalCards />
      </section>

      <HomeFaqSection />

      {/* CTA */}
      <section className="mx-auto max-w-6xl px-6 pb-20">
        <RevealSection>
          <div className="relative overflow-hidden rounded-2xl border border-[color-mix(in_srgb,var(--primary)_30%,transparent)] bg-[color-mix(in_srgb,var(--primary)_10%,var(--card))] px-8 py-12 text-center shadow-xl">
            <div className="marketing-hero-glow absolute left-1/2 top-0 size-48 -translate-x-1/2 -translate-y-1/2" />
            <h2 className="relative text-2xl font-bold sm:text-3xl">
              {isCustomer && token ? "Ready to scan your palm?" : "Ready to enroll your palm?"}
            </h2>
            <p className="relative mx-auto mt-3 max-w-md text-sm text-[var(--muted-foreground)]">
              {isCustomer && token
                ? "Open Enrollment from the menu to register both hands, then use Recognition for live verification."
                : "Create a member account in minutes — email verification or instant Google sign-up."}
            </p>
            <Button asChild size="lg" className="btn-brand relative mt-6">
              <Link to={primaryCta}>{primaryLabel}</Link>
            </Button>
          </div>
        </RevealSection>
      </section>
    </div>
  )
}
