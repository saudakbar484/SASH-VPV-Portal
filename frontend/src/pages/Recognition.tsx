import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertTriangle,
  CheckCircle2,
  CircleX,
  Loader2,
  ScanFace,
  Sparkles,
  Timer,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ConfidenceBar } from "@/components/ConfidenceBar"
import { AdminPageHeader } from "@/components/AdminPageHeader"
import { GlassPanel, LiveFeedFrame } from "@/components/GlassPanel"
import { LiveFeedToolbar } from "@/components/LiveFeedToolbar"
import { LiveFeed } from "@/components/LiveFeed"
import { cn } from "@/lib/utils"
import {
  endpoints,
  type IdentifyResponse,
  type RegisteredIdentity,
  type VerifyResponse,
} from "@/lib/api"

export function Recognition() {
  const queryClient = useQueryClient()
  const [tab, setTab] = useState("verify")
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [verifyResult, setVerifyResult] = useState<VerifyResponse | null>(null)
  const [identifyResult, setIdentifyResult] =
    useState<IdentifyResponse | null>(null)
  const [identifyError, setIdentifyError] = useState<string | null>(null)
  const [verifyError, setVerifyError] = useState<string | null>(null)

  const identities = useQuery({
    queryKey: ["admin-registered-identities"],
    queryFn: endpoints.admin.registeredIdentities,
    retry: false,
  })

  const gallery = useQuery({
    queryKey: ["public-stats"],
    queryFn: endpoints.public.stats,
    staleTime: 30_000,
  })

  const verify = useMutation({
    mutationFn: (accountId: number) => endpoints.recognize.verifyAccount(accountId),
    onSuccess: (data) => {
      setVerifyResult(data)
      setVerifyError(null)
      queryClient.invalidateQueries({ queryKey: ["recognition-logs"] })
    },
    onError: (err) => {
      const msg = (err as { message?: string })?.message ?? "Verification request failed"
      setVerifyError(msg.includes("timeout") ? "Timed out — ensure scanner is connected and backend is warmed up." : msg)
    },
  })

  const identify = useMutation({
    mutationFn: () => endpoints.recognize.identify(5),
    onSuccess: (data) => {
      setIdentifyResult(data)
      setIdentifyError(null)
      queryClient.invalidateQueries({ queryKey: ["recognition-logs"] })
    },
    onError: (err) => {
      const msg = (err as { message?: string })?.message ?? "Identify request failed"
      setIdentifyError(
        msg.includes("timeout")
          ? "Timed out after 2 minutes — place palm on scanner, wait for live feed, then retry."
          : msg,
      )
    },
  })

  const enrolledPeople = identities.data?.identities ?? []
  const verifiablePeople = enrolledPeople.filter((person) =>
    person.hands.some((hand) => hand.enrolled),
  )
  const gallerySize = gallery.data?.enrolled_identities ?? 0
  const identitiesAuthError =
    identities.isError &&
    (identities.error as { response?: { status?: number } })?.response?.status === 401

  return (
    <div className="space-y-6">
      <AdminPageHeader
        title="Recognition Console"
        description="Run 1:1 verification or 1:N gallery search against enrolled palm templates."
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <GlassPanel
          title="Live scanner"
          description="Each Verify or Identify click captures one frame and runs the neural matcher."
        >
          <LiveFeedToolbar className="mb-2" showDistance />
          <LiveFeedFrame>
            <LiveFeed size="standard" />
          </LiveFeedFrame>
        </GlassPanel>

        <div className="space-y-4">
          <Tabs value={tab} onValueChange={setTab}>
            <TabsList className="w-full border border-white/10 bg-white/5">
              <TabsTrigger value="verify" className="flex-1 data-[state=active]:btn-brand/30">
                Verify (1:1)
              </TabsTrigger>
              <TabsTrigger value="identify" className="flex-1 data-[state=active]:btn-brand/30">
                Identify (1:N)
              </TabsTrigger>
            </TabsList>

            <TabsContent value="verify" className="mt-4 space-y-4">
              <GlassPanel title="Claim and prove">
                {identitiesAuthError ? (
                  <p className="text-sm text-red-500">
                    Session expired. Please sign out and sign in again as admin.
                  </p>
                ) : identities.isPending ? (
                  <p className="text-sm text-[var(--muted-foreground)]">Loading identities…</p>
                ) : verifiablePeople.length === 0 ? (
                  <p className="text-sm text-[var(--muted-foreground)]">
                    No enrolled palm templates yet. Use Enrollment or Signup first.
                  </p>
                ) : (
                  <div className="max-h-56 space-y-1 overflow-y-auto">
                    {verifiablePeople.map((person) => (
                      <PersonRow
                        key={person.account_id}
                        person={person}
                        selected={selectedAccountId === person.account_id}
                        onSelect={() => setSelectedAccountId(person.account_id)}
                      />
                    ))}
                  </div>
                )}
                <Button
                  className="mt-3 w-full btn-brand "
                  size="lg"
                  onClick={() => selectedAccountId && verify.mutate(selectedAccountId)}
                  disabled={!selectedAccountId || verify.isPending}
                >
                  {verify.isPending ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <ScanFace className="size-4" />
                  )}
                  Verify
                </Button>
              </GlassPanel>

              {verifyResult && <ResultCard verify={verifyResult} />}
              {verifyError && (
                <p className="text-center text-sm text-red-500">{verifyError}</p>
              )}
            </TabsContent>

            <TabsContent value="identify" className="mt-4 space-y-4">
              <GlassPanel title="Who is this?">
                <p className="mb-3 text-xs text-[var(--muted-foreground)]">
                  Hold palm steady 3–8 cm above the scanner until veins appear in the live feed.
                  First scan after restart may take up to a minute while the model loads.
                </p>
                {gallerySize === 0 && !gallery.isPending && (
                  <p className="mb-3 text-sm text-[var(--muted-foreground)]">
                    No enrolled templates in gallery yet.
                  </p>
                )}
                <Button
                  className="w-full btn-brand "
                  size="lg"
                  onClick={() => identify.mutate()}
                  disabled={identify.isPending || gallerySize === 0}
                >
                  {identify.isPending ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Sparkles className="size-4" />
                  )}
                  Identify
                </Button>
              </GlassPanel>

              {identifyResult && <IdentifyCard data={identifyResult} />}
              {identifyError && (
                <p className="text-center text-sm text-red-500">{identifyError}</p>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}

function PersonRow({
  person,
  selected,
  onSelect,
}: {
  person: RegisteredIdentity
  selected: boolean
  onSelect: () => void
}) {
  const left = person.hands.find((h) => h.hand === "Left")
  const right = person.hands.find((h) => h.hand === "Right")
  const handLabel = [
    left ? `L·${left.sample_count}` : null,
    right ? `R·${right.sample_count}` : null,
  ]
    .filter(Boolean)
    .join(" ")

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "flex w-full items-center justify-between rounded-lg border px-3 py-2 text-sm transition-colors",
        selected
          ? "border-[var(--primary)]/50 bg-[color-mix(in_srgb,var(--primary)_15%,transparent)]"
          : "border-white/10 bg-white/5 hover:border-[var(--primary)]/30",
      )}
    >
      <span className="font-medium">{person.full_name}</span>
      <span className="font-mono text-xs text-[var(--muted-foreground)]">
        {handLabel || `${person.total_samples} samples`}
      </span>
    </button>
  )
}

function ResultCard({ verify }: { verify: VerifyResponse }) {
  return (
    <GlassPanel
      title={verify.matched ? "Accepted" : "Rejected"}
      icon={
        verify.matched ? (
          <CheckCircle2 className="size-5 text-emerald-400" />
        ) : (
          <CircleX className="size-5 text-red-400" />
        )
      }
      description={`${verify.claimed_name} · ${verify.hand} hand matched`}
    >
      <ConfidenceBar
        similarity={verify.similarity}
        threshold={verify.threshold}
        confidence={verify.confidence}
        matched={verify.matched}
      />
      <div className="mt-3 flex items-center justify-between font-mono text-xs text-[var(--muted-foreground)]">
        <span className="flex items-center gap-1">
          <Timer className="size-3" />
          {verify.latency_ms} ms
        </span>
        {verify.log_id ? <span>log #{verify.log_id}</span> : null}
      </div>
      {verify.rejected_reason && (
        <div className="mt-3 flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" />
          <span className="break-all">{verify.rejected_reason}</span>
        </div>
      )}
    </GlassPanel>
  )
}

function IdentifyCard({ data }: { data: IdentifyResponse }) {
  const best = data.candidates[0]
  const hasCandidates = data.candidates.length > 0
  return (
    <GlassPanel
      title={
        data.matched
          ? `Matched: ${best?.name ?? "—"}`
          : data.rejected_reason
            ? "Capture rejected"
            : "No match above threshold"
      }
      icon={
        data.matched ? (
          <CheckCircle2 className="size-5 text-emerald-400" />
        ) : (
          <CircleX className="size-5 text-red-400" />
        )
      }
      description={
        hasCandidates
          ? `Top ${data.candidates.length} candidates · ${data.latency_ms} ms`
          : `${data.latency_ms} ms`
      }
    >
      {best && (
        <ConfidenceBar
          similarity={best.similarity}
          threshold={data.threshold}
          confidence={best.confidence}
          matched={data.matched}
        />
      )}
      {data.candidates.length > 1 && (
        <div className="mt-3 space-y-1 border-t border-white/10 pt-3">
          <div className="text-xs font-medium uppercase tracking-wider text-brand-muted">
            Other candidates
          </div>
          {data.candidates.slice(1).map((c) => (
            <div
              key={c.user_id}
              className="flex items-center justify-between font-mono text-xs"
            >
              <span>
                {c.name}{" "}
                <span className="text-[var(--muted-foreground)]">({c.hand})</span>
              </span>
              <span className="text-[var(--muted-foreground)]">
                sim {c.similarity.toFixed(4)}
              </span>
            </div>
          ))}
        </div>
      )}
      {data.rejected_reason && (
        <div className="mt-3 flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" />
          <span className="break-all">{data.rejected_reason}</span>
        </div>
      )}
    </GlassPanel>
  )
}
