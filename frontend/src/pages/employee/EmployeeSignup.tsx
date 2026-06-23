import { useEffect, useState } from "react"

import { Link, useNavigate, useSearchParams } from "react-router-dom"

import { useMutation, useQuery } from "@tanstack/react-query"

import { CheckCircle2, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"

import { Input } from "@/components/ui/input"

import { Label } from "@/components/ui/label"

import { PalmCapturePanel, type PalmSessionStatus } from "@/components/PalmCapturePanel"

import { PalmVeinLogo } from "@/components/PalmVeinLogo"

import { AuthLayout } from "@/components/AuthLayout"

import { EmailVerifyPanel } from "@/components/auth/AuthEmailPanels"

import { endpoints } from "@/lib/api"

import { useAuthStore } from "@/store/useAuthStore"

import { cn } from "@/lib/utils"



type Step = "details" | "palm-setup" | "palm-capture" | "verify-email" | "done"

type Hand = "Left" | "Right"



export function EmployeeSignup() {

  const navigate = useNavigate()

  const [params] = useSearchParams()

  const inviteToken = params.get("invite") ?? ""

  const setAuth = useAuthStore((s) => s.setAuth)



  const [step, setStep] = useState<Step>("details")

  const [verifyEmailAddress, setVerifyEmailAddress] = useState("")

  const [verifyEmailSent, setVerifyEmailSent] = useState(true)

  const [fullName, setFullName] = useState("")

  const [email, setEmail] = useState("")

  const [password, setPassword] = useState("")

  const [confirmPassword, setConfirmPassword] = useState("")

  const [captchaAnswer, setCaptchaAnswer] = useState("")

  const [registerSessionId, setRegisterSessionId] = useState("")

  const [datasetName, setDatasetName] = useState("")

  const [firstHand, setFirstHand] = useState<Hand>("Left")

  const [sessionStatus, setSessionStatus] = useState<PalmSessionStatus | null>(null)



  const invite = useQuery({

    queryKey: ["invite-preview", inviteToken],

    queryFn: () => endpoints.auth.previewInvite(inviteToken),

    enabled: inviteToken.length >= 8,

  })



  useEffect(() => {

    if (invite.data?.valid) {

      setFullName(invite.data.full_name ?? "")

      setEmail(invite.data.email ?? "")

      setDatasetName((invite.data.full_name ?? "").replace(/\s+/g, "_").toLowerCase())

    }

  }, [invite.data])



  const captcha = useQuery({

    queryKey: ["captcha"],

    queryFn: endpoints.auth.captcha,

  })



  const startRegister = useMutation({

    mutationFn: () =>

      endpoints.auth.registerStart({

        full_name: fullName,

        email,

        password,

        confirm_password: confirmPassword,

        captcha_id: captcha.data!.captcha_id,

        captcha_answer: Number(captchaAnswer),

        invite_token: inviteToken,

      }),

    onSuccess: (data) => {

      setRegisterSessionId(data.register_session_id)

      setStep("palm-setup")

    },

  })



  const startPalm = useMutation({

    mutationFn: () =>

      endpoints.auth.registerPalmStart(registerSessionId, firstHand, datasetName),

    onSuccess: (data) => {

      setSessionStatus(data)

      setStep("palm-capture")

    },

  })



  const switchHand = useMutation({

    mutationFn: (next: Hand) => endpoints.auth.registerSwitchHand(registerSessionId, next),

    onSuccess: (data) => setSessionStatus(data),

  })



  const complete = useMutation({

    mutationFn: () => endpoints.auth.registerComplete(registerSessionId),

    onSuccess: (data) => {

      if (data.verification_required) {

        setVerifyEmailAddress(data.email)

        setVerifyEmailSent(data.email_sent ?? true)

        setStep("verify-email")

        return

      }

      if (!data.access_token) return

      setAuth(data.access_token, {

        account_id: data.account_id,

        email: data.email,

        full_name: data.full_name,

        dataset_id: data.dataset_id,

        dataset_name: data.dataset_name,

        role: data.role ?? "employee",

        session_id: data.session_id ?? null,

      })

      setStep("done")

    },

  })



  const completeError =

    complete.isError &&

    (complete.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail



  useEffect(() => {

    if (sessionStatus?.both_complete && !complete.isPending && step === "palm-capture") {

      complete.mutate()

    }

    // eslint-disable-next-line react-hooks/exhaustive-deps

  }, [sessionStatus?.both_complete])



  if (!inviteToken) {

    return (

      <AuthLayout themePortal="employee" className="items-center justify-center p-6">

        <div className="glass-panel max-w-md p-8 text-center">

          <PalmVeinLogo variant="full" height={80} subtitle="Employee" className="mb-4 justify-center" />

          <h1 className="text-xl font-bold">HR invite required</h1>

          <p className="mt-2 text-sm text-[var(--muted-foreground)]">

            Employee registration is invite-only. Ask HR for your personal signup link.

          </p>

          <Button asChild className="mt-4 btn-brand">

            <Link to="/employee/login">Back to login</Link>

          </Button>

        </div>

      </AuthLayout>

    )

  }



  if (invite.isPending) {

    return (

      <AuthLayout themePortal="employee" className="items-center justify-center">

        <Loader2 className="size-8 animate-spin icon-brand" />

      </AuthLayout>

    )

  }



  if (!invite.data?.valid) {

    return (

      <AuthLayout themePortal="employee" className="items-center justify-center p-6">

        <div className="glass-panel max-w-md p-8 text-center">

          <h1 className="text-xl font-bold text-red-300">Invalid invite</h1>

          <p className="mt-2 text-sm text-[var(--muted-foreground)]">

            {invite.data?.message ?? "This invite link is expired or already used."}

          </p>

        </div>

      </AuthLayout>

    )

  }



  return (

    <AuthLayout themePortal="employee" className="items-center justify-center p-6">

      <div className={cn("glass-panel w-full p-8", step === "palm-capture" ? "max-w-3xl" : "max-w-2xl")}>

        <div className="mb-6 flex justify-center">

          <PalmVeinLogo variant="full" height={80} subtitle="Employee" />

        </div>

        <h1 className="-mt-2 mb-2 text-center text-2xl font-bold tracking-widest">Employee Registration</h1>

        <p className="mb-6 text-center text-xs text-emerald-400">HR invite verified</p>



        {step === "details" && (

          <div className="space-y-4">

            <div className="space-y-2">

              <Label>Full name</Label>

              <Input value={fullName} readOnly className="opacity-80" />

            </div>

            <div className="space-y-2">

              <Label>Email address</Label>

              <Input type="email" value={email} readOnly className="opacity-80" />

            </div>

            <div className="grid grid-cols-2 gap-3">

              <div className="space-y-2">

                <Label>Password</Label>

                <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />

              </div>

              <div className="space-y-2">

                <Label>Confirm password</Label>

                <Input

                  type="password"

                  value={confirmPassword}

                  onChange={(e) => setConfirmPassword(e.target.value)}

                />

              </div>

            </div>

            <div className="rounded-lg border border-white/10 bg-white/5 p-4">

              <Label className="text-xs uppercase tracking-wider text-brand-muted">Human verification</Label>

              <p className="mt-1 text-sm">{captcha.data?.question ?? "Loading…"}</p>

              <Input

                className="mt-2"

                type="number"

                placeholder="Your answer"

                value={captchaAnswer}

                onChange={(e) => setCaptchaAnswer(e.target.value)}

              />

            </div>

            <Button

              className="w-full btn-brand "

              size="lg"

              disabled={startRegister.isPending}

              onClick={() => startRegister.mutate()}

            >

              Continue to palm enrollment

            </Button>

          </div>

        )}



        {step === "palm-setup" && (

          <div className="space-y-4">

            <div className="space-y-2">

              <Label>Dataset user name</Label>

              <Input value={datasetName} onChange={(e) => setDatasetName(e.target.value)} />

            </div>

            <div className="space-y-2">

              <Label>Capture first hand</Label>

              <div className="flex gap-2">

                {(["Left", "Right"] as const).map((h) => (

                  <Button

                    key={h}

                    type="button"

                    variant={firstHand === h ? "default" : "outline"}

                    className={cn("flex-1", firstHand === h && "btn-brand")}

                    onClick={() => setFirstHand(h)}

                  >

                    {h}

                  </Button>

                ))}

              </div>

            </div>

            <Button

              className="w-full btn-brand"

              size="lg"

              disabled={!datasetName.trim() || startPalm.isPending}

              onClick={() => startPalm.mutate()}

            >

              Open scanner & start captures

            </Button>

          </div>

        )}



        {step === "palm-capture" && sessionStatus && registerSessionId && (

          <div className="space-y-4">

            <PalmCapturePanel

              registerSessionId={registerSessionId}

              sessionStatus={sessionStatus}

              onStatusChange={setSessionStatus}

              onSwitchHand={(h) => switchHand.mutate(h)}

              switchHandPending={switchHand.isPending}

            />

            {complete.isPending && (

              <div className="flex items-center justify-center gap-2 text-sm text-brand-muted">

                <Loader2 className="size-4 animate-spin" />

                Saving registration…

              </div>

            )}

            {completeError && (

              <Button variant="outline" size="sm" onClick={() => complete.mutate()}>

                Retry finalize

              </Button>

            )}

          </div>

        )}



        {step === "verify-email" && (

          <EmailVerifyPanel

            email={verifyEmailAddress}

            emailSent={verifyEmailSent}

            onVerified={(data) => {

              setAuth(data.access_token, { ...data.user, role: "employee" })

              setStep("done")

            }}

          />

        )}



        {step === "done" && (

          <div className="text-center">

            <CheckCircle2 className="mx-auto size-12 text-emerald-400" />

            <p className="mt-4 font-medium">Welcome aboard!</p>

            <Button className="mt-4 btn-brand" onClick={() => navigate("/employee/dashboard")}>

              Go to Employee Home

            </Button>

          </div>

        )}



        <p className="mt-6 text-center text-sm text-[var(--muted-foreground)]">

          Already registered?{" "}

          <Link to="/employee/login" className="icon-brand hover:underline">

            Sign in

          </Link>

        </p>

      </div>

    </AuthLayout>

  )

}


