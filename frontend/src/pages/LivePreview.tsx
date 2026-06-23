import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  Camera,
  CircleCheck,
  CircleX,
  Hand,
  RefreshCw,
  Ruler,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { LiveFeed } from "@/components/LiveFeed"
import { api, endpoints } from "@/lib/api"
import { useAppStore } from "@/store/useAppStore"
import { cn } from "@/lib/utils"

function StatRow({
  icon: Icon,
  label,
  value,
  tone = "default",
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: React.ReactNode
  tone?: "default" | "success" | "warn" | "muted"
}) {
  const toneClass =
    tone === "success"
      ? "text-[var(--success)]"
      : tone === "warn"
        ? "text-[var(--warning)]"
        : tone === "muted"
          ? "text-[var(--muted-foreground)]"
          : "text-[var(--foreground)]"
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <span className="flex items-center gap-2 text-sm text-[var(--muted-foreground)]">
        <Icon className="size-4" />
        {label}
      </span>
      <span className={cn("font-mono text-sm tabular-nums", toneClass)}>
        {value}
      </span>
    </div>
  )
}

export function LivePreview() {
  const queryClient = useQueryClient()
  const bumpStreamKey = useAppStore((s) => s.bumpStreamKey)

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
  const info = useQuery({
    queryKey: ["hardware-info"],
    queryFn: endpoints.hardware.info,
  })
  const publicStats = useQuery({
    queryKey: ["public-stats"],
    queryFn: endpoints.public.stats,
  })
  const palmDist = useQuery({
    queryKey: ["palm-distance"],
    queryFn: endpoints.hardware.palmDistance,
    refetchInterval: 800,
    enabled: !!status.data?.connected,
  })

  const reconnect = useMutation({
    mutationFn: endpoints.device.reconnect,
    onSuccess: () => {
      bumpStreamKey()
      queryClient.invalidateQueries({ queryKey: ["device-status"] })
      queryClient.invalidateQueries({ queryKey: ["stream-status"] })
      queryClient.invalidateQueries({ queryKey: ["hardware-info"] })
    },
  })

  const snapshot = useMutation({
    mutationFn: async () => (await api.post("/api/capture")).data,
  })

  const connected = !!status.data?.connected
  const fps = stream.data?.fps ?? 0
  const ageS = stream.data?.last_frame_age_seconds

  return (
    <div className="grid h-full grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
      {/* Left column: big live preview */}
      <Card className="flex h-fit flex-col">
        <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0">
          <div>
            <CardTitle>Live preview</CardTitle>
            <CardDescription>
              Raw NIR + vein-mask feed from the XRTECH MagicVein Plus
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => snapshot.mutate()}
              disabled={!connected || snapshot.isPending}
            >
              <Camera className="size-4" />
              {snapshot.isPending ? "Saving..." : "Snapshot"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => reconnect.mutate()}
              disabled={reconnect.isPending}
            >
              <RefreshCw
                className={cn("size-4", reconnect.isPending && "animate-spin")}
              />
              Reconnect
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <LiveFeed size="large" />
          {snapshot.data && (
            <div className="mt-3 rounded-md border border-[var(--border)] bg-[var(--muted)] px-3 py-2 font-mono text-xs">
              Snapshot saved: {snapshot.data.filename}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Right column: stats */}
      <div className="space-y-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Sensor status</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <StatRow
              icon={connected ? CircleCheck : CircleX}
              label="Connection"
              value={connected ? "connected" : "offline"}
              tone={connected ? "success" : "warn"}
            />
            <StatRow
              icon={Ruler}
              label="Palm distance"
              value={
                palmDist.data?.distance_mm != null
                  ? `${palmDist.data.distance_mm} mm`
                  : "—"
              }
              tone={palmDist.data?.in_range ? "success" : "muted"}
            />
            <StatRow
              icon={Hand}
              label="Stream"
              value={connected && fps > 0 ? `${fps.toFixed(1)} fps` : "idle"}
              tone={fps > 0 ? "default" : "muted"}
            />
            <StatRow
              icon={RefreshCw}
              label="Last frame"
              value={
                ageS != null ? `${ageS.toFixed(1)} s ago` : "—"
              }
              tone="muted"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Hardware</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 pt-0 text-sm">
            {info.isPending && (
              <p className="text-[var(--muted-foreground)]">Loading...</p>
            )}
            {info.data && (
              <dl className="grid grid-cols-[80px_minmax(0,1fr)] gap-x-2 gap-y-1 font-mono text-xs">
                <dt className="text-[var(--muted-foreground)]">Serial</dt>
                <dd className="truncate" title={info.data.serial ?? undefined}>
                  {info.data.serial ?? "—"}
                </dd>
                <dt className="text-[var(--muted-foreground)]">Firmware</dt>
                <dd className="truncate" title={info.data.fw_version ?? undefined}>
                  {info.data.fw_version ?? "—"}
                </dd>
                <dt className="text-[var(--muted-foreground)]">SDK</dt>
                <dd className="truncate" title={info.data.sdk_version ?? undefined}>
                  {info.data.sdk_version ?? "—"}
                </dd>
              </dl>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Model</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 pt-0 text-xs text-[var(--muted-foreground)]">
            <p>EfficientNet-B0 + CBAM, ArcFace-trained head</p>
            <p>512-d L2-normalised embeddings · cosine similarity</p>
            <p>
              Production match threshold:{" "}
              <span className="font-mono text-[var(--foreground)]">
                {publicStats.data?.match_threshold.toFixed(3) ?? "0.400"}
              </span>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
