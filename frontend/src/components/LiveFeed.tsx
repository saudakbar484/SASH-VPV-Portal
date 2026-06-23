import { useEffect, useRef, useState } from "react"

import { Loader2 } from "lucide-react"

import { useQuery } from "@tanstack/react-query"

import { SCANNER_SIZE_CLASS, type ScannerSize } from "@/components/ScannerViewport"
import { cn } from "@/lib/utils"

import { endpoints } from "@/lib/api"

import { useAppStore } from "@/store/useAppStore"

interface LiveFeedProps {
  className?: string
  /** Preset scanner frame size — use compact in side-by-side recognition/enrollment panels. */
  size?: ScannerSize
  /** Fill parent container (e.g. auth-scan-viewport) instead of fixed preset size. */
  fill?: boolean
}

const LOAD_TIMEOUT_MS = 12_000
const STALE_FRAME_S = 8

/**
 * MJPEG live feed from the sensor. The `streamKey` from the Zustand store
 * is appended as a cache-busting query param so calling reconnect from
 * anywhere in the app forces the browser to drop the stale connection and
 * re-open a fresh one.
 */
export function LiveFeed({ className, size = "compact", fill = false }: LiveFeedProps) {
  const streamKey = useAppStore((s) => s.streamKey)
  const bumpStreamKey = useAppStore((s) => s.bumpStreamKey)
  const [loaded, setLoaded] = useState(false)
  const [errored, setErrored] = useState(false)
  const [stalled, setStalled] = useState(false)
  const autoReconnectAttempted = useRef(false)
  const imgRef = useRef<HTMLImageElement>(null)

  const { data: streamStatus } = useQuery({
    queryKey: ["stream-status", streamKey],
    queryFn: endpoints.device.streamStatus,
    refetchInterval: 3000,
    retry: false,
  })

  useEffect(() => {
    setLoaded(false)
    setErrored(false)
    setStalled(false)
    autoReconnectAttempted.current = false
  }, [streamKey])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (!loaded && !errored) {
        setErrored(true)
        setStalled(true)
      }
    }, LOAD_TIMEOUT_MS)
    return () => window.clearTimeout(timer)
  }, [streamKey, loaded, errored])

  useEffect(() => {
    const age = streamStatus?.last_frame_age_seconds
    if (age == null || age < STALE_FRAME_S) {
      return
    }
    setStalled(true)
    if (autoReconnectAttempted.current) {
      return
    }
    autoReconnectAttempted.current = true
    endpoints.device
      .reconnect()
      .then(() => bumpStreamKey())
      .catch(() => {
        setErrored(true)
      })
  }, [streamStatus?.last_frame_age_seconds, bumpStreamKey])

  const showSpinner = !loaded && !errored

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-lg border border-[var(--border)] bg-black",
        fill ? "h-full w-full" : cn("mx-auto", SCANNER_SIZE_CLASS[size]),
        className,
      )}
    >
      {showSpinner && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-white/70">
          <Loader2 className="size-6 animate-spin" />
          <span className="text-xs text-white/50">Connecting to scanner…</span>
        </div>
      )}
      {errored && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-4 text-center text-white/80">
          <span className="text-sm font-medium">
            {stalled ? "Scanner feed stalled" : "Stream unavailable"}
          </span>
          <span className="text-xs text-white/60">
            Check the sensor connection, then click Reconnect above.
          </span>
        </div>
      )}
      <img
        ref={imgRef}
        key={streamKey}
        src={`/api/stream?t=${streamKey}`}
        alt="Live palm-vein stream"
        onLoad={() => {
          setLoaded(true)
          setErrored(false)
          setStalled(false)
        }}
        onError={() => {
          setErrored(true)
          setStalled(true)
        }}
        className={cn(
          "h-full w-full object-contain transition-opacity duration-300",
          loaded ? "opacity-100" : "opacity-0",
        )}
      />
      {loaded && !stalled && (
        <div className="pointer-events-none absolute bottom-2 left-2 rounded-md bg-black/60 px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-white/80">
          live
        </div>
      )}
    </div>
  )
}
