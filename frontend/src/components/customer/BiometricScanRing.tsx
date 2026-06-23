export function BiometricScanRing({
  progress = 0,
  size = 160,
  label,
}: {
  progress?: number
  size?: number
  label?: string
}) {
  const r = (size - 12) / 2
  const c = 2 * Math.PI * r
  const offset = c - (progress / 100) * c

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="scan-ring -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="color-mix(in srgb, var(--primary) 15%, transparent)"
          strokeWidth={6}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--primary)"
          strokeWidth={6}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          className="transition-all duration-500"
        />
      </svg>
      <div className="absolute text-center">
        <div className="text-2xl font-bold tabular-nums text-[var(--primary)]">{Math.round(progress)}%</div>
        {label && (
          <div className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted-foreground)]">
            {label}
          </div>
        )}
      </div>
    </div>
  )
}
