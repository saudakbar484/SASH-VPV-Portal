import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { Brain, Loader2 } from "lucide-react"

import { GlassPanel } from "@/components/GlassPanel"
import { Button } from "@/components/ui/button"
import { endpoints } from "@/lib/api"

export function ModelTrainingPanel() {
  const queryClient = useQueryClient()
  const status = useQuery({
    queryKey: ["training-status"],
    queryFn: endpoints.admin.trainingStatus,
    refetchInterval: 30_000,
  })

  const runTrain = useMutation({
    mutationFn: endpoints.admin.runTraining,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training-status"] })
    },
  })

  const data = status.data

  return (
    <GlassPanel
      title="Model training"
      description="Weekly supervised fine-tune on new enrollment captures from all panels."
      icon={<Brain className="size-5 text-[var(--primary)]" />}
    >
      {status.isPending ? (
        <p className="text-sm text-[var(--muted-foreground)]">Loading training status…</p>
      ) : data ? (
        <div className="space-y-4 text-sm">
          <dl className="grid gap-2 sm:grid-cols-2">
            <div>
              <dt className="text-[var(--muted-foreground)]">Last trained</dt>
              <dd className="font-medium">
                {data.last_trained_at
                  ? new Date(data.last_trained_at).toLocaleString()
                  : "Never"}
              </dd>
            </div>
            <div>
              <dt className="text-[var(--muted-foreground)]">Pending images</dt>
              <dd className="font-medium">{data.pending_images}</dd>
            </div>
            <div>
              <dt className="text-[var(--muted-foreground)]">Days since train</dt>
              <dd className="font-medium">{data.days_since_train}</dd>
            </div>
            <div>
              <dt className="text-[var(--muted-foreground)]">Last status</dt>
              <dd className="font-medium">{data.last_run_status ?? "—"}</dd>
            </div>
            {data.last_val_eer != null && (
              <div>
                <dt className="text-[var(--muted-foreground)]">Val EER</dt>
                <dd className="font-mono font-medium">{data.last_val_eer.toFixed(4)}</dd>
              </div>
            )}
            {data.last_val_rank1 != null && (
              <div>
                <dt className="text-[var(--muted-foreground)]">Val Rank-1</dt>
                <dd className="font-mono font-medium">{data.last_val_rank1.toFixed(4)}</dd>
              </div>
            )}
          </dl>
          <p className="text-xs text-[var(--muted-foreground)]">
            Member enroll: {data.pending_sources.member_enroll ?? 0} · Admin enroll:{" "}
            {data.pending_sources.admin_enroll ?? 0}
          </p>
          <Button
            className="btn-brand"
            disabled={runTrain.isPending || data.training_in_progress}
            onClick={() => runTrain.mutate()}
          >
            {runTrain.isPending || data.training_in_progress ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Training…
              </>
            ) : (
              "Run weekly retrain now"
            )}
          </Button>
          {runTrain.data?.message && (
            <p className="text-xs text-emerald-600">{runTrain.data.message}</p>
          )}
        </div>
      ) : null}
    </GlassPanel>
  )
}
