import { Link } from "react-router-dom"

import { Cpu, ArrowRight } from "lucide-react"

import { MarketingPageHero } from "@/components/marketing/MarketingPageHero"
import { Button } from "@/components/ui/button"
import { useRevealOnScroll } from "@/hooks/useRevealOnScroll"
import { cn } from "@/lib/utils"

const STACK = [
  { layer: "Capture", detail: "480×640 grayscale NIR frames from XRTECH vein sensor" },
  { layer: "Preprocess", detail: "Landmark detection, ROI crop, Frangi/Gabor vein enhancement" },
  { layer: "Encoder", detail: "EfficientNet-B0 backbone with CBAM attention modules" },
  { layer: "Metric learning", detail: "ArcFace-trained 512-d L2-normalised embeddings" },
  { layer: "Matcher", detail: "Cosine similarity with calibrated threshold + margin checks" },
]

export function TechnologyPage() {
  const { ref, visible } = useRevealOnScroll<HTMLDivElement>()

  return (
    <div>
      <MarketingPageHero
        icon={Cpu}
        eyebrow="Architecture"
        title="Technology stack"
        description="A production pipeline from near-infrared optics to neural vein embeddings — built for accuracy, auditability, and sub-second decisions."
      />

      <div className="mx-auto max-w-4xl px-6 py-12">
        <div
          ref={ref}
          className={cn("marketing-reveal space-y-3", visible && "is-visible")}
        >
          {STACK.map((row, i) => (
            <div
              key={row.layer}
              className="marketing-feature-card flex gap-4 p-5"
              style={{ transitionDelay: `${i * 50}ms` }}
            >
              <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-[var(--primary)] text-xs font-bold text-white">
                {i + 1}
              </span>
              <div>
                <h3 className="font-semibold">{row.layer}</h3>
                <p className="mt-1 text-sm text-[var(--muted-foreground)]">{row.detail}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="customer-card mt-8 overflow-x-auto p-6">
          <h2 className="mb-4 font-semibold">Biometric comparison</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-xs uppercase text-[var(--muted-foreground)]">
                <th className="pb-2">Method</th>
                <th className="pb-2">Spoof risk</th>
                <th className="pb-2">Contact</th>
                <th className="pb-2">Template</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["Palm vein (NIR)", "Very low", "Contactless", "512-d embedding"],
                ["Fingerprint", "Medium", "Contact", "Minutiae map"],
                ["Face (2D)", "Higher", "Contactless", "Photo-based"],
              ].map(([m, s, c, t]) => (
                <tr key={m} className="border-b border-[var(--border)]">
                  <td className="py-3 font-medium">{m}</td>
                  <td className="py-3">{s}</td>
                  <td className="py-3">{c}</td>
                  <td className="py-3 text-[var(--muted-foreground)]">{t}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <Button asChild className="btn-brand">
            <Link to="/how-it-works">
              See the user journey
              <ArrowRight className="ml-1 size-4" />
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/security">Security model</Link>
          </Button>
        </div>
      </div>
    </div>
  )
}
