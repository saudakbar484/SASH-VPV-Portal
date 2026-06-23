import { useState } from "react"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { Copy, UserPlus } from "lucide-react"

import { GlassPanel } from "@/components/GlassPanel"

import { Button } from "@/components/ui/button"

import { Input } from "@/components/ui/input"

import { Label } from "@/components/ui/label"

import { endpoints } from "@/lib/api"

export function InviteEmployeePanel() {
  const queryClient = useQueryClient()
  const [inviteName, setInviteName] = useState("")
  const [inviteEmail, setInviteEmail] = useState("")
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null)

  const invites = useQuery({
    queryKey: ["admin-invites"],
    queryFn: endpoints.admin.invites,
  })

  const createInvite = useMutation({
    mutationFn: () => endpoints.admin.createInvite({ full_name: inviteName, email: inviteEmail }),
    onSuccess: (data) => {
      setInviteName("")
      setInviteEmail("")
      const url = `${window.location.origin}${data.invite.signup_url}`
      setCopiedUrl(url)
      queryClient.invalidateQueries({ queryKey: ["admin-invites"] })
    },
  })

  return (
    <GlassPanel title="Invite new employee" icon={<UserPlus className="size-5 icon-brand" />}>
      <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto] md:items-end">
        <div>
          <Label>Full name</Label>
          <Input value={inviteName} onChange={(e) => setInviteName(e.target.value)} className="mt-1" />
        </div>
        <div>
          <Label>Work email</Label>
          <Input type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} className="mt-1" />
        </div>
        <Button
          className="btn-brand "
          disabled={!inviteName || !inviteEmail || createInvite.isPending}
          onClick={() => createInvite.mutate()}
        >
          Create invite
        </Button>
      </div>
      {copiedUrl && (
        <div className="mt-3 flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs">
          <code className="flex-1 break-all text-emerald-200">{copiedUrl}</code>
          <Button size="sm" variant="outline" onClick={() => navigator.clipboard.writeText(copiedUrl)}>
            <Copy className="size-3.5" />
            Copy
          </Button>
        </div>
      )}
      {invites.data && invites.data.invites.length > 0 && (
        <div className="mt-4 max-h-32 space-y-1 overflow-y-auto text-xs">
          {invites.data.invites.slice(0, 8).map((inv) => (
            <div key={inv.id} className="flex justify-between rounded border border-white/5 px-2 py-1">
              <span>
                {inv.full_name} · {inv.email}
              </span>
              <span className="capitalize text-[var(--muted-foreground)]">{inv.status}</span>
            </div>
          ))}
        </div>
      )}
    </GlassPanel>
  )
}
