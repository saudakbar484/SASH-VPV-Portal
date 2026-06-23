import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertCircle,
  Camera,
  CheckCircle2,
  CircleX,
  Hand,
  Loader2,
  Play,
  RotateCcw,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { AdminPageHeader } from "@/components/AdminPageHeader"
import { GlassPanel, LiveFeedFrame } from "@/components/GlassPanel"
import { LiveFeedToolbar } from "@/components/LiveFeedToolbar"
import { LiveFeed } from "@/components/LiveFeed"
import { endpoints } from "@/lib/api"
import { cn } from "@/lib/utils"

type Hand = "Left" | "Right"

interface ActiveSession {
  session_id: string
  name: string
  hand: Hand
  target_count: number
  captured_count: number
  attempts: number
  last_error: string | null
}

interface FinishResult {
  user_id: number
  name: string
  hand: Hand
  sample_count: number
  template_dim: number
}

const TARGET_COUNT = 5
const POSE_CUES = [
  "Place your palm flat over the sensor",
  "Lift and replace — same pose",
  "Lift and replace — slight natural shift",
  "Lift and replace — palm a touch closer",
  "Lift and replace — palm a touch further",
  "Lift and replace — last one",
]

export function Enrollment() {
  const queryClient = useQueryClient()
  const [name, setName] = useState("")
  const [hand, setHand] = useState<Hand>("Left")
  const [session, setSession] = useState<ActiveSession | null>(null)
  const [finished, setFinished] = useState<FinishResult | null>(null)
  const [debouncedName, setDebouncedName] = useState("")

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedName(name.trim()), 400)
    return () => clearTimeout(t)
  }, [name])

  const lookup = useQuery({
    queryKey: ["enroll-lookup", debouncedName],
    queryFn: () => endpoints.enroll.lookup(debouncedName),
    enabled: debouncedName.length >= 2 && !session,
  })

  const start = useMutation({
    mutationFn: () => endpoints.enroll.start(name.trim(), hand, TARGET_COUNT),
    onSuccess: (data: ActiveSession) => {
      setSession(data)
      setFinished(null)
    },
  })

  const capture = useMutation({
    mutationFn: (sessionId: string) => endpoints.enroll.capture(sessionId),
    onSuccess: (data: ActiveSession) => setSession(data),
  })

  const finish = useMutation({
    mutationFn: (sessionId: string) => endpoints.enroll.finish(sessionId),
    onSuccess: (data: FinishResult) => {
      setFinished(data)
      setSession(null)
      queryClient.invalidateQueries({ queryKey: ["identities"] })
    },
  })

  const cancel = useMutation({
    mutationFn: (sessionId: string) => endpoints.enroll.cancel(sessionId),
    onSuccess: () => setSession(null),
  })

  useEffect(() => {
    if (
      session &&
      session.captured_count >= session.target_count &&
      !finish.isPending
    ) {
      finish.mutate(session.session_id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.captured_count, session?.target_count])

  const canStart = name.trim().length >= 1 && !session && !start.isPending
  const remaining = session ? session.target_count - session.captured_count : 0
  const currentCueIdx = session ? session.captured_count : 0
  const currentCue =
    POSE_CUES[Math.min(currentCueIdx, POSE_CUES.length - 1)] ?? ""

  return (
    <div className="space-y-6">
      <AdminPageHeader
        title="Admin Enrollment"
        description="Extend palm datasets with smart name lookup — detects existing identities and similar names before capture."
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <GlassPanel
          title="Live scanner"
          description="Hold palm 3–8 cm above the sensor. Follow the pose cue between captures."
          icon={<Hand className="size-5 icon-brand" />}
        >
          <LiveFeedToolbar className="mb-2" />
          <LiveFeedFrame>
            <LiveFeed size="standard" />
          </LiveFeedFrame>
          <div className="mt-4 rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-center">
            {session ? (
              <>
                <div className="text-xs uppercase tracking-wider text-brand-muted">
                  Pose {session.captured_count + 1} of {session.target_count}
                </div>
                <div className="mt-1 font-medium">{currentCue}</div>
              </>
            ) : finished ? (
              <div className="font-medium text-emerald-400">
                Enrollment complete for {finished.name}.
              </div>
            ) : (
              <div className="text-sm text-[var(--muted-foreground)]">
                Enter a name and hand to start a session.
              </div>
            )}
          </div>
        </GlassPanel>

        <div className="space-y-4">
          <GlassPanel title="New identity">
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="enroll-name">Name</Label>
                <Input
                  id="enroll-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. huzaifa"
                disabled={!!session || start.isPending}
              />
              {lookup.data?.message && !session && (
                <div className="rounded-md border border-[var(--primary)]/30 bg-[color-mix(in_srgb,var(--primary)_10%,transparent)] px-3 py-2 text-xs text-[var(--foreground)]">
                  {lookup.data.message}
                  {lookup.data.similar.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {lookup.data.similar.map((m) => (
                        <Button
                          key={m.name}
                          type="button"
                          size="sm"
                          variant="outline"
                          className="h-7 border-[var(--primary)]/40 text-xs"
                          onClick={() => setName(m.name)}
                        >
                          Use {m.name}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
              <div className="space-y-1.5">
                <Label>Hand</Label>
                <div className="flex gap-2">
                  {(["Left", "Right"] as const).map((h) => (
                    <Button
                      key={h}
                      type="button"
                      variant={hand === h ? "default" : "outline"}
                      size="sm"
                      className={cn("flex-1", hand === h && "btn-brand ")}
                      disabled={!!session}
                      onClick={() => setHand(h)}
                    >
                      {h}
                    </Button>
                  ))}
                </div>
              </div>

              {!session && (
                <Button
                  className="w-full btn-brand "
                  size="lg"
                  onClick={() => start.mutate()}
                  disabled={!canStart}
                >
                  {start.isPending ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Play className="size-4" />
                  )}
                  Start session
                </Button>
              )}

              {session && (
                <div className="space-y-3 rounded-lg border border-white/10 bg-white/5 p-3">
                  <div className="space-y-1.5">
                    <div className="flex justify-between font-mono text-xs">
                      <span className="text-[var(--muted-foreground)]">Progress</span>
                      <span>
                        {session.captured_count} / {session.target_count}
                      </span>
                    </div>
                    <Progress
                      value={session.captured_count}
                      max={session.target_count}
                      className="h-2"
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button
                      className="flex-1 btn-brand "
                      size="lg"
                      onClick={() => capture.mutate(session.session_id)}
                      disabled={capture.isPending || finish.isPending || remaining <= 0}
                    >
                      {capture.isPending ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <Camera className="size-4" />
                      )}
                      Capture
                    </Button>
                    <Button
                      variant="outline"
                      size="lg"
                      className="border-white/15"
                      onClick={() => cancel.mutate(session.session_id)}
                      disabled={cancel.isPending || finish.isPending}
                    >
                      <CircleX className="size-4" />
                    </Button>
                  </div>
                  {session.last_error && (
                    <div className="flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                      <AlertCircle className="mt-0.5 size-4 shrink-0" />
                      <span>{session.last_error}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </GlassPanel>

          {finished && (
            <GlassPanel
              title="Enrolled"
              icon={<CheckCircle2 className="size-5 text-emerald-400" />}
            >
              <dl className="grid grid-cols-[100px_minmax(0,1fr)] gap-y-1 font-mono text-xs">
                <dt className="text-[var(--muted-foreground)]">User ID</dt>
                <dd>{finished.user_id}</dd>
                <dt className="text-[var(--muted-foreground)]">Name</dt>
                <dd>{finished.name}</dd>
                <dt className="text-[var(--muted-foreground)]">Hand</dt>
                <dd>{finished.hand}</dd>
                <dt className="text-[var(--muted-foreground)]">Samples</dt>
                <dd>{finished.sample_count}</dd>
                <dt className="text-[var(--muted-foreground)]">Template</dt>
                <dd>{finished.template_dim}-d</dd>
              </dl>
              <Button
                variant="outline"
                size="sm"
                className="mt-3 w-full border-white/15"
                onClick={() => {
                  setFinished(null)
                  setName("")
                }}
              >
                <RotateCcw className="size-4" />
                Enroll another
              </Button>
            </GlassPanel>
          )}

          <GlassPanel title="Tips">
            <ul className="space-y-1.5 text-xs text-[var(--muted-foreground)]">
              <li>• Keep palm 3–8 cm above the sensor.</li>
              <li>• Lift between captures for natural micro-variation.</li>
              <li>• Wait ~1 s between captures for a fresh frame.</li>
              <li>• For full signup (both hands + account), use Create Account instead.</li>
            </ul>
          </GlassPanel>
        </div>
      </div>
    </div>
  )
}
