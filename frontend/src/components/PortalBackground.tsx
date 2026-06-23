import { useMemo } from "react"

import { cn } from "@/lib/utils"

type Star = {
  id: number
  x: number
  y: number
  size: number
  delay: number
  duration: number
  shine: boolean
}

function mulberry32(seed: number) {
  let a = seed
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function buildStars(seed: number, count: number): Star[] {
  const rng = mulberry32(seed)
  return Array.from({ length: count }, (_, id) => ({
    id,
    x: rng() * 100,
    y: rng() * 100,
    size: rng() > 0.88 ? 3 : rng() > 0.55 ? 2 : 1,
    delay: rng() * 6,
    duration: 2.2 + rng() * 3.8,
    shine: rng() > 0.8,
  }))
}

/** Ambient mesh + twinkling stars — light stars on dark, dark stars on light. */
export function PortalBackground({ variant = "dark" }: { variant: "light" | "dark" }) {
  const stars = useMemo(
    () => buildStars(variant === "light" ? 42 : 137, variant === "light" ? 90 : 110),
    [variant],
  )

  return (
    <div
      className={cn(
        "portal-bg pointer-events-none fixed inset-0 z-0 overflow-hidden",
        variant === "light" ? "portal-bg-light" : "portal-bg-dark",
      )}
      aria-hidden
    >
      <div className="portal-bg-mesh portal-bg-mesh-a" />
      <div className="portal-bg-mesh portal-bg-mesh-b" />
      <div className="portal-bg-mesh portal-bg-mesh-c" />
      {stars.map((star) => (
        <span
          key={star.id}
          className={cn("portal-star", star.shine && "portal-star-shine")}
          style={{
            left: `${star.x}%`,
            top: `${star.y}%`,
            width: star.size,
            height: star.size,
            animationDelay: `${star.delay}s`,
            animationDuration: `${star.duration}s`,
          }}
        />
      ))}
    </div>
  )
}
