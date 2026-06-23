import { useEffect, useState } from "react"

import { Link } from "react-router-dom"

import { Route, ArrowRight } from "lucide-react"

import { BiometricScanRing } from "@/components/customer/BiometricScanRing"
import { HudPanel } from "@/components/customer/HudPanel"
import { MarketingPageHero } from "@/components/marketing/MarketingPageHero"
import { Button } from "@/components/ui/button"
import { useRevealOnScroll } from "@/hooks/useRevealOnScroll"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/store/useAuthStore"

const STEPS = [
  {
    title: "Create your account",
    desc: "Register with email + verification code, or sign up instantly with Google.",
    link: "/user/signup",
  },
  {
    title: "Enroll both palms",
    desc: "Ten guided captures per hand build averaged left/right vein templates.",
    link: "/member/enrollment",
  },
  {
    title: "Live verification",
    desc: "Hold your palm over the scanner — the matcher returns similarity and confidence.",
    link: "/member/recognition",
  },
  {
    title: "Audited access",
    desc: "Every login, verification, and enrollment is logged for compliance review.",
    link: "/security",
  },
]

export function HowItWorksPage() {
  const [demoProgress, setDemoProgress] = useState(0)
  const isCustomer = useAuthStore((s) => s.isCustomer())
  const token = useAuthStore((s) => s.token)
  const { ref, visible } = useRevealOnScroll<HTMLOListElement>()

  useEffect(() => {
    const t = setInterval(() => {
      setDemoProgress((p) => (p >= 100 ? 0 : p + 2))
    }, 80)
    return () => clearInterval(t)
  }, [])

  const startLink = isCustomer && token ? "/member/enrollment" : "/user/signup"

  return (
    <div>
      <MarketingPageHero
        icon={Route}
        eyebrow="User journey"
        title="How it works"
        description="From first sign-up to trusted palm access — a clear, consent-based flow designed for members and operators alike."
      />

      <div className="mx-auto max-w-4xl px-6 py-12">
        <ol
          ref={ref}
          className={cn("marketing-reveal space-y-4", visible && "is-visible")}
        >
          {STEPS.map((step, i) => (
            <li key={step.title}>
              <Link
                to={step.link}
                className="marketing-feature-card flex gap-4 p-5 transition-transform"
              >
                <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-[var(--primary)] text-sm font-bold text-white shadow-lg shadow-[var(--brand-orange)]/25">
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <h3 className="font-semibold">{step.title}</h3>
                  <p className="mt-1 text-sm text-[var(--muted-foreground)]">{step.desc}</p>
                  <span className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-[var(--primary)]">
                    Learn more <ArrowRight className="size-3" />
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ol>

        <HudPanel title="Interactive verification demo" className="mt-10 flex flex-col items-center">
          <BiometricScanRing progress={demoProgress} label="SCAN" />
          <p className="mt-4 text-xs text-[var(--muted-foreground)]">
            Simulated live-match progress — real scans complete in seconds
          </p>
        </HudPanel>

        <Button asChild className="btn-brand mt-8">
          <Link to={startLink}>
            {isCustomer && token ? "Continue enrollment" : "Start enrollment"}
            <ArrowRight className="ml-1 size-4" />
          </Link>
        </Button>
      </div>
    </div>
  )
}
