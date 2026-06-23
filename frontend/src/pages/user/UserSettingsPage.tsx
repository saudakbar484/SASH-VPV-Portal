import { useState } from "react"

import { useMutation } from "@tanstack/react-query"

import { CustomerPageHeader } from "@/components/customer/CustomerPageHeader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { endpoints } from "@/lib/api"
import { cn } from "@/lib/utils"

export function UserSettingsPage() {
  const [current, setCurrent] = useState("")
  const [newPw, setNewPw] = useState("")
  const [confirm, setConfirm] = useState("")
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const changePw = useMutation({
    mutationFn: () =>
      endpoints.auth.changePassword({
        current_password: current,
        new_password: newPw,
        confirm_password: confirm,
      }),
    onSuccess: () => {
      setMsg({ ok: true, text: "Password updated." })
      setCurrent("")
      setNewPw("")
      setConfirm("")
    },
    onError: () => setMsg({ ok: false, text: "Password change failed." }),
  })

  const deleteAcc = useMutation({
    mutationFn: endpoints.user.deleteAccount,
    onSuccess: (d) => setMsg({ ok: true, text: d.message }),
  })

  return (
    <div>
      <CustomerPageHeader title="Settings" description="Account security and preferences" />
      <div className="space-y-6">
        <section className="customer-card space-y-3 p-5">
          <h2 className="font-semibold">Change password</h2>
          <div className="space-y-1.5">
            <Label>Current password</Label>
            <Input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>New password</Label>
            <Input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Confirm</Label>
            <Input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          </div>
          <Button className="btn-brand" onClick={() => changePw.mutate()} disabled={changePw.isPending}>
            Update password
          </Button>
        </section>
        <section className="customer-card p-5">
          <h2 className="font-semibold text-red-600">Delete account</h2>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">Request permanent account removal.</p>
          <Button variant="destructive" className="mt-3" onClick={() => deleteAcc.mutate()}>
            Request deletion
          </Button>
        </section>
        {msg && <p className={cn("text-sm", msg.ok ? "text-emerald-600" : "text-red-600")}>{msg.text}</p>}
      </div>
    </div>
  )
}
