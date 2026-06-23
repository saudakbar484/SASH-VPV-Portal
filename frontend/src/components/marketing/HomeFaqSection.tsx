import { useState } from "react"

import { Link } from "react-router-dom"

import { ChevronDown, HelpCircle } from "lucide-react"

import { MARKETING_FAQ } from "@/components/marketing/marketingFaq"
import { useRevealOnScroll } from "@/hooks/useRevealOnScroll"
import { cn } from "@/lib/utils"

export function HomeFaqSection() {
  const [open, setOpen] = useState<string | null>(null)
  const { ref, visible } = useRevealOnScroll<HTMLDivElement>()

  return (
    <section id="faq" className="border-t border-[var(--border)] bg-[color-mix(in_srgb,var(--accent)_35%,transparent)]">
      <div
        ref={ref}
        className={cn("marketing-reveal mx-auto max-w-4xl px-6 py-16", visible && "is-visible")}
      >
        <div className="text-center">
          <div className="marketing-icon-ring mx-auto mb-4">
            <HelpCircle className="size-6 text-[var(--primary)]" />
          </div>
          <h2 className="text-2xl font-bold sm:text-3xl">Frequently asked questions</h2>
          <p className="mx-auto mt-3 max-w-lg text-sm text-[var(--muted-foreground)]">
            Quick answers about registration, privacy, and hardware setup.
          </p>
        </div>

        <div className="mt-10 space-y-8">
          {MARKETING_FAQ.map((section) => (
            <div key={section.cat}>
              <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--primary)]">
                {section.cat}
              </h3>
              <div className="mt-3 space-y-2">
                {section.items.map((item) => {
                  const id = `${section.cat}-${item.q}`
                  const isOpen = open === id
                  return (
                    <div
                      key={id}
                      className="customer-card overflow-hidden transition-all duration-200 hover:shadow-md"
                    >
                      <button
                        type="button"
                        className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left text-sm font-medium"
                        onClick={() => setOpen(isOpen ? null : id)}
                        aria-expanded={isOpen}
                      >
                        {item.q}
                        <ChevronDown
                          className={cn(
                            "size-4 shrink-0 text-[var(--primary)] transition-transform duration-200",
                            isOpen && "rotate-180",
                          )}
                        />
                      </button>
                      {isOpen && (
                        <p className="border-t border-[var(--border)] px-5 py-4 text-sm leading-relaxed text-[var(--muted-foreground)]">
                          {item.a}
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        <p className="mt-10 text-center text-sm text-[var(--muted-foreground)]">
          Still need help?{" "}
          <Link to="/contact" className="font-semibold text-[var(--primary)] hover:underline">
            Contact our team
          </Link>
        </p>
      </div>
    </section>
  )
}
