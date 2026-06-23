import { useState } from "react"

import { useMutation } from "@tanstack/react-query"

import { CheckCircle2, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { endpoints } from "@/lib/api"

function parseApiError(err: unknown, fallback: string) {
  const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  return typeof msg === "string" ? msg : fallback
}

type EmailVerifyPanelProps = {
  email: string
  emailSent?: boolean
  onVerified: (data: {
    access_token: string
    user: {
      account_id: number
      email: string
      full_name: string
      dataset_id: string
      dataset_name: string
      role?: string
      session_id?: number | null
    }
  }) => void
  onBack?: () => void
}

export function EmailVerifyPanel({ email, emailSent = true, onVerified, onBack }: EmailVerifyPanelProps) {
  const [code, setCode] = useState("")
  const [error, setError] = useState<string | null>(null)

  const verify = useMutation({
    mutationFn: () => endpoints.auth.verifyEmail(email.trim(), code.trim()),
    onSuccess: (data) => {
      if (data.access_token && data.user) {
        onVerified({ access_token: data.access_token, user: data.user })
        return
      }
      setError("Verification succeeded but sign-in failed — try signing in manually")
    },
    onError: (err) => setError(parseApiError(err, "Invalid verification code")),
  })

  const resend = useMutation({
    mutationFn: () => endpoints.auth.resendVerification(email.trim()),
    onSuccess: (data) => setError(data.email_sent ? null : data.message),
    onError: (err) => setError(parseApiError(err, "Could not resend code")),
  })

  return (
    <div className="space-y-4">
      <h2 className="text-center text-xl font-bold">Verify your email</h2>
      <p className="text-center text-sm text-[var(--muted-foreground)]">
        {emailSent
          ? `Enter the 6-digit code sent to ${email}.`
          : `We could not send email to ${email}. Check SMTP settings or try resend.`}
      </p>
      <div className="space-y-2">
        <Label htmlFor="verify-code">Verification code</Label>
        <Input
          id="verify-code"
          inputMode="numeric"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="123456"
          autoComplete="one-time-code"
        />
      </div>
      <Button
        className="btn-brand w-full"
        disabled={!code.trim() || verify.isPending}
        onClick={() => {
          setError(null)
          verify.mutate()
        }}
      >
        {verify.isPending ? (
          <>
            <Loader2 className="size-4 animate-spin" />
            Verifying…
          </>
        ) : (
          "Verify and sign in"
        )}
      </Button>
      <Button variant="outline" className="w-full" disabled={resend.isPending} onClick={() => resend.mutate()}>
        {resend.isPending ? "Sending…" : "Resend code"}
      </Button>
      {onBack && (
        <Button variant="ghost" className="w-full" onClick={onBack}>
          Back
        </Button>
      )}
      {error && <p className="text-center text-sm text-red-500">{error}</p>}
    </div>
  )
}

type ForgotPasswordPanelProps = {
  defaultEmail?: string
  onBack: () => void
  onDone?: (role?: string) => void
}

export function ForgotPasswordPanel({ defaultEmail = "", onBack, onDone }: ForgotPasswordPanelProps) {
  const [step, setStep] = useState<"email" | "reset" | "done">("email")
  const [email, setEmail] = useState(defaultEmail)
  const [code, setCode] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [resetRole, setResetRole] = useState<string | undefined>()
  const [error, setError] = useState<string | null>(null)

  const forgot = useMutation({
    mutationFn: () => endpoints.auth.forgotPassword(email.trim()),
    onSuccess: () => {
      setStep("reset")
      setError(null)
    },
    onError: (err) => setError(parseApiError(err, "Could not send reset code")),
  })

  const reset = useMutation({
    mutationFn: () =>
      endpoints.auth.resetPassword({
        email: email.trim(),
        code: code.trim(),
        password,
        confirm_password: confirmPassword,
      }),
    onSuccess: (data) => {
      setResetRole(data.role)
      setStep("done")
      setError(null)
    },
    onError: (err) => setError(parseApiError(err, "Could not reset password")),
  })

  if (step === "done") {
    return (
      <div className="space-y-4 text-center">
        <CheckCircle2 className="mx-auto size-12 text-emerald-500" />
        <p className="font-semibold">Password updated</p>
        <p className="text-sm text-[var(--muted-foreground)]">You can now sign in with your new password.</p>
        <Button
          className="btn-brand w-full"
          onClick={() => {
            onDone?.(resetRole)
            onBack()
          }}
        >
          Back to sign in
        </Button>
      </div>
    )
  }

  if (step === "reset") {
    return (
      <div className="space-y-4">
        <h2 className="text-center text-xl font-bold">Reset password</h2>
        <p className="text-center text-sm text-[var(--muted-foreground)]">
          Enter the 6-digit code sent to {email} and choose a new password.
        </p>
        <div className="space-y-2">
          <Label>Reset code</Label>
          <Input inputMode="numeric" value={code} onChange={(e) => setCode(e.target.value)} placeholder="123456" />
        </div>
        <div className="space-y-2">
          <Label>New password</Label>
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
        </div>
        <div className="space-y-2">
          <Label>Confirm password</Label>
          <Input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
          />
        </div>
        <Button
          className="btn-brand w-full"
          disabled={!code || !password || password !== confirmPassword || reset.isPending}
          onClick={() => {
            setError(null)
            reset.mutate()
          }}
        >
          {reset.isPending ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Updating…
            </>
          ) : (
            "Update password"
          )}
        </Button>
        <Button variant="ghost" className="w-full" onClick={() => setStep("email")}>
          Back
        </Button>
        {error && <p className="text-center text-sm text-red-500">{error}</p>}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h2 className="text-center text-xl font-bold">Forgot password</h2>
      <p className="text-center text-sm text-[var(--muted-foreground)]">
        Enter your account email and we will send a 6-digit reset code.
      </p>
      <div className="space-y-2">
        <Label htmlFor="forgot-email">Email</Label>
        <Input
          id="forgot-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          autoComplete="email"
        />
      </div>
      <Button
        className="btn-brand w-full"
        disabled={!email.trim() || forgot.isPending}
        onClick={() => {
          setError(null)
          forgot.mutate()
        }}
      >
        {forgot.isPending ? (
          <>
            <Loader2 className="size-4 animate-spin" />
            Sending…
          </>
        ) : (
          "Send reset code"
        )}
      </Button>
      <Button variant="ghost" className="w-full" onClick={onBack}>
        Back to sign in
      </Button>
      {error && <p className="text-center text-sm text-red-500">{error}</p>}
    </div>
  )
}

export function portalPathForRole(role?: string) {
  if (role === "admin") return "/dashboard"
  if (role === "customer") return "/"
  return "/employee/dashboard"
}
