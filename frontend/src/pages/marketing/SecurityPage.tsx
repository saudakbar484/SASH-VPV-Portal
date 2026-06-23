import { Link } from "react-router-dom"

import { Lock, ShieldCheck } from "lucide-react"

import { MarketingPageHero } from "@/components/marketing/MarketingPageHero"
import { Button } from "@/components/ui/button"
import { useRevealOnScroll } from "@/hooks/useRevealOnScroll"
import { cn } from "@/lib/utils"

const ITEMS = [
  {
    title: "Vein-internal pattern",
    desc: "Patterns lie beneath the skin — extremely difficult to spoof with prints or photos.",
  },
  {
    title: "Embedding-only matching",
    desc: "512-d mathematical templates are compared — raw vein images are not replayed for auth.",
  },
  {
    title: "Role isolation",
    desc: "Admin, employee, and member portals are separated with distinct login policies.",
  },
  {
    title: "Margin-aware matching",
    desc: "Top-1 vs top-2 similarity margin reduces ambiguous false accepts on login.",
  },
  {
    title: "Full audit trail",
    desc: "Logins, verifications, enrollments, and failed attempts are recorded with timestamps.",
  },
  {
    title: "Explicit consent",
    desc: "Biometric processing consent is required before palm capture during enrollment.",
  },
]

export function SecurityPage() {
  const { ref, visible } = useRevealOnScroll<HTMLDivElement>()

  return (
    <div>
      <MarketingPageHero
        icon={ShieldCheck}
        eyebrow="Trust & compliance"
        title="Security architecture"
        description="Defense in depth for biometric identity — from template storage to portal access policies and operator visibility."
      />

      <div className="mx-auto max-w-4xl px-6 py-12">
        <div
          ref={ref}
          className={cn("marketing-reveal grid gap-4 sm:grid-cols-2", visible && "is-visible")}
        >
          {ITEMS.map((item) => (
            <div key={item.title} className="marketing-feature-card p-5">
              <Lock className="size-5 text-[var(--primary)]" />
              <h3 className="mt-3 font-semibold">{item.title}</h3>
              <p className="mt-2 text-sm text-[var(--muted-foreground)]">{item.desc}</p>
            </div>
          ))}
        </div>

        <div className="mt-8 flex gap-3">
          <Button asChild variant="outline">
            <Link to={{ pathname: "/", hash: "#faq" }}>Read FAQ</Link>
          </Button>
          <Button asChild className="btn-brand">
            <Link to="/contact">Contact security team</Link>
          </Button>
        </div>
      </div>
    </div>
  )
}
