import { useEffect, useMemo, useState } from "react"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { Bell, Mail, Send } from "lucide-react"

import { GlassPanel } from "@/components/GlassPanel"

import { Badge } from "@/components/ui/badge"

import { Button } from "@/components/ui/button"

import { Label } from "@/components/ui/label"

import { endpoints } from "@/lib/api"

import { cn } from "@/lib/utils"

const REASON_LABELS: Record<string, string> = {
  smtp_not_configured: "Add SMTP_PASSWORD to .env and restart the backend.",
  smtp_auth_failed:
    "Brevo rejected the SMTP login. Regenerate the SMTP key (xsmtpsib-...) in Brevo → SMTP & API → SMTP and update .env.",
  smtp_ip_blocked:
    "Brevo blocked this server's IP. In Brevo go to SMTP & API → SMTP → disable IP restriction, or add your public IP under Security → Authorized IPs.",
  no_recipient: "No administrator email found.",
  send_failed:
    "SMTP send failed. Verify saudakbar65367@gmail.com is verified as a sender in Brevo, then check backend logs.",
  no_admin_email: "No administrator account email found.",
}

export function EmailNotificationsPanel() {
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState({
    notify_absent: false,
    notify_weekly_summary: false,
  })
  const [saveMsg, setSaveMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [actionMsg, setActionMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const notifications = useQuery({
    queryKey: ["admin-notification-settings"],
    queryFn: endpoints.admin.notificationSettings,
  })

  const attendanceSettings = useQuery({
    queryKey: ["admin-attendance-settings"],
    queryFn: endpoints.admin.attendanceSettings,
  })

  useEffect(() => {
    if (notifications.data) {
      setDraft({
        notify_absent: notifications.data.notify_absent,
        notify_weekly_summary: notifications.data.notify_weekly_summary,
      })
    }
  }, [notifications.data])

  const dirty = useMemo(() => {
    if (!notifications.data) return false
    return (
      draft.notify_absent !== notifications.data.notify_absent ||
      draft.notify_weekly_summary !== notifications.data.notify_weekly_summary
    )
  }, [draft, notifications.data])

  const save = useMutation({
    mutationFn: () =>
      endpoints.admin.updateAttendanceSettings({
        notify_absent: draft.notify_absent,
        notify_weekly_summary: draft.notify_weekly_summary,
      }),
    onSuccess: () => {
      setSaveMsg({ ok: true, text: "Notification settings saved." })
      queryClient.invalidateQueries({ queryKey: ["admin-notification-settings"] })
      queryClient.invalidateQueries({ queryKey: ["admin-attendance-settings"] })
    },
    onError: () => setSaveMsg({ ok: false, text: "Could not save settings. Try again." }),
  })

  const testEmail = useMutation({
    mutationFn: () => endpoints.admin.testNotificationEmail(),
    onSuccess: (data) => {
      if (data.sent) {
        setActionMsg({ ok: true, text: `Test email sent to ${data.to}.` })
      } else {
        const detail = data.reason ? REASON_LABELS[data.reason] ?? data.reason : "Test email was not sent."
        setActionMsg({ ok: false, text: detail })
      }
      queryClient.invalidateQueries({ queryKey: ["admin-notification-settings"] })
    },
    onError: () => setActionMsg({ ok: false, text: "Test email request failed." }),
  })

  const weeklySummary = useMutation({
    mutationFn: endpoints.admin.sendWeeklySummary,
    onSuccess: (data) => {
      if (data.sent) {
        setActionMsg({
          ok: true,
          text: `Weekly summary sent to ${data.to}${data.date_from && data.date_to ? ` (${data.date_from} – ${data.date_to})` : ""}.`,
        })
      } else {
        const detail = data.reason ? REASON_LABELS[data.reason] ?? data.reason : "Weekly summary was not sent."
        setActionMsg({ ok: false, text: detail })
      }
    },
    onError: () => setActionMsg({ ok: false, text: "Could not send weekly summary." }),
  })

  const n = notifications.data
  const hrEmail = n?.resolved_recipient ?? n?.admin_notify_email ?? "—"

  return (
    <GlassPanel
      title="Email & notifications"
      description="HR alerts and attendance summaries use the primary administrator email"
      icon={<Bell className="size-5 icon-brand" />}
    >
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="space-y-5">
          <div className="rounded-lg border border-[var(--border)] bg-[var(--accent)]/10 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                SMTP delivery
              </span>
              <Badge
                variant="outline"
                className={cn(
                  n?.smtp_configured
                    ? "border-emerald-500/40 text-emerald-400"
                    : "border-amber-500/40 text-amber-400",
                )}
              >
                {n?.smtp_configured ? "Ready" : n?.smtp_password_set ? "Misconfigured" : "Password required"}
              </Badge>
            </div>
            <dl className="mt-3 space-y-1 text-xs text-[var(--muted-foreground)]">
              {n?.smtp_host && (
                <div className="flex justify-between gap-2">
                  <dt>Server</dt>
                  <dd className="font-mono text-[var(--foreground)]">{n.smtp_host}</dd>
                </div>
              )}
              {n?.smtp_from && (
                <div className="flex justify-between gap-2">
                  <dt>From address</dt>
                  <dd className="font-mono text-[var(--foreground)]">{n.smtp_from}</dd>
                </div>
              )}
            </dl>
            {!n?.smtp_configured && (
              <p className="mt-2 text-xs leading-relaxed text-amber-400">
                Add your Brevo <span className="font-mono">SMTP_PASSWORD</span> (SMTP key from Brevo → SMTP
                &amp; API → SMTP) to <span className="font-mono">.env</span> and restart the backend.
              </p>
            )}
          </div>

          <div className="rounded-lg border border-[var(--border)] p-4">
            <Label>HR / admin recipient</Label>
            <p className="mt-1.5 font-mono text-sm font-medium">{hrEmail}</p>
            <p className="mt-1.5 text-xs text-[var(--muted-foreground)]">
              Weekly summaries and test emails always go to the primary administrator account.
            </p>
          </div>

          <div className="space-y-3 rounded-lg border border-[var(--border)] p-4">
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                className="mt-1"
                checked={draft.notify_absent}
                onChange={(e) => {
                  setSaveMsg(null)
                  setDraft((s) => ({ ...s, notify_absent: e.target.checked }))
                }}
              />
              <span>
                <span className="block text-sm font-medium">Email employees when marked absent</span>
                <span className="mt-0.5 block text-xs text-[var(--muted-foreground)]">
                  Sends after end-of-day processing when an employee had no check-in for that work date.
                </span>
              </span>
            </label>
            <label className="flex cursor-pointer items-start gap-3">
              <input
                type="checkbox"
                className="mt-1"
                checked={draft.notify_weekly_summary}
                onChange={(e) => {
                  setSaveMsg(null)
                  setDraft((s) => ({ ...s, notify_weekly_summary: e.target.checked }))
                }}
              />
              <span>
                <span className="block text-sm font-medium">Auto weekly summary (Mondays)</span>
                <span className="mt-0.5 block text-xs text-[var(--muted-foreground)]">
                  Automatically emails the administrator when attendance days are closed on Monday.
                </span>
              </span>
            </label>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              className="btn-brand "
              disabled={save.isPending || !dirty}
              onClick={() => save.mutate()}
            >
              Save notification settings
            </Button>
            <Button
              variant="outline"
              className="gap-2"
              disabled={testEmail.isPending}
              onClick={() => {
                setActionMsg(null)
                testEmail.mutate()
              }}
            >
              <Mail className="size-4" />
              Send test email
            </Button>
            <Button
              variant="outline"
              className="gap-2"
              disabled={weeklySummary.isPending}
              onClick={() => {
                setActionMsg(null)
                weeklySummary.mutate()
              }}
            >
              <Send className="size-4" />
              Send weekly summary now
            </Button>
          </div>

          {saveMsg && (
            <p className={cn("text-xs", saveMsg.ok ? "text-emerald-400" : "text-red-400")}>{saveMsg.text}</p>
          )}
          {actionMsg && (
            <p className={cn("text-xs", actionMsg.ok ? "text-emerald-400" : "text-amber-400")}>{actionMsg.text}</p>
          )}
        </div>

        <aside className="space-y-3 text-sm">
          <div className="rounded-lg border border-[var(--border)] p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-brand-muted">Delivery preview</h3>
            <dl className="mt-3 space-y-2 text-xs">
              <div>
                <dt className="text-[var(--muted-foreground)]">HR recipient</dt>
                <dd className="mt-0.5 break-all font-medium">{hrEmail}</dd>
              </div>
              <div>
                <dt className="text-[var(--muted-foreground)]">Absent notices</dt>
                <dd className="mt-0.5 font-medium">
                  {draft.notify_absent ? "Each employee's work email" : "Disabled"}
                </dd>
              </div>
              <div>
                <dt className="text-[var(--muted-foreground)]">Auto summary</dt>
                <dd className="mt-0.5 font-medium">
                  {draft.notify_weekly_summary ? "Mondays after close-day" : "Manual only"}
                </dd>
              </div>
              {attendanceSettings.data && (
                <div>
                  <dt className="text-[var(--muted-foreground)]">Report timezone</dt>
                  <dd className="mt-0.5 font-mono">{attendanceSettings.data.timezone}</dd>
                </div>
              )}
            </dl>
          </div>
        </aside>
      </div>
    </GlassPanel>
  )
}
