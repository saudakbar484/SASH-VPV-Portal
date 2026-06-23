import { useEffect, useState } from "react"

import { useNavigate } from "react-router-dom"

import { useMutation, useQueryClient } from "@tanstack/react-query"

import { CheckCircle2, Loader2 } from "lucide-react"

import { CustomerPageHeader } from "@/components/customer/CustomerPageHeader"
import { PalmCapturePanel, type PalmSessionStatus } from "@/components/PalmCapturePanel"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { endpoints } from "@/lib/api"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/store/useAuthStore"

type EnrollStep = "setup" | "capture" | "done"

function parseApiError(err: unknown, fallback: string) {
  const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  return typeof msg === "string" ? msg : fallback
}

export function UserEnrollPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [step, setStep] = useState<EnrollStep>("setup")
  const [firstHand, setFirstHand] = useState<"Left" | "Right">("Left")
  const [consent, setConsent] = useState(false)
  const [registerSessionId, setRegisterSessionId] = useState("")
  const [sessionStatus, setSessionStatus] = useState<PalmSessionStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  const startEnroll = useMutation({
    mutationFn: () => endpoints.auth.registerEnrollStart(firstHand),
    onSuccess: (data) => {
      setRegisterSessionId(data.register_session_id)
      setSessionStatus(data)
      setStep("capture")
      setError(null)
    },
    onError: (err) => setError(parseApiError(err, "Could not start enrollment")),
  })

  const switchHand = useMutation({
    mutationFn: (next: "Left" | "Right") => endpoints.auth.registerSwitchHand(registerSessionId, next),
    onSuccess: (data) => setSessionStatus(data),
  })

  const complete = useMutation({
    mutationFn: () => endpoints.auth.registerComplete(registerSessionId),
    onSuccess: (data) => {
      if (!data.access_token) return
      setAuth(data.access_token, {
        account_id: data.account_id,
        email: data.email,
        full_name: data.full_name,
        dataset_id: data.dataset_id,
        dataset_name: data.dataset_name,
        role: data.role ?? "customer",
        session_id: data.session_id ?? null,
      })
      void queryClient.invalidateQueries({ queryKey: ["user-dashboard"] })
      void queryClient.invalidateQueries({ queryKey: ["user-profile"] })
      setStep("done")
    },
    onError: (err) => setError(parseApiError(err, "Could not finish enrollment")),
  })

  useEffect(() => {
    if (sessionStatus?.both_complete && !complete.isPending && step === "capture") {
      complete.mutate()
    }
  }, [sessionStatus?.both_complete, step, complete])

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
      <CustomerPageHeader
        title="Enroll your palm"
        description="Capture both palms to enable palm sign-in. You can do this anytime after creating your account."
      />

      {step === "setup" && (
        <div className="customer-card mx-auto max-w-md space-y-4 p-6">
          <p className="text-sm text-[var(--muted-foreground)]">
            Place your hand 3–8 cm above the scanner. You will capture 10 images per hand.
          </p>
          <div className="space-y-2">
            <Label>Which hand first?</Label>
            <div className="flex gap-2">
              {(["Left", "Right"] as const).map((h) => (
                <Button
                  key={h}
                  type="button"
                  variant={firstHand === h ? "default" : "outline"}
                  className={cn("flex-1", firstHand === h && "btn-brand")}
                  onClick={() => setFirstHand(h)}
                >
                  {h} first
                </Button>
              ))}
            </div>
          </div>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              className="mt-1"
            />
            I consent to biometric palm vein processing for identity verification.
          </label>
          <Button
            className="btn-brand w-full"
            disabled={!consent || startEnroll.isPending}
            onClick={() => startEnroll.mutate()}
          >
            {startEnroll.isPending ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Starting…
              </>
            ) : (
              "Start palm capture"
            )}
          </Button>
          {error && <p className="text-center text-sm text-red-500">{error}</p>}
        </div>
      )}

      {step === "capture" && sessionStatus && registerSessionId && (
        <div className="space-y-4">
          <PalmCapturePanel
            registerSessionId={registerSessionId}
            sessionStatus={sessionStatus}
            onStatusChange={setSessionStatus}
            onSwitchHand={(h) => switchHand.mutate(h)}
            switchHandPending={switchHand.isPending}
          />
          {complete.isPending && (
            <p className="text-center text-sm text-[var(--muted-foreground)]">
              <Loader2 className="mr-2 inline size-4 animate-spin" />
              Saving enrollment…
            </p>
          )}
          {error && <p className="text-center text-sm text-red-500">{error}</p>}
        </div>
      )}

      {step === "done" && (
        <div className="customer-card mx-auto max-w-md p-8 text-center">
          <CheckCircle2 className="mx-auto size-12 text-emerald-500" />
          <p className="mt-4 font-semibold">Palm enrollment complete</p>
          <p className="mt-2 text-sm text-[var(--muted-foreground)]">
            Both palms are enrolled. You can now use palm login on the sign-in page.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Button className="btn-brand" onClick={() => navigate("/")}>
              Back to home
            </Button>
            <Button variant="outline" onClick={() => navigate("/user/login")}>
              Try palm sign-in
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
