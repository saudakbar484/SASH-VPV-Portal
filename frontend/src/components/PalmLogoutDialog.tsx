import { useState } from "react"

import { useMutation } from "@tanstack/react-query"

import { Loader2, ScanFace } from "lucide-react"

import { Button } from "@/components/ui/button"

import {

  Dialog,

  DialogContent,

  DialogDescription,

  DialogFooter,

  DialogHeader,

  DialogTitle,

} from "@/components/ui/dialog"

import { Input } from "@/components/ui/input"

import { Label } from "@/components/ui/label"

import { LiveFeed } from "@/components/LiveFeed"

import { LiveFeedToolbar } from "@/components/LiveFeedToolbar"

import { endpoints } from "@/lib/api"

import { useAuthStore } from "@/store/useAuthStore"



interface PalmLogoutDialogProps {

  open: boolean

  onOpenChange: (open: boolean) => void

  onLoggedOut: () => void

}



export function PalmLogoutDialog({ open, onOpenChange, onLoggedOut }: PalmLogoutDialogProps) {

  const user = useAuthStore((s) => s.user)

  const clearAuth = useAuthStore((s) => s.clearAuth)

  const [showFallback, setShowFallback] = useState(false)

  const [password, setPassword] = useState("")

  const [error, setError] = useState<string | null>(null)



  const palmLogout = useMutation({

    mutationFn: () => endpoints.auth.logoutPalm(user?.session_id),

    onSuccess: (data) => {

      if (data.matched && data.success) {

        clearAuth()

        onOpenChange(false)

        onLoggedOut()

        return

      }

      setError(data.message ?? "Palm did not match — try again")

    },

    onError: () => setError("Logout scan failed — check scanner connection"),

  })



  const emailLogout = useMutation({

    mutationFn: () =>

      endpoints.auth.logout({

        session_id: user?.session_id,

        email_fallback: true,

        password,

      }),

    onSuccess: () => {

      clearAuth()

      onOpenChange(false)

      onLoggedOut()

    },

    onError: () => setError("Password incorrect or logout failed"),

  })



  return (

    <Dialog open={open} onOpenChange={onOpenChange}>

      <DialogContent className="max-w-md border-white/10 bg-[#120a1c]">

        <DialogHeader>

          <DialogTitle>Confirm sign out</DialogTitle>

          <DialogDescription>

            Scan your palm to verify it is you before ending your session.

          </DialogDescription>

        </DialogHeader>



        {!showFallback ? (

          <div className="space-y-3">

            <LiveFeedToolbar showLiveBadge={false} />

            <LiveFeed size="standard" />

            {error && <p className="text-sm text-red-300">{error}</p>}

            <Button

              className="w-full btn-brand "

              onClick={() => {

                setError(null)

                palmLogout.mutate()

              }}

              disabled={palmLogout.isPending}

            >

              {palmLogout.isPending ? (

                <Loader2 className="size-4 animate-spin" />

              ) : (

                <ScanFace className="size-4" />

              )}

              Scan palm to sign out

            </Button>

            <button

              type="button"

              className="w-full text-center text-xs text-[var(--muted-foreground)] underline"

              onClick={() => setShowFallback(true)}

            >

              Scanner not working? Use password instead

            </button>

          </div>

        ) : (

          <div className="space-y-3">

            <div>

              <Label htmlFor="logout-pw">Password</Label>

              <Input

                id="logout-pw"

                type="password"

                value={password}

                onChange={(e) => setPassword(e.target.value)}

                className="mt-1"

              />

            </div>

            {error && <p className="text-sm text-red-300">{error}</p>}

            <Button

              className="w-full"

              variant="outline"

              onClick={() => emailLogout.mutate()}

              disabled={!password || emailLogout.isPending}

            >

              Sign out with password

            </Button>

            <button

              type="button"

              className="w-full text-center text-xs text-brand-muted underline"

              onClick={() => setShowFallback(false)}

            >

              Back to palm scan

            </button>

          </div>

        )}



        <DialogFooter>

          <Button variant="ghost" onClick={() => onOpenChange(false)}>

            Cancel

          </Button>

        </DialogFooter>

      </DialogContent>

    </Dialog>

  )

}


