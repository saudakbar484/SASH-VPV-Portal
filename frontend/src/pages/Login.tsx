import { useEffect, useState } from "react"

import { Link, useNavigate } from "react-router-dom"

import { useMutation } from "@tanstack/react-query"

import { Camera, CheckCircle2, Loader2, XCircle } from "lucide-react"

import { AuthMethodTabs, AuthScanPanels } from "@/components/auth/AuthScanPanels"
import { EmailVerifyPanel, ForgotPasswordPanel } from "@/components/auth/AuthEmailPanels"
import { AuthLayout } from "@/components/AuthLayout"
import { PalmVeinLogo } from "@/components/PalmVeinLogo"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { endpoints } from "@/lib/api"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/store/useAuthStore"

const PALM_STEPS = [
  "Capturing palm frame…",
  "Extracting vein pattern…",
  "Matching registered templates…",
]

function parseApiError(err: unknown, fallback: string) {
  const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  return typeof msg === "string" ? msg : fallback
}

export function Login({ employeeMode = false, customerMode = false }: { employeeMode?: boolean; customerMode?: boolean }) {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const isAdminPortal = !employeeMode && !customerMode
  const [method, setMethod] = useState<"palm" | "email">(isAdminPortal ? "email" : "palm")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [lastProbeUrl, setLastProbeUrl] = useState<string | null>(null)
  const [palmStepIdx, setPalmStepIdx] = useState(0)
  const [loginError, setLoginError] = useState<string | null>(null)
  const [subview, setSubview] = useState<"default" | "forgot" | "verify">("default")

  const portalTitle = employeeMode ? "Employee portal" : customerMode ? "Member portal" : "Admin portal"
  const heading = employeeMode ? "Employee sign in" : customerMode ? "Member sign in" : "Admin sign in"

  const afterLogin = (role?: string) => {
    if (role === "admin") return "/dashboard"
    if (role === "customer" || customerMode) return "/"
    if (employeeMode) return "/employee/dashboard"
    if (role === "employee") return "/employee/dashboard"
    return "/"
  }

  const passwordLogin = useMutation({
    mutationFn: () => endpoints.auth.login(email, password),
    onSuccess: (data) => {
      setAuth(data.access_token, {
        ...data.user,
        role: data.user.role ?? "employee",
      })
      navigate(afterLogin(data.user.role))
    },
    onError: (err) => {
      const msg = parseApiError(err, "Invalid email or password")
      setLoginError(msg)
      if (msg.toLowerCase().includes("not verified")) {
        setSubview("verify")
      }
    },
  })

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
        navigate(afterLogin(data.role ?? undefined))
      }
    },
  })

  useEffect(() => {
    if (!palmLogin.isPending) {
      setPalmStepIdx(0)
      return
    }
    setPalmStepIdx(0)
    const timers = [
      window.setTimeout(() => setPalmStepIdx(1), 900),
      window.setTimeout(() => setPalmStepIdx(2), 2200),
    ]
    return () => timers.forEach(clearTimeout)
  }, [palmLogin.isPending])

  return (
    <AuthLayout themePortal="admin">
      <div className={cn("glass-panel w-full p-8", method === "palm" ? "max-w-2xl" : "max-w-md")}>
        <div className="mb-2 flex justify-center">
          <PalmVeinLogo variant="full" size={72} subtitle={portalTitle} />
        </div>
        <h1 className="text-center text-xl font-bold">{heading}</h1>
        <p className="mb-6 mt-1 text-center text-sm text-[var(--muted-foreground)]">
          Secure biometric access
        </p>

        <AuthMethodTabs value={method} onChange={setMethod} showPalm={!isAdminPortal} />

        {subview === "forgot" ? (
          <ForgotPasswordPanel defaultEmail={email} onBack={() => setSubview("default")} />
        ) : subview === "verify" ? (
          <EmailVerifyPanel
            email={email}
            onVerified={(data) => {
              setAuth(data.access_token, {
                ...data.user,
                role: data.user.role ?? "admin",
              })
              navigate(afterLogin(data.user.role))
            }}
            onBack={() => setSubview("default")}
          />
        ) : method === "palm" ? (
          <div className="space-y-4">
            <AuthScanPanels probeUrl={lastProbeUrl} />

            <Button
              className="btn-brand w-full"
              size="lg"
              onClick={() => palmLogin.mutate()}
              disabled={palmLogin.isPending}
            >
              {palmLogin.isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  {PALM_STEPS[palmStepIdx]}
                </>
              ) : (
                <>
                  <Camera className="size-4" />
                  Capture & sign in
                </>
              )}
            </Button>

            {palmLogin.data && (
              <div
                className={cn(
                  "flex items-start gap-2 rounded-lg border px-3 py-2 text-sm",
                  palmLogin.data.matched
                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-500"
                    : "border-red-500/30 bg-red-500/10 text-red-500",
                )}
              >
                {palmLogin.data.matched ? (
                  <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
                ) : (
                  <XCircle className="mt-0.5 size-4 shrink-0" />
                )}
                <span>
                  {palmLogin.data.matched
                    ? `Matched ${palmLogin.data.full_name} (sim ${palmLogin.data.similarity.toFixed(3)})`
                    : `${palmLogin.data.message ?? "No match"}${
                        palmLogin.data.similarity > 0
                          ? ` (sim ${palmLogin.data.similarity.toFixed(3)} / ${palmLogin.data.threshold.toFixed(3)})`
                          : ""
                      }`}
                </span>
              </div>
            )}
            {palmLogin.isError && (
              <p className="text-center text-sm text-red-500">Login request failed</p>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="login-email">Email</Label>
              <Input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="login-password">Password</Label>
              <Input
                id="login-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                className="text-xs text-[var(--muted-foreground)] hover:text-[var(--primary)] hover:underline"
                onClick={() => {
                  setLoginError(null)
                  setSubview("forgot")
                }}
              >
                Forgot password?
              </button>
            </div>
            <Button
              className="btn-brand w-full"
              size="lg"
              onClick={() => {
                setLoginError(null)
                passwordLogin.mutate()
              }}
              disabled={passwordLogin.isPending || !email || !password}
            >
              {passwordLogin.isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </Button>
            {loginError && <p className="text-center text-sm text-red-500">{loginError}</p>}
          </div>
        )}

        <p className="mt-6 text-center text-xs text-[var(--muted-foreground)]">
          {!employeeMode && !customerMode && (
            <>
              Employee?{" "}
              <Link to="/employee/login" className="hover:text-[var(--primary)] hover:underline">
                Employee sign in
              </Link>
              {" · "}
              Member?{" "}
              <Link to="/user/login" className="hover:text-[var(--primary)] hover:underline">
                Member sign in
              </Link>
            </>
          )}
          {(employeeMode || customerMode) && (
            <>
              No account?{" "}
              <Link
                to={customerMode ? "/user/signup" : "/employee/signup"}
                className="icon-brand hover:underline"
              >
                Create one
              </Link>
            </>
          )}
        </p>
      </div>
    </AuthLayout>
  )
}
