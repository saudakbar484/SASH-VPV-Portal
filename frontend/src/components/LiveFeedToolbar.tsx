import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { endpoints } from "@/lib/api"
import { useAppStore } from "@/store/useAppStore"

interface LiveFeedToolbarProps {
  className?: string
  showLiveBadge?: boolean
  showDistance?: boolean
}

export function LiveFeedToolbar({
  className,
  showLiveBadge = true,
  showDistance = false,
}: LiveFeedToolbarProps) {
  const queryClient = useQueryClient()
  const bumpStreamKey = useAppStore((s) => s.bumpStreamKey)

  const palmDist = useQuery({
    queryKey: ["palm-distance"],
    queryFn: endpoints.hardware.palmDistance,
    refetchInterval: showDistance ? 800 : false,
    enabled: showDistance,
  })

  const reconnect = useMutation({
    mutationFn: endpoints.device.reconnect,
    onSuccess: () => {
      bumpStreamKey()
      queryClient.invalidateQueries({ queryKey: ["device-status"] })
    },
  })

  return (
    <div className={cn("mb-3 flex items-center justify-between gap-2", className)}>
      <div className="min-w-0">
        <p className="text-xs uppercase tracking-wider text-brand-muted">Live scanner feed</p>
        {showDistance && palmDist.data && (
          <p
            className={cn(
              "mt-0.5 text-[10px] font-mono",
              palmDist.data.in_range ? "text-emerald-500" : "text-amber-600",
            )}
          >
            {palmDist.data.distance_mm != null
              ? `${palmDist.data.distance_mm} mm${palmDist.data.in_range ? " · in range" : " · move palm closer (3–8 cm)"}`
              : "Place palm 3–8 cm above sensor"}
          </p>
        )}
      </div>
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          className="h-8 border-[var(--input-border)] bg-[color-mix(in_srgb,var(--input-background)_90%,transparent)]"
          onClick={() => reconnect.mutate()}
          disabled={reconnect.isPending}
        >
          <RefreshCw className={cn("size-3.5", reconnect.isPending && "animate-spin")} />
          Reconnect
        </Button>
        {showLiveBadge && (
          <span className="inline-flex items-center rounded-full bg-emerald-500/20 px-2.5 py-1 text-[10px] font-semibold text-emerald-400 ring-1 ring-emerald-500/40">
            ● LIVE
          </span>
        )}
      </div>
    </div>
  )
}
