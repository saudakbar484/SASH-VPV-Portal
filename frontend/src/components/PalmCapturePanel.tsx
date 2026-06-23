import { useCallback, useEffect, useRef, useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { Camera, CheckCircle2, Loader2, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { LiveFeed } from "@/components/LiveFeed"
import { LiveFeedToolbar } from "@/components/LiveFeedToolbar"
import { SCANNER_PANEL_CONTENT_STANDARD_CLASS } from "@/components/ScannerViewport"
import { endpoints, type RegisterSessionStatus } from "@/lib/api"
import { cn } from "@/lib/utils"

type Hand = "Left" | "Right"

export type PalmSessionStatus = RegisterSessionStatus & {
  last_error?: string | null
}

interface PalmCapturePanelProps {
  registerSessionId: string
  sessionStatus: PalmSessionStatus
  onStatusChange: (status: PalmSessionStatus) => void
  onSwitchHand: (hand: Hand) => void
  switchHandPending?: boolean
  perHand?: number
  /** Minimum ms between successful captures (avoids duplicate SDK frames). */
  cooldownMs?: number
}

interface LastCapture {
  hand: Hand
  index: number
  imageUrl: string
  message: string
  embeddingNorm?: number
}

export function PalmCapturePanel({
  registerSessionId,
  sessionStatus,
  onStatusChange,
  onSwitchHand,
  switchHandPending,
  perHand = 10,
  cooldownMs = 1000,
}: PalmCapturePanelProps) {
  const [lastCapture, setLastCapture] = useState<LastCapture | null>(null)
  const [cooldownLeft, setCooldownLeft] = useState(0)
  const lastSuccessAt = useRef(0)

  const currentHand = sessionStatus.current_hand as Hand
  const leftCount = sessionStatus.left_captured
  const rightCount = sessionStatus.right_captured
  const currentCount = currentHand === "Left" ? leftCount : rightCount
  const handDone = currentCount >= perHand
  const otherHand: Hand = currentHand === "Left" ? "Right" : "Left"
  const otherDone =
    otherHand === "Left" ? leftCount >= perHand : rightCount >= perHand

  const capture = useMutation({
    mutationFn: () => endpoints.auth.registerPalmCapture(registerSessionId),
    onSuccess: (data) => {
      onStatusChange(data)
      if (data.captured && data.last_capture_index && data.last_capture_hand) {
        lastSuccessAt.current = Date.now()
        setCooldownLeft(cooldownMs)
        setLastCapture({
          hand: data.last_capture_hand as Hand,
          index: data.last_capture_index,
          imageUrl: `${data.last_image_url}&t=${Date.now()}`,
          message: data.message ?? "Capture saved and processed",
          embeddingNorm: data.embedding_norm ?? undefined,
        })
      }
    },
  })

  // Cooldown timer after each successful capture.
  useEffect(() => {
    if (cooldownLeft <= 0) return
    const t = window.setInterval(() => {
      const remain = cooldownMs - (Date.now() - lastSuccessAt.current)
      setCooldownLeft(Math.max(0, remain))
    }, 100)
    return () => window.clearInterval(t)
  }, [cooldownLeft, cooldownMs])

  const canCapture =
    !capture.isPending &&
    !handDone &&
    cooldownLeft <= 0

  const handleCapture = useCallback(() => {
    if (!canCapture) return
    capture.mutate()
  }, [canCapture, capture])

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Live scanner feed */}
        <div className="space-y-2">
          <div className={cn("flex flex-col", SCANNER_PANEL_CONTENT_STANDARD_CLASS)}>
            <LiveFeedToolbar className="mb-1 shrink-0" />
            <div className="relative min-h-0 flex-1">
              <LiveFeed fill />
            </div>
          </div>
          <p className="text-center text-xs text-[var(--muted-foreground)]">
            Position palm 3–8 cm above the sensor, then press Capture.
          </p>
        </div>

        {/* Last saved + processed capture */}
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-wider text-brand-muted">Last capture</p>
          <div
            className={cn(
              "flex flex-col items-center justify-center rounded-xl border border-white/10 bg-black/40 p-3",
              SCANNER_PANEL_CONTENT_STANDARD_CLASS,
            )}
          >
            {lastCapture ? (
              <>
                <img
                  src={lastCapture.imageUrl}
                  alt={`${lastCapture.hand} capture ${lastCapture.index}`}
                  className="max-h-[200px] max-w-full rounded-lg object-contain ring-1 ring-emerald-500/40"
                />
                <div className="mt-3 flex items-center gap-2 text-xs text-emerald-400">
                  <CheckCircle2 className="size-4 shrink-0" />
                  <span className="text-left">{lastCapture.message}</span>
                </div>
              </>
            ) : (
              <p className="text-center text-sm text-[var(--muted-foreground)]">
                No captures yet. Each press saves a PNG and runs the ArcFace embedding pipeline.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Progress */}
      <div className="rounded-lg border border-white/10 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span className="font-medium">
            {currentHand} hand — {currentCount} / {perHand}
          </span>
          <span className="text-[var(--muted-foreground)]">
            Left {leftCount}/{perHand} · Right {rightCount}/{perHand}
          </span>
        </div>
        <Progress value={currentCount} max={perHand} className="mt-2" />
        <CaptureDots
          count={currentCount}
          total={perHand}
          className="mt-3"
        />
        <p className="mt-2 text-xs text-[var(--muted-foreground)]">
          Lift and replace your palm between captures. Wait ~1 s after each success.
        </p>
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button
          className="flex-1 btn-brand "
          size="lg"
          disabled={!canCapture}
          onClick={handleCapture}
        >
          {capture.isPending ? (
            <>
              <Loader2 className="size-5 animate-spin" />
              Processing…
            </>
          ) : cooldownLeft > 0 ? (
            <>
              <RefreshCw className="size-5" />
              Reposition palm ({Math.ceil(cooldownLeft / 1000)}s)
            </>
          ) : (
            <>
              <Camera className="size-5" />
              Capture & Process
            </>
          )}
        </Button>

        {handDone && !otherDone && (
          <Button
            variant="outline"
            size="lg"
            className="border-[var(--primary)]/40"
            onClick={() => onSwitchHand(otherHand)}
            disabled={switchHandPending}
          >
            Continue with {otherHand} hand
          </Button>
        )}
      </div>

      {(sessionStatus.last_error || capture.data?.reason) && !capture.data?.captured && (
        <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-300">
          {sessionStatus.last_error ?? capture.data?.reason}
        </p>
      )}

      {capture.isError && (
        <p className="text-sm text-red-400">Capture request failed — try again.</p>
      )}
    </div>
  )
}

function CaptureDots({
  count,
  total,
  className,
}: {
  count: number
  total: number
  className?: string
}) {
  return (
    <div className={cn("flex flex-wrap gap-1.5", className)}>
      {Array.from({ length: total }, (_, i) => (
        <div
          key={i}
          className={cn(
            "size-2.5 rounded-full transition-colors",
            i < count ? "bg-emerald-400 shadow-[0_0_6px] shadow-emerald-400/50" : "bg-white/15",
          )}
          title={i < count ? `Capture ${i + 1} saved` : `Slot ${i + 1}`}
        />
      ))}
    </div>
  )
}
