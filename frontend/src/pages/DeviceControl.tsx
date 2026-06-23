import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertCircle,
  Lightbulb,
  Moon,
  Sun,
  Volume2,
  VolumeX,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Slider } from "@/components/ui/slider"
import { endpoints } from "@/lib/api"
import { cn } from "@/lib/utils"

const PRESETS: { id: string; label: string; rgb: [number, number, number]; tone?: string }[] = [
  { id: "off", label: "Off", rgb: [0, 0, 0] },
  { id: "red", label: "Red", rgb: [1, 0, 0], tone: "bg-red-500" },
  { id: "green", label: "Green", rgb: [0, 1, 0], tone: "bg-green-500" },
  { id: "blue", label: "Blue", rgb: [0, 0, 1], tone: "bg-blue-500" },
  { id: "yellow", label: "Yellow", rgb: [1, 1, 0], tone: "bg-yellow-400" },
  { id: "magenta", label: "Magenta", rgb: [1, 0, 1], tone: "bg-fuchsia-500" },
  { id: "cyan", label: "Cyan", rgb: [0, 1, 1], tone: "bg-cyan-400" },
  { id: "white", label: "White", rgb: [1, 1, 1], tone: "bg-white border-2" },
]

export function DeviceControl() {
  const queryClient = useQueryClient()
  const [activePreset, setActivePreset] = useState<string | null>(null)
  const [r, setR] = useState(0)
  const [g, setG] = useState(0)
  const [b, setB] = useState(0)
  const [volume, setVolume] = useState(50)
  const [sleeping, setSleeping] = useState(false)

  const info = useQuery({
    queryKey: ["hardware-info"],
    queryFn: endpoints.hardware.info,
  })

  const setPreset = useMutation({
    mutationFn: (preset: string) => endpoints.hardware.setLedPreset(preset),
    onSuccess: (_d, preset) => {
      setActivePreset(preset)
      const p = PRESETS.find((p) => p.id === preset)
      if (p) {
        setR(p.rgb[0])
        setG(p.rgb[1])
        setB(p.rgb[2])
      }
    },
  })

  const setRgb = useMutation({
    mutationFn: (rgb: [number, number, number]) =>
      endpoints.hardware.setLed(rgb[0], rgb[1], rgb[2]),
    onSuccess: () => setActivePreset("custom"),
  })

  const setVol = useMutation({
    mutationFn: (level: number) => endpoints.hardware.setVolume(level),
  })

  const setSleep = useMutation({
    mutationFn: (enabled: boolean) => endpoints.hardware.setSleep(enabled),
    onSuccess: (_d, enabled) => {
      setSleeping(enabled)
      queryClient.invalidateQueries({ queryKey: ["device-status"] })
    },
  })

  const audioSupported = setVol.isError ? false : true

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Hardware</CardTitle>
          <CardDescription>
            Identifiers reported by the XRTECH SDK for the connected sensor.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {info.isPending && (
            <p className="text-sm text-[var(--muted-foreground)]">Loading...</p>
          )}
          {info.data && (
            <dl className="grid grid-cols-[100px_minmax(0,1fr)] gap-y-1 font-mono text-xs">
              <dt className="text-[var(--muted-foreground)]">Connected</dt>
              <dd>{String(info.data.connected)}</dd>
              <dt className="text-[var(--muted-foreground)]">Serial</dt>
              <dd>{info.data.serial ?? "—"}</dd>
              <dt className="text-[var(--muted-foreground)]">Firmware</dt>
              <dd>{info.data.fw_version ?? "—"}</dd>
              <dt className="text-[var(--muted-foreground)]">SDK</dt>
              <dd>{info.data.sdk_version ?? "—"}</dd>
            </dl>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lightbulb className="size-5" />
            Status LED
          </CardTitle>
          <CardDescription>
            The MagicVein Plus has an on-board tri-colour LED. Each channel is
            on/off in firmware so the SDK clamps any non-zero value to "lit".
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-4 gap-2">
            {PRESETS.map((p) => (
              <Button
                key={p.id}
                variant={activePreset === p.id ? "default" : "outline"}
                onClick={() => setPreset.mutate(p.id)}
                disabled={setPreset.isPending}
                className="flex h-16 flex-col gap-1"
              >
                <div
                  className={cn(
                    "size-4 rounded-full border border-[var(--border)]",
                    p.tone ?? "bg-[var(--muted)]",
                  )}
                />
                <span className="text-xs">{p.label}</span>
              </Button>
            ))}
          </div>

          <div className="space-y-2 rounded-md border border-[var(--border)] p-3">
            <div className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
              Custom RGB ({r ? "R" : ""}{g ? "G" : ""}{b ? "B" : ""}
              {!(r || g || b) && "off"})
            </div>
            <div className="flex gap-2">
              {[
                { ch: "R", val: r, set: setR, color: "bg-red-500" },
                { ch: "G", val: g, set: setG, color: "bg-green-500" },
                { ch: "B", val: b, set: setB, color: "bg-blue-500" },
              ].map(({ ch, val, set, color }) => (
                <Button
                  key={ch}
                  variant={val ? "default" : "outline"}
                  className={cn("flex-1", val && color)}
                  onClick={() => {
                    const next: [number, number, number] = [r, g, b]
                    if (ch === "R") next[0] = val ? 0 : 1
                    if (ch === "G") next[1] = val ? 0 : 1
                    if (ch === "B") next[2] = val ? 0 : 1
                    set(val ? 0 : 1)
                    setRgb.mutate(next)
                  }}
                >
                  {ch}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {volume > 0 ? (
              <Volume2 className="size-5" />
            ) : (
              <VolumeX className="size-5" />
            )}
            Speaker volume
          </CardTitle>
          <CardDescription>
            0-100% mapped to the SDK's 0-31 hardware range. Some modules ship
            without a speaker — in that case the SDK call returns an error and
            we surface the warning below.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-3">
            <Slider
              value={volume}
              min={0}
              max={100}
              onValueChange={setVolume}
              className="flex-1"
            />
            <span className="w-12 font-mono text-sm tabular-nums">{volume}%</span>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setVol.mutate(volume)}
              disabled={setVol.isPending}
            >
              Apply
            </Button>
          </div>
          {setVol.isError && (
            <div className="flex items-start gap-2 rounded-md border border-[var(--warning)] bg-[var(--warning)]/10 px-3 py-2 text-xs">
              <AlertCircle className="mt-0.5 size-4 text-[var(--warning)]" />
              <span>
                This hardware unit does not expose a speaker (P810 BaseBlink).
                The XR_Vein_SetVolume call is unsupported here.
              </span>
            </div>
          )}
          {!audioSupported && null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {sleeping ? <Moon className="size-5" /> : <Sun className="size-5" />}
            Sleep mode
          </CardTitle>
          <CardDescription>
            Disables the IR LEDs and pauses the on-device algorithm. Useful for
            keeping the sensor enumerated but idle.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-3">
          <span className="font-mono text-sm">
            {sleeping ? "Asleep" : "Active"}
          </span>
          <Button
            variant={sleeping ? "default" : "outline"}
            onClick={() => setSleep.mutate(!sleeping)}
            disabled={setSleep.isPending}
          >
            {sleeping ? "Wake up" : "Sleep"}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
