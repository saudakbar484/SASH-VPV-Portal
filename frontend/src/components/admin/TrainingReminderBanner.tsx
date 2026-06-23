import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { Brain, Loader2, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { endpoints } from "@/lib/api"
import { cn } from "@/lib/utils"

const DISMISS_KEY = "palmvein-training-banner-dismissed"

export function TrainingReminderBanner({ className }: { className?: string }) {
  const queryClient = useQueryClient()
  const status = useQuery({
    queryKey: ["training-status"],
    queryFn: endpoints.admin.trainingStatus,
    refetchInterval: (query) =>
      query.state.data?.training_in_progress ? 10_000 : 60_000,
  })

  const runTrain = useMutation({
    mutationFn: endpoints.admin.runTraining,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["training-status"] })
    },
  })

  const dismissed = sessionStorage.getItem(DISMISS_KEY) === "1"
  const data = status.data

  if (!data?.show_reminder_banner || dismissed) {
    return null
  }

  const pendingMessage = `${data.pending_images} new palm images are ready to train (${data.pending_sources.member_enroll ?? 0} member, ${data.pending_sources.admin_enroll ?? 0} admin). Retrain the matcher to improve accuracy across sessions.`

  const message = data.training_in_progress
    ? "Model training is running on this PC. Open Settings → Model training to see status and results when it finishes."
    : pendingMessage

  const isTraining = runTrain.isPending || data.training_in_progress

  return (
    <div
      className={cn(
        "admin-training-banner sticky top-14 z-20 flex items-start gap-3 border-b px-4 py-3 sm:items-center lg:top-16",
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <Brain className="mt-0.5 size-5 shrink-0 sm:mt-0" aria-hidden />
      <p className="min-w-0 flex-1 text-sm font-semibold leading-snug sm:text-[0.9375rem]">
        {message}
      </p>
      <div className="flex shrink-0 items-center gap-2">
        <Button
          size="sm"
          variant={isTraining ? "secondary" : "default"}
          className={cn(
            "whitespace-nowrap",
            !isTraining && "btn-brand",
          )}
          disabled={isTraining}
          onClick={() => runTrain.mutate()}
        >
          {isTraining ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Training…
            </>
          ) : (
            "Train on new data"
          )}
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="admin-training-banner__dismiss size-8 shrink-0"
          aria-label="Dismiss reminder"
          onClick={() => sessionStorage.setItem(DISMISS_KEY, "1")}
        >
          <X className="size-4" />
        </Button>
      </div>
    </div>
  )
}
