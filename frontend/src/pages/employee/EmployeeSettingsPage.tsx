import { useState } from "react"

import { useMutation, useQuery } from "@tanstack/react-query"

import {
  Building2,
  Fingerprint,
  Lock,
  Shield,
  User,
} from "lucide-react"

import { EmployeePageHeader } from "@/components/employee/EmployeePageHeader"

import { EmployeePanel } from "@/components/employee/EmployeePanel"

import { Badge } from "@/components/ui/badge"

import { Button } from "@/components/ui/button"

import { Input } from "@/components/ui/input"

import { Label } from "@/components/ui/label"

import { endpoints } from "@/lib/api"

import { cn } from "@/lib/utils"

export function EmployeeSettingsPage() {
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [passwordMsg, setPasswordMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const profile = useQuery({
    queryKey: ["employee-profile"],
    queryFn: endpoints.employee.profile,
  })

  const policy = useQuery({
    queryKey: ["employee-company-policy"],
    queryFn: endpoints.employee.companyPolicy,
  })

  const changePassword = useMutation({
    mutationFn: () =>
      endpoints.auth.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
    onSuccess: () => {
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
      setPasswordMsg({ ok: true, text: "Password updated successfully." })
    },
    onError: () =>
      setPasswordMsg({ ok: false, text: "Could not update password. Check your current password." }),
  })

  const p = profile.data
  const pol = policy.data

  return (
    <div className="space-y-5 sm:space-y-6">
      <EmployeePageHeader
        title="Settings"
        description="Account profile, security, and company attendance rules."
      />

      <div className="grid gap-4 lg:grid-cols-2 lg:gap-5">
        <EmployeePanel title="Account profile" description="Your workplace identity" icon={<User className="size-4" />}>
          {p ? (
            <dl className="grid gap-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-xs text-[var(--muted-foreground)]">Full name</dt>
                <dd className="mt-1 font-semibold">{p.full_name}</dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--muted-foreground)]">Work email</dt>
                <dd className="mt-1 break-all font-medium">{p.email}</dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--muted-foreground)]">Employee ID</dt>
                <dd className="mt-1 font-mono">{p.dataset_id}</dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--muted-foreground)]">Registered</dt>
                <dd className="mt-1">{new Date(p.registered_at).toLocaleDateString()}</dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--muted-foreground)]">Role</dt>
                <dd className="mt-1 capitalize">{p.role}</dd>
              </div>
              <div>
                <dt className="text-xs text-[var(--muted-foreground)]">Biometric ID</dt>
                <dd className="mt-1 font-mono text-xs">{p.dataset_name}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-[var(--muted-foreground)]">Loading profile…</p>
          )}
        </EmployeePanel>

        <EmployeePanel
          title="Palm enrollment"
          description="Hands registered for sign-in and sign-out"
          icon={<Fingerprint className="size-4" />}
        >
          {p ? (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-3">
                <Badge
                  variant="outline"
                  className={cn(
                    "px-3 py-1.5",
                    p.left_enrolled
                      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                      : "",
                  )}
                >
                  Left hand {p.left_enrolled ? "✓ Enrolled" : "— Not enrolled"}
                </Badge>
                <Badge
                  variant="outline"
                  className={cn(
                    "px-3 py-1.5",
                    p.right_enrolled
                      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                      : "",
                  )}
                >
                  Right hand {p.right_enrolled ? "✓ Enrolled" : "— Not enrolled"}
                </Badge>
              </div>
              <p className="text-xs leading-relaxed text-[var(--muted-foreground)]">
                Palm templates are managed during onboarding. Contact HR if you need to re-enroll a hand.
              </p>
            </div>
          ) : null}
        </EmployeePanel>

        <EmployeePanel
          title="Company attendance policy"
          description="Rules set by your organization"
          icon={<Building2 className="size-4" />}
        >
          {pol ? (
            <dl className="space-y-3 text-sm">
              {[
                ["Work day starts", pol.work_day_start],
                ["Grace period", `${pol.grace_minutes} minutes`],
                ["Half-day threshold", `Less than ${pol.half_day_hours} hours on site`],
                ["Timezone", pol.timezone],
                ["Weekends excluded", pol.exclude_weekends ? "Yes" : "No"],
                ["Palm logout required", pol.require_palm_logout ? "Yes" : "No"],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between gap-4 border-b border-[var(--border)] pb-2 last:border-0">
                  <dt className="text-[var(--muted-foreground)]">{label}</dt>
                  <dd className="text-right font-medium">{value}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="text-sm text-[var(--muted-foreground)]">Loading company policy…</p>
          )}
          <p className="mt-4 text-xs text-[var(--muted-foreground)]">
            These settings are managed by HR in the admin console. Contact your administrator to request changes.
          </p>
        </EmployeePanel>

        <EmployeePanel
          className="lg:col-span-2"
          title="Security"
          description="Update your sign-in password"
          icon={<Shield className="size-4" />}
        >
          <div className="mx-auto grid max-w-md gap-4">
            <div>
              <Label htmlFor="cur-pw">Current password</Label>
              <Input
                id="cur-pw"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="mt-1.5"
                autoComplete="current-password"
              />
            </div>
            <div>
              <Label htmlFor="new-pw">New password</Label>
              <Input
                id="new-pw"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="mt-1.5"
                autoComplete="new-password"
              />
            </div>
            <div>
              <Label htmlFor="confirm-pw">Confirm new password</Label>
              <Input
                id="confirm-pw"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="mt-1.5"
                autoComplete="new-password"
              />
            </div>
            <Button
              className="w-fit gap-2 btn-brand"
              disabled={
                !currentPassword ||
                !newPassword ||
                newPassword !== confirmPassword ||
                changePassword.isPending
              }
              onClick={() => changePassword.mutate()}
            >
              <Lock className="size-4" />
              Update password
            </Button>
            {passwordMsg && (
              <p className={cn("text-xs", passwordMsg.ok ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400")}>
                {passwordMsg.text}
              </p>
            )}
          </div>
        </EmployeePanel>
      </div>
    </div>
  )
}
