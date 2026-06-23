import { cn } from "@/lib/utils"

const LOGO_SRC = "/palm-vein-logo.png"

export type PalmVeinLogoVariant = "full" | "header"

interface PalmVeinLogoProps {
  className?: string
  /** Icon size in px (preferred). */
  size?: number
  /** Legacy — treated as icon size when set. */
  height?: number
  variant?: PalmVeinLogoVariant
  /** Portal label below wordmark (Admin Console, Workplace, Employee). */
  subtitle?: string
  /** Show PALM VEIN wordmark beside / below the icon. */
  showText?: boolean
}

function LogoMark({ size }: { size: number }) {
  return (
    <img
      src={LOGO_SRC}
      alt=""
      width={size}
      height={size}
      className="shrink-0 object-contain drop-shadow-[0_0_14px_rgba(56,189,248,0.45)]"
      style={{ width: size, height: size }}
      draggable={false}
      aria-hidden
    />
  )
}

function LogoWordmark({
  subtitle,
  compact,
}: {
  subtitle?: string
  compact?: boolean
}) {
  return (
    <div className={cn("leading-tight", compact ? "min-w-0" : "text-center")}>
      <div
        className={cn(
          "font-bold tracking-[0.14em] text-[var(--foreground)]",
          compact ? "text-sm" : "text-base sm:text-lg",
        )}
      >
        SASH-VPV
      </div>
      {!compact && (
        <div className="text-[10px] font-medium uppercase tracking-[0.22em] text-[var(--muted-foreground)]">
          Portal
        </div>
      )}
      {subtitle ? (
        <div className="mt-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--primary)]">
          {subtitle}
        </div>
      ) : null}
    </div>
  )
}

/** SASH-VPV Portal brand — transparent icon mark + wordmark. */
export function PalmVeinLogo({
  className,
  size,
  height,
  variant = "full",
  subtitle,
  showText = true,
}: PalmVeinLogoProps) {
  const isHeader = variant === "header"
  const iconSize = size ?? height ?? (isHeader ? 36 : 72)

  if (isHeader) {
    return (
      <div className={cn("palm-vein-logo flex items-center gap-2.5", className)}>
        <LogoMark size={iconSize} />
        {showText ? (
          <LogoWordmark subtitle={subtitle ?? "Admin Console"} compact />
        ) : subtitle ? (
          <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--primary)]">
            {subtitle}
          </span>
        ) : null}
      </div>
    )
  }

  return (
    <div className={cn("palm-vein-logo flex flex-col items-center gap-3", className)}>
      <LogoMark size={iconSize} />
      {showText ? <LogoWordmark subtitle={subtitle} /> : null}
      {!showText && subtitle ? (
        <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--primary)]">
          {subtitle}
        </span>
      ) : null}
    </div>
  )
}

export { LOGO_SRC as PALM_VEIN_LOGO_SRC }
