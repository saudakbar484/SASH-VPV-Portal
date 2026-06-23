import { useQuery } from "@tanstack/react-query"
import { CircleCheck, CircleX, Loader2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { endpoints } from "@/lib/api"

/**
 * Compact connection + FPS badge for the top bar; polls every 2s.
 */
export function DeviceStatusBadge() {
  const status = useQuery({
    queryKey: ["device-status"],
    queryFn: endpoints.device.status,
    refetchInterval: 2000,
  })
  const stream = useQuery({
    queryKey: ["stream-status"],
    queryFn: endpoints.device.streamStatus,
    refetchInterval: 2000,
  })

  if (status.isPending) {
    return (
      <Badge variant="secondary">
        <Loader2 className="size-3 animate-spin" /> connecting
      </Badge>
    )
  }

  const connected = !!status.data?.connected
  const fps = stream.data?.fps ?? 0

  return (
    <div className="flex items-center gap-2">
      <Badge variant={connected ? "success" : "destructive"}>
        {connected ? (
          <CircleCheck className="size-3" />
        ) : (
          <CircleX className="size-3" />
        )}
        {connected ? "Sensor connected" : "Sensor offline"}
      </Badge>
      {connected && fps > 0 && (
        <Badge variant="outline" className="font-mono">
          {fps.toFixed(1)} fps
        </Badge>
      )}
    </div>
  )
}
