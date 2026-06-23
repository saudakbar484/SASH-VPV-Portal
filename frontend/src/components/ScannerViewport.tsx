import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

/** Shared scanner preview dimensions — 3:4 portrait, compact for side-by-side panels. */
export const SCANNER_COMPACT_CLASS = "h-[248px] w-[186px] max-w-full shrink-0"

export const SCANNER_STANDARD_CLASS = "h-[280px] w-[210px] max-w-full shrink-0"

export const SCANNER_LARGE_CLASS =
  "aspect-[3/4] h-auto max-h-[360px] w-full max-w-[270px]"

export type ScannerSize = "compact" | "standard" | "large"

export const SCANNER_SIZE_CLASS: Record<ScannerSize, string> = {
  compact: SCANNER_COMPACT_CLASS,
  standard: SCANNER_STANDARD_CLASS,
  large: SCANNER_LARGE_CLASS,
}

/** Matched inner height for side-by-side scanner + result panels (below panel title). */
export const SCANNER_PANEL_CONTENT_CLASS = "h-[248px]"

export const SCANNER_PANEL_CONTENT_STANDARD_CLASS = "h-[280px]"

type ScannerViewportProps = {
  children: ReactNode
  size?: ScannerSize
  className?: string
  center?: boolean
}

/** Wraps LiveFeed (or probe image) in a consistent viewport size. */
export function ScannerViewport({
  children,
  size = "compact",
  className,
  center = true,
}: ScannerViewportProps) {
  return (
    <div className={cn(SCANNER_SIZE_CLASS[size], center && "mx-auto", className)}>
      {children}
    </div>
  )
}
