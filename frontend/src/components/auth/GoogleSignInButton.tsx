import { useEffect, useRef, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { GoogleLogin, GoogleOAuthProvider, type CredentialResponse } from "@react-oauth/google"

import { endpoints } from "@/lib/api"

const ENV_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined

type GoogleIntent = "login" | "signup"

function GoogleButton({
  intent,
  onCredential,
  disabled,
  width,
}: {
  intent: GoogleIntent
  onCredential: (credential: string) => void
  disabled?: boolean
  width: number
}) {
  return (
    <div className={disabled ? "pointer-events-none opacity-50" : "flex justify-center"}>
      <GoogleLogin
        onSuccess={(response: CredentialResponse) => {
          if (response.credential) onCredential(response.credential)
        }}
        onError={() => undefined}
        text={intent === "login" ? "signin_with" : "signup_with"}
        shape="rectangular"
        theme="outline"
        size="large"
        width={width}
      />
    </div>
  )
}

export function GoogleSignInButton({
  intent,
  onCredential,
  disabled,
}: {
  intent: GoogleIntent
  onCredential: (credential: string) => void
  disabled?: boolean
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(320)

  const config = useQuery({
    queryKey: ["google-auth-config"],
    queryFn: endpoints.auth.googleConfig,
    staleTime: 60_000,
  })

  const clientId = ENV_CLIENT_ID || config.data?.client_id || ""
  const enabled = Boolean(clientId) && (config.data?.enabled ?? Boolean(ENV_CLIENT_ID))

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const update = () => setWidth(Math.max(240, Math.floor(el.offsetWidth)))
    update()
    const observer = new ResizeObserver(update)
    observer.observe(el)
    return () => observer.disconnect()
  }, [enabled])

  if (config.isLoading) {
    return (
      <div className="h-10 animate-pulse rounded-lg border border-[var(--border)] bg-[var(--accent)]/40" />
    )
  }

  if (!enabled) {
    return (
      <p className="rounded-lg border border-dashed border-[var(--border)] px-3 py-2 text-center text-xs text-[var(--muted-foreground)]">
        Google sign-in is not configured. Add your OAuth JSON to the{" "}
        <span className="font-medium">Google OAuth</span> folder and restart the backend.
      </p>
    )
  }

  return (
    <div ref={containerRef} className="w-full">
      <GoogleOAuthProvider clientId={clientId}>
        <GoogleButton intent={intent} onCredential={onCredential} disabled={disabled} width={width} />
      </GoogleOAuthProvider>
    </div>
  )
}
