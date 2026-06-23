import { cn } from "@/lib/utils"

interface ConfidenceBarProps {
  similarity: number
  threshold: number
  confidence: number
  matched: boolean
  className?: string
}

/**
 * Visualises a cosine-similarity score relative to the threshold. The bar
 * fills 0..1 to map similarity, with a vertical marker showing the decision
 * threshold (0.40 by default).
 */
export function ConfidenceBar({
  similarity,
  threshold,
  confidence,
  matched,
  className,
}: ConfidenceBarProps) {
  const simPct = Math.max(0, Math.min(100, similarity * 100))
  const thrPct = Math.max(0, Math.min(100, threshold * 100))

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex justify-between text-xs font-mono text-[var(--muted-foreground)]">
        <span>similarity</span>
        <span>
          <span
            className={cn(
              "font-semibold",
              matched
                ? "text-[var(--success)]"
                : "text-[var(--destructive)]",
            )}
          >
            {similarity.toFixed(4)}
          </span>{" "}
          / threshold {threshold.toFixed(3)}
        </span>
      </div>

      <div className="relative h-3 w-full overflow-hidden rounded-full bg-[var(--secondary)]">
        <div
          className={cn(
            "h-full transition-all duration-500 ease-out",
            matched
              ? "bg-[var(--success)]"
              : similarity > 0
                ? "bg-[var(--warning)]"
                : "bg-[var(--destructive)]",
          )}
          style={{ width: `${simPct}%` }}
        />
        <div
          className="absolute inset-y-0 w-px bg-[var(--foreground)]/40"
          style={{ left: `${thrPct}%` }}
          aria-hidden
        />
      </div>

      <div className="flex justify-between text-xs">
        <span
          className={cn(
            "font-medium",
            matched
              ? "text-[var(--success)]"
              : "text-[var(--destructive)]",
          )}
        >
          {matched ? "ACCEPT" : "REJECT"}
        </span>
        <span className="font-mono text-[var(--muted-foreground)]">
          confidence {confidence.toFixed(1)}%
        </span>
      </div>
    </div>
  )
}
