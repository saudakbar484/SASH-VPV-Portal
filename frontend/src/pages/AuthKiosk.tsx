import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useMutation } from "@tanstack/react-query"
import { Camera, CheckCircle2, Loader2, XCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { LiveFeed } from "@/components/LiveFeed"
import { LiveFeedToolbar } from "@/components/LiveFeedToolbar"
import { PalmVeinLogo } from "@/components/PalmVeinLogo"
import { AuthLayout } from "@/components/AuthLayout"
import { endpoints } from "@/lib/api"
import { useAuthStore } from "@/store/useAuthStore"

const STEPS = [
  "Capturing palm frame…",
  "Extracting vein pattern…",
  "Matching against registered accounts…",
]

export function AuthKiosk() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated())
  const [stepIdx, setStepIdx] = useState(0)
  const [lastProbeUrl, setLastProbeUrl] = useState<string | null>(null)

  const palmLogin = useMutation({
    mutationFn: endpoints.auth.loginPalm,
    onSuccess: (data) => {
      if (data.probe_image_url) {
        setLastProbeUrl(`${data.probe_image_url}&t=${Date.now()}`)
      }
      if (data.matched && data.access_token && data.account_id) {
        setAuth(data.access_token, {
          account_id: data.account_id,
          email: data.email!,
          full_name: data.full_name!,
          dataset_id: data.dataset_id ?? "",
          dataset_name: data.dataset_name!,
          role: data.role ?? "employee",
          session_id: data.session_id ?? null,
        })
        navigate(data.role === "admin" ? "/dashboard" : "/employee/dashboard")
      }
    },
  })

  useEffect(() => {
    if (!palmLogin.isPending) {
      setStepIdx(0)
      return
    }
    setStepIdx(0)
    const timers = [
      window.setTimeout(() => setStepIdx(1), 900),
      window.setTimeout(() => setStepIdx(2), 2200),
    ]
    return () => timers.forEach(clearTimeout)
  }, [palmLogin.isPending])

  return (
    <AuthLayout themePortal="employee" className="flex-col">
      <header className="flex items-center justify-between px-8 py-6">
        <PalmVeinLogo variant="header" size={30} />
        <div className="flex gap-2">
          {!isAuthenticated && (
            <>
              <Button variant="outline" className="border-white/15" asChild>
                <Link to="/login">Staff login</Link>
              </Button>
              <Button variant="outline" className="border-white/15" asChild>
                <Link to="/signup">Register</Link>
              </Button>
            </>
          )}
          {isAuthenticated && (
            <Button className="btn-brand " asChild>
              <Link to="/dashboard">Dashboard</Link>
            </Button>
          )}
        </div>
      </header>

      <main className="flex flex-1 flex-col items-center justify-center px-6 pb-12">
        <div className="glass-panel w-full max-w-4xl p-8">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
            <div>
              <p className="mb-3 text-xs uppercase tracking-wider text-brand-muted">Live preview</p>
              <LiveFeedToolbar className="mb-2" />
              <div className="relative rounded-2xl border border-white/10 bg-black/60 p-3">
                <LiveFeed size="large" />
                <span className="absolute bottom-5 left-5 rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-semibold text-emerald-400 ring-1 ring-emerald-500/40">
                  ● LIVE
                </span>
              </div>
              <p className="mt-3 text-center text-sm text-[var(--muted-foreground)]">
                Hold palm 3–8 cm above the sensor, then press Scan Palm.
              </p>
            </div>

            <div className="flex flex-col justify-center">
              <h2 className="text-3xl font-bold tracking-wide">Scan to sign in</h2>
              <p className="mt-2 text-[var(--muted-foreground)]">
                Place your registered palm over the scanner. Matching uses your enrolled vein
                template — no password required.
              </p>

              <Button
                className="mt-8 h-14 w-full btn-brand text-lg "
                onClick={() => palmLogin.mutate()}
                disabled={palmLogin.isPending}
              >
                {palmLogin.isPending ? (
                  <>
                    <Loader2 className="size-5 animate-spin" />
                    {STEPS[stepIdx]}
                  </>
                ) : (
                  <>
                    <Camera className="size-5" />
                    Scan Palm
                  </>
                )}
              </Button>

              {palmLogin.isPending && (
                <div className="mt-4 space-y-2">
                  {STEPS.map((label, i) => (
                    <div
                      key={label}
                      className={
                        i <= stepIdx
                          ? "text-sm text-[var(--foreground)]"
                          : "text-sm text-[var(--muted-foreground)]"
                      }
                    >
                      {i < stepIdx ? "✓" : i === stepIdx ? "…" : "○"} {label}
                    </div>
                  ))}
                </div>
              )}

              {palmLogin.data && !palmLogin.data.matched && (
                <div className="mt-4 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
                  <XCircle className="mt-0.5 size-4 shrink-0" />
                  <span>
                    {palmLogin.data.message}
                    {palmLogin.data.similarity > 0 && (
                      <>
                        {" "}
                        (similarity {palmLogin.data.similarity.toFixed(3)} / threshold{" "}
                        {palmLogin.data.threshold.toFixed(3)})
                      </>
                    )}
                  </span>
                </div>
              )}

              {palmLogin.isError && (
                <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
                  Scan failed — check scanner connection and try again.
                </div>
              )}

              {lastProbeUrl && (
                <div className="mt-6">
                  <p className="mb-2 text-xs uppercase tracking-wider text-brand-muted">
                    Last capture
                  </p>
                  <img
                    src={lastProbeUrl}
                    alt="Last palm capture"
                    className="max-h-32 rounded-lg border border-white/10 object-contain"
                  />
                </div>
              )}

              {palmLogin.data?.matched && (
                <div className="mt-4 flex items-center gap-2 text-emerald-400">
                  <CheckCircle2 className="size-5" />
                  Welcome, {palmLogin.data.full_name}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </AuthLayout>
  )
}
