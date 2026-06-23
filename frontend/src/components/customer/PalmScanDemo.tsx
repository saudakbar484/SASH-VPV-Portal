import { cn } from "@/lib/utils"

const PALM_HAND_SRC = "/palm-scan-hand.png"

/** Hero demo: floating palm with a vertical scanner sweep. */
export function PalmScanDemo({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "relative mx-auto w-full max-w-[320px] sm:max-w-[360px] lg:max-w-[400px]",
        className,
      )}
    >
      <div className="relative">
        <img
          src={PALM_HAND_SRC}
          alt="Palm vein scan demonstration"
          className="h-auto w-full"
          draggable={false}
        />

        <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
          <div className="palm-scan-line absolute left-[18%] right-[18%] h-px bg-white/80" />
        </div>
      </div>
    </div>
  )
}
