import { useEffect, useState } from "react"

import { useMutation } from "@tanstack/react-query"

import { CheckCircle2, Loader2, XCircle } from "lucide-react"

import { BiometricScanRing } from "@/components/customer/BiometricScanRing"
import { HudPanel } from "@/components/customer/HudPanel"
import { ConfidenceBar } from "@/components/ConfidenceBar"
import { LiveFeed } from "@/components/LiveFeed"
import { LiveFeedToolbar } from "@/components/LiveFeedToolbar"
import { SCANNER_PANEL_CONTENT_CLASS } from "@/components/ScannerViewport"
import { Button } from "@/components/ui/button"
import { endpoints } from "@/lib/api"
import { cn } from "@/lib/utils"

const STEPS = ["Capturing palm frame…", "Extracting vein pattern…", "Matching your template…"]

/** Inline palm recognition panel for member signup and scan flows. */
export function PalmRecognitionPanel({ className }: { className?: string }) {
  const [stepIdx, setStepIdx] = useState(0)
  const [probeUrl, setProbeUrl] = useState<string | null>(null)
  const [verifyError, setVerifyError] = useState<string | null>(null)

  const parseApiError = (err: unknown, fallback: string) => {
    const ax = err as { response?: { data?: { detail?: unknown }; status?: number }; message?: string }
    const detail = ax?.response?.data?.detail
    if (typeof detail === "string") return detail
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string }
      if (typeof first?.msg === "string") return first.msg
    }
    if (ax?.response?.status === 401) return "Session expired or not signed in. Please sign in again."
    if (!ax?.response && ax?.message?.includes("Network")) return "Cannot reach server — is backend running?"
    return fallback
  }

  const verify = useMutation({
    mutationFn: endpoints.user.verifyPalm,
    onSuccess: (data) => {
      setVerifyError(null)
      if (data.probe_image_url) setProbeUrl(`${data.probe_image_url}&t=${Date.now()}`)
    },
    onError: (err) => {
      setVerifyError(parseApiError(err, "Palm verification failed"))
    },
  })

  useEffect(() => {
    if (!verify.isPending) {
      setStepIdx(0)
      return
    }
    setStepIdx(0)
    const timers = [
      window.setTimeout(() => setStepIdx(1), 800),
      window.setTimeout(() => setStepIdx(2), 1800),
    ]
    return () => timers.forEach(clearTimeout)
  }, [verify.isPending])

  const data = verify.data

  return (
    <div className={cn("grid gap-4 lg:grid-cols-2 lg:items-start", className)}>
      <HudPanel title="Recognition camera" className="flex flex-col">
        <div className={cn("flex flex-col", SCANNER_PANEL_CONTENT_CLASS)}>
          <LiveFeedToolbar className="mb-2 shrink-0" showDistance />
          <div className="relative min-h-0 flex-1">
            <LiveFeed fill />
          </div>
        </div>
        {probeUrl && (
          <img
            src={probeUrl}
            alt="Last probe"
            className="mx-auto mt-3 max-h-20 max-w-[186px] rounded border border-[var(--border)] object-contain"
          />
        )}
      </HudPanel>

      <div className="flex flex-col gap-4">
        <HudPanel title="Recognition result">
          <div
            className={cn(
              "flex flex-col items-center justify-center gap-2 text-center",
              SCANNER_PANEL_CONTENT_CLASS,
            )}
          >
            <BiometricScanRing
              progress={verify.isPending ? 45 + stepIdx * 20 : data?.matched ? 100 : 0}
              label="SCAN"
            />
            <p className="text-sm text-[var(--muted-foreground)]">
              {verify.isPending ? STEPS[stepIdx] : data?.message ?? "Place your palm and scan to verify"}
            </p>
            {data && (
              <div className="mt-2 w-full">
                <ConfidenceBar
                  similarity={data.similarity}
                  threshold={data.threshold}
                  confidence={data.similarity}
                  matched={data.matched}
                />
              </div>
            )}
          </div>
        </HudPanel>

        <Button
          className="btn-brand w-full"
          size="lg"
          disabled={verify.isPending}
          onClick={() => {
            setVerifyError(null)
            verify.mutate()
          }}
        >
          {verify.isPending ? <Loader2 className="animate-spin" /> : "Recognize your palm"}
        </Button>
        {verifyError && <p className="text-center text-sm text-red-500">{verifyError}</p>}

        {data?.matched && (
          <div className="flex items-center gap-2 text-emerald-500">
            <CheckCircle2 className="size-5" />
            Palm recognized — {data.hand} hand
          </div>
        )}
        {data && !data.matched && !verify.isPending && (
          <div className="flex items-center gap-2 text-red-500">
            <XCircle className="size-5 shrink-0" />
            <span className="text-sm">{data.message ?? "No match — adjust hand position and try again"}</span>
          </div>
        )}
      </div>
    </div>
  )
}
