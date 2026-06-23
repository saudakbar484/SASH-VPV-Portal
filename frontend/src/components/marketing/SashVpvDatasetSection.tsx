import { ArrowRight, Database, ExternalLink, ScanLine, Waves } from "lucide-react"

import { Button } from "@/components/ui/button"
import { SASH_VPV_DATASET, SASH_VPV_KAGGLE_URL } from "@/lib/sashVpvDataset"
import { cn } from "@/lib/utils"

type SashVpvDatasetSectionProps = {
  className?: string
}

export function SashVpvDatasetSection({ className }: SashVpvDatasetSectionProps) {
  const { local } = SASH_VPV_DATASET

  const stats = [
    { label: "Subjects", value: local.subjects },
    { label: "Images (full corpus)", value: local.images.toLocaleString() },
    { label: "Hand classes", value: local.handClasses },
    { label: "Avg / hand", value: `~${local.imagesPerHand.average}` },
  ]

  const specs = [
    { icon: ScanLine, label: "Sensor", value: local.sensor },
    { icon: Waves, label: "Illumination", value: local.wavelength },
    { icon: Database, label: "Resolution", value: `${local.resolution} PNG` },
  ]

  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-2xl border border-[color-mix(in_srgb,var(--primary)_25%,transparent)]",
        "bg-[color-mix(in_srgb,var(--primary)_8%,var(--card))] px-6 py-10 sm:px-10 sm:py-12",
        className,
      )}
      aria-labelledby="sash-vpv-heading"
    >
      <div className="marketing-hero-glow absolute -right-16 top-0 size-56 opacity-60" aria-hidden />
      <div className="relative grid gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--primary)]">
            Major research contribution
          </p>
          <h2 id="sash-vpv-heading" className="mt-2 text-2xl font-bold sm:text-3xl">
            {SASH_VPV_DATASET.acronym}: {SASH_VPV_DATASET.subtitle}
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-[var(--muted-foreground)] sm:text-base">
            {SASH_VPV_DATASET.title} — a custom near-infrared palm vein dataset collected at{" "}
            <strong className="font-medium text-[var(--foreground)]">NUTECH, Islamabad</strong> for
            contactless biometric verification, ROI extraction, and deep metric-learning pipelines.
            This corpus powers the neural matcher deployed in this system.
          </p>
          <p className="mt-3 text-sm leading-relaxed text-[var(--muted-foreground)]">
            {SASH_VPV_DATASET.kaggleNote}
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <Button asChild size="lg" className="btn-brand group">
              <a href={SASH_VPV_KAGGLE_URL} target="_blank" rel="noopener noreferrer">
                View on Kaggle
                <ExternalLink className="ml-1.5 size-4" />
              </a>
            </Button>
            <Button asChild size="lg" variant="outline" className="backdrop-blur-sm">
              <a href={SASH_VPV_KAGGLE_URL} target="_blank" rel="noopener noreferrer">
                Download public release
                <ArrowRight className="ml-1 size-4" />
              </a>
            </Button>
          </div>

          <p className="mt-4 text-xs text-[var(--muted-foreground)]">
            Published by {SASH_VPV_DATASET.publisher} · {SASH_VPV_DATASET.license}
          </p>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            {stats.map((s) => (
              <div key={s.label} className="customer-card marketing-stat-card p-4 text-center">
                <div className="text-2xl font-bold tabular-nums text-[var(--primary)]">{s.value}</div>
                <div className="mt-1 text-[10px] font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  {s.label}
                </div>
              </div>
            ))}
          </div>

          <div className="customer-card space-y-3 p-4">
            {specs.map(({ icon: Icon, label, value }) => (
              <div key={label} className="flex items-center gap-3 text-sm">
                <div className="marketing-icon-ring flex size-9 shrink-0 items-center justify-center">
                  <Icon className="size-4 text-[var(--primary)]" />
                </div>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
                    {label}
                  </p>
                  <p className="font-medium">{value}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
