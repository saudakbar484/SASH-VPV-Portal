import * as React from "react"
import { cn } from "@/lib/utils"

interface SliderProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  value: number
  min?: number
  max?: number
  step?: number
  onValueChange: (v: number) => void
  className?: string
}

/**
 * Minimal slider using a styled native range input. Avoids the Radix
 * dependency while keeping shadcn-style focus + filled-track aesthetics.
 */
export function Slider({
  value,
  min = 0,
  max = 100,
  step = 1,
  onValueChange,
  className,
  ...props
}: SliderProps) {
  const pct = ((value - min) / (max - min)) * 100
  return (
    <div className={cn("relative flex w-full items-center", className)}>
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onValueChange(Number(e.target.value))}
        className="h-1.5 w-full cursor-pointer appearance-none rounded-full outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 [&::-webkit-slider-thumb]:size-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-[var(--primary)] [&::-webkit-slider-thumb]:bg-[var(--background)]"
        style={{
          background: `linear-gradient(to right, var(--primary) 0%, var(--primary) ${pct}%, var(--secondary) ${pct}%, var(--secondary) 100%)`,
          backgroundClip: "padding-box",
          height: 6,
          borderRadius: 999,
        }}
        {...props}
      />
    </div>
  )
}
