import { useState } from "react"

import { Link, useNavigate } from "react-router-dom"

import { useMutation } from "@tanstack/react-query"

import { Camera, Loader2 } from "lucide-react"

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

function parseApiError(err: unknown, fallback: string) {
  const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  return typeof msg === "string" ? msg : fallback
}

export function EmployeeLogin() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [method, setMethod] = useState<"palm" | "email">("email")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [lastProbeUrl, setLastProbeUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [subview, setSubview] = useState<"default" | "forgot" | "verify">("default")

  const passwordLogin = useMutation({
    mutationFn: () => endpoints.auth.login(email, password),
    onSuccess: (data) => {
      const role = data.user.role ?? "employee"
      if (role === "admin") {
        setError("Admin accounts must use the admin portal at /login")
        return
      }
      if (role === "customer") {
        setError("Member accounts must use the member portal at /user/login")
        return
      }
      setAuth(data.access_token, { ...data.user, role: "employee" })
      navigate("/employee/dashboard")
    },
    onError: (err) => {
      const msg = parseApiError(err, "Invalid email or password")
      setError(msg)
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
      if (!data.matched || !data.access_token) {
        setError(data.message ?? "Palm not recognized")
        return
      }
      const role = data.role ?? "employee"
      if (role === "admin") {
        setError("Admin palm matched — use the admin portal at /login")
        return
      }
      if (role === "customer") {
        setError("Member palm matched — use the member portal at /user/login")
        return
      }
      setAuth(data.access_token, {
        account_id: data.account_id!,
        email: data.email!,
        full_name: data.full_name!,
        dataset_id: data.dataset_id ?? "",
        dataset_name: data.dataset_name!,
        role: "employee",
        session_id: data.session_id ?? null,
      })
      navigate("/employee/dashboard")
    },
    onError: () => setError("Palm login failed"),
  })

  return (
    <AuthLayout themePortal="employee">
      <div className={cn("glass-panel w-full p-8", method === "palm" ? "max-w-2xl" : "max-w-md")}>
        <div className="mb-2 flex justify-center">
          <PalmVeinLogo variant="full" size={72} subtitle="Employee portal" />
        </div>
        <h1 className="text-center text-xl font-bold">Employee sign in</h1>
        <p className="mb-6 mt-1 text-center text-sm text-[var(--muted-foreground)]">
          Sign in with your work account. Registration is invite-only from HR.
        </p>

        <AuthMethodTabs value={method} onChange={setMethod} palmLabel="Palm" emailLabel="Email" />

        {subview === "forgot" ? (
          <ForgotPasswordPanel defaultEmail={email} onBack={() => setSubview("default")} />
        ) : subview === "verify" ? (
          <EmailVerifyPanel
            email={email}
            onVerified={(data) => {
              setAuth(data.access_token, { ...data.user, role: "employee" })
              navigate("/employee/dashboard")
            }}
            onBack={() => setSubview("default")}
          />
        ) : method === "email" ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="emp-email">Work email</Label>
              <Input
                id="emp-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                autoComplete="email"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="emp-password">Password</Label>
              <Input
                id="emp-password"
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
                  setError(null)
                  setSubview("forgot")
                }}
              >
                Forgot password?
              </button>
            </div>
            <Button
              className="btn-brand w-full"
              size="lg"
              disabled={passwordLogin.isPending || !email || !password}
              onClick={() => {
                setError(null)
                passwordLogin.mutate()
              }}
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
          </div>
        ) : (
          <div className="space-y-4">
            <AuthScanPanels probeUrl={lastProbeUrl} />
            <Button
              className="btn-brand w-full"
              size="lg"
              disabled={palmLogin.isPending}
              onClick={() => {
                setError(null)
                palmLogin.mutate()
              }}
            >
              {palmLogin.isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Scanning…
                </>
              ) : (
                <>
                  <Camera className="size-4" />
                  Capture & sign in
                </>
              )}
            </Button>
          </div>
        )}

        {error && (
          <p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-center text-sm text-red-500">
            {error}
          </p>
        )}

        <p className="mt-6 text-center text-xs text-[var(--muted-foreground)]">
          Admin?{" "}
          <Link to="/login" className="hover:text-[var(--primary)] hover:underline">
            Admin sign in
          </Link>
          {" · "}
          Member?{" "}
          <Link to="/user/login" className="hover:text-[var(--primary)] hover:underline">
            Member sign in
          </Link>
        </p>
      </div>
    </AuthLayout>
  )
}
