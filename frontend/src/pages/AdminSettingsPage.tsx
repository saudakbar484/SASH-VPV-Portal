import { useState } from "react"

import { Link } from "react-router-dom"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {

  ArrowRight,
  Building2,

  Cpu,

  Fingerprint,

  Lock,

  Monitor,

  RefreshCw,

  ScanLine,

  Server,

  Shield,

  User,

} from "lucide-react"

import { AdminPageHeader } from "@/components/AdminPageHeader"
import { EmailNotificationsPanel } from "@/components/admin/EmailNotificationsPanel"
import { ModelTrainingPanel } from "@/components/admin/ModelTrainingPanel"
import { GlassPanel } from "@/components/GlassPanel"

import { Badge } from "@/components/ui/badge"

import { Button } from "@/components/ui/button"

import { Input } from "@/components/ui/input"

import { Label } from "@/components/ui/label"

import { api, endpoints } from "@/lib/api"

import { cn } from "@/lib/utils"

function SettingsRow({ label, value }: { label: string; value: React.ReactNode }) {

  return (

    <div className="admin-settings-row text-sm">

      <dt className="text-[var(--muted-foreground)]">{label}</dt>

      <dd className="text-right font-medium">{value}</dd>

    </div>

  )

}



export function AdminSettingsPage() {

  const queryClient = useQueryClient()



  const [currentPassword, setCurrentPassword] = useState("")

  const [newPassword, setNewPassword] = useState("")

  const [confirmPassword, setConfirmPassword] = useState("")

  const [passwordMsg, setPasswordMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const [deviceMsg, setDeviceMsg] = useState<string | null>(null)



  const profile = useQuery({

    queryKey: ["auth-me"],

    queryFn: endpoints.auth.me,

  })



  const attendanceSettings = useQuery({

    queryKey: ["admin-attendance-settings"],

    queryFn: endpoints.admin.attendanceSettings,

  })



  const holidays = useQuery({

    queryKey: ["admin-holidays"],

    queryFn: endpoints.admin.holidays,

  })

  const device = useQuery({

    queryKey: ["device-status"],

    queryFn: endpoints.device.status,

    refetchInterval: 5000,

  })



  const hardware = useQuery({

    queryKey: ["hardware-info"],

    queryFn: endpoints.hardware.info,

    refetchInterval: 10000,

    enabled: !!device.data?.connected,

  })



  const stats = useQuery({

    queryKey: ["dashboard-stats"],

    queryFn: endpoints.dashboard.stats,

    refetchInterval: 10000,

  })



  const health = useQuery({

    queryKey: ["api-health"],

    queryFn: () => api.get<{ status: string; service: string }>("/api/health").then((r) => r.data),

    refetchInterval: 30000,

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



  const reconnectDevice = useMutation({

    mutationFn: endpoints.device.reconnect,

    onSuccess: () => {

      setDeviceMsg("Scanner reconnect requested.")

      queryClient.invalidateQueries({ queryKey: ["device-status"] })

      queryClient.invalidateQueries({ queryKey: ["hardware-info"] })

      queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] })

    },

    onError: () => setDeviceMsg("Reconnect failed. Check USB connection and driver."),

  })



  const initDevice = useMutation({

    mutationFn: endpoints.device.init,

    onSuccess: () => {

      setDeviceMsg("Device initialization started.")

      queryClient.invalidateQueries({ queryKey: ["device-status"] })

    },

    onError: () => setDeviceMsg("Could not initialize device."),

  })



  const p = profile.data

  const pol = attendanceSettings.data

  const connected = !!device.data?.connected

  return (

    <div className="space-y-6">

      <AdminPageHeader

        title="Settings"

        description="Administrator account, security, company policy overview, notifications, and system health."

      />



      <div className="grid gap-6 lg:grid-cols-2">

        <GlassPanel title="Administrator account" icon={<User className="size-5 icon-brand" />}>

          {p ? (

            <dl className="space-y-3">

              <SettingsRow label="Full name" value={p.full_name} />

              <SettingsRow label="Email" value={<span className="break-all">{p.email}</span>} />

              <SettingsRow

                label="Role"

                value={

                  <Badge variant="outline" className="border-emerald-500/40 text-emerald-400 capitalize">

                    {p.role ?? "admin"}

                  </Badge>

                }

              />

              <SettingsRow label="Account ID" value={<span className="font-mono">{p.account_id}</span>} />

              <SettingsRow label="Dataset ID" value={<span className="font-mono">{p.dataset_id}</span>} />

              <SettingsRow label="Biometric ID" value={<span className="font-mono text-xs">{p.dataset_name}</span>} />

            </dl>

          ) : (

            <p className="text-sm text-[var(--muted-foreground)]">Loading profile…</p>

          )}

        </GlassPanel>

        <GlassPanel title="Security" icon={<Shield className="size-5 icon-brand" />}>

        <p className="mb-4 max-w-2xl text-sm text-[var(--muted-foreground)]">

          Update your administrator sign-in password. Use at least 8 characters with a mix of letters and numbers.

        </p>

        <div className="grid max-w-md gap-4">

          <div>

            <Label htmlFor="admin-cur-pw">Current password</Label>

            <Input

              id="admin-cur-pw"

              type="password"

              value={currentPassword}

              onChange={(e) => setCurrentPassword(e.target.value)}

              className="mt-1.5"

              autoComplete="current-password"

            />

          </div>

          <div>

            <Label htmlFor="admin-new-pw">New password</Label>

            <Input

              id="admin-new-pw"

              type="password"

              value={newPassword}

              onChange={(e) => setNewPassword(e.target.value)}

              className="mt-1.5"

              autoComplete="new-password"

            />

          </div>

          <div>

            <Label htmlFor="admin-confirm-pw">Confirm new password</Label>

            <Input

              id="admin-confirm-pw"

              type="password"

              value={confirmPassword}

              onChange={(e) => setConfirmPassword(e.target.value)}

              className="mt-1.5"

              autoComplete="new-password"

            />

          </div>

          <Button

            className="w-fit gap-2 btn-brand "

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

            <p className={cn("text-xs", passwordMsg.ok ? "text-emerald-400" : "text-red-400")}>

              {passwordMsg.text}

            </p>

          )}

        </div>

      </GlassPanel>

      </div>



      <GlassPanel
          title="Company & attendance policy"
          description="Configured on the dashboard — summary below"
          icon={<Building2 className="size-5 icon-brand" />}
          headerExtra={
            <Link
              to="/dashboard"
              className="inline-flex shrink-0 items-center gap-1 text-xs font-medium icon-brand hover:text-brand-muted"
            >
              Edit on dashboard
              <ArrowRight className="size-3.5" />
            </Link>
          }
        >
          {pol ? (
            <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <SettingsRow label="Work day starts" value={pol.work_day_start} />
              <SettingsRow label="Grace period" value={`${pol.grace_minutes} minutes`} />
              <SettingsRow label="Half-day threshold" value={`${pol.half_day_hours} hours`} />
              <SettingsRow label="Timezone" value={pol.timezone} />
              <SettingsRow label="Exclude weekends" value={pol.exclude_weekends ? "Yes" : "No"} />
              <SettingsRow label="Require palm logout" value={pol.require_palm_logout ? "Yes" : "No"} />
              <SettingsRow label="Holidays configured" value={String(holidays.data?.holidays.length ?? 0)} />
            </dl>
          ) : (
            <p className="text-sm text-[var(--muted-foreground)]">Loading policy…</p>
          )}
        </GlassPanel>

      <EmailNotificationsPanel />

      <ModelTrainingPanel />

      <GlassPanel title="Scanner & hardware" icon={<ScanLine className="size-5 icon-brand" />}>

        <div className="grid gap-6 lg:grid-cols-2">

          <dl className="space-y-3">

            <SettingsRow

              label="Scanner status"

              value={

                <Badge

                  variant="outline"

                  className={cn(

                    connected ? "border-emerald-500/40 text-emerald-400" : "border-red-500/40 text-red-400",

                  )}

                >

                  {connected ? "Connected" : "Offline"}

                </Badge>

              }

            />

            <SettingsRow label="Status message" value={stats.data?.scanner_message ?? "—"} />

            <SettingsRow label="SDK loaded" value={device.data?.loaded ? "Yes" : "No"} />

            <SettingsRow label="Image size" value={device.data?.img_size ?? stats.data?.image_resolution ?? "—"} />

            <SettingsRow

              label="Feature vector"

              value={

                device.data?.feat_size != null

                  ? `${device.data.feat_size} bytes`

                  : stats.data?.feature_size != null

                    ? `${stats.data.feature_size} bytes`

                    : "—"

              }

            />

            {hardware.data && (

              <>

                <SettingsRow label="Serial" value={hardware.data.serial ?? "—"} />

                <SettingsRow label="Firmware" value={hardware.data.fw_version ?? "—"} />

                <SettingsRow label="SDK version" value={hardware.data.sdk_version ?? "—"} />

              </>

            )}

          </dl>

          <div className="space-y-3">

            <p className="text-sm text-[var(--muted-foreground)]">

              If the palm scanner is unplugged or shows offline, reconnect USB and use the actions below. Ensure the

              Zadig WinUSB driver is installed for the XRTECH device.

            </p>

            <div className="flex flex-wrap gap-2">

              <Button

                variant="outline"

                className="gap-2"

                disabled={reconnectDevice.isPending}

                onClick={() => reconnectDevice.mutate()}

              >

                <RefreshCw className={cn("size-4", reconnectDevice.isPending && "animate-spin")} />

                Reconnect scanner

              </Button>

              {!connected && (

                <Button

                  className="gap-2 btn-brand "

                  disabled={initDevice.isPending}

                  onClick={() => initDevice.mutate()}

                >

                  Initialize device

                </Button>

              )}

            </div>

            {deviceMsg && <p className="text-xs text-[var(--muted-foreground)]">{deviceMsg}</p>}

          </div>

        </div>

      </GlassPanel>



      <div className="grid gap-6 lg:grid-cols-2">

        <GlassPanel title="Recognition & dataset" icon={<Fingerprint className="size-5 icon-brand" />}>

          <dl className="space-y-3">

            <SettingsRow label="Enrolled persons" value={String(stats.data?.enrolled_persons ?? 0)} />

            <SettingsRow label="Dataset classes" value={String(stats.data?.dataset_classes ?? 0)} />

            <SettingsRow label="Image resolution" value={stats.data?.image_resolution ?? "480×640"} />

            <SettingsRow

              label="Recognition logging"

              value={

                <Badge variant="outline" className="border-emerald-500/40 text-emerald-400">

                  Enabled

                </Badge>

              }

            />

          </dl>

          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              to="/identities"
              className="inline-flex h-8 items-center rounded-md border border-[var(--border)] px-3 text-xs font-medium transition hover:bg-[var(--accent)]"
            >
              View identities
            </Link>
            <Link
              to="/logs"
              className="inline-flex h-8 items-center rounded-md border border-[var(--border)] px-3 text-xs font-medium transition hover:bg-[var(--accent)]"
            >
              Recognition logs
            </Link>
          </div>
        </GlassPanel>

        <GlassPanel title="System health" icon={<Server className="size-5 icon-brand" />}>

          <dl className="space-y-3">

            <SettingsRow

              label="API status"

              value={

                <Badge

                  variant="outline"

                  className={cn(

                    health.data?.status === "ok"

                      ? "border-emerald-500/40 text-emerald-400"

                      : "border-amber-500/40 text-amber-400",

                  )}

                >

                  {health.data?.status === "ok" ? "Healthy" : health.isLoading ? "Checking…" : "Unavailable"}

                </Badge>

              }

            />

            <SettingsRow label="Backend service" value={health.data?.service ?? "—"} />

            <SettingsRow

              label="Admin session"

              value={p?.session_id != null ? `Active (#${p.session_id})` : "Password session"}

            />

          </dl>

          <p className="mt-4 flex items-start gap-2 text-xs text-[var(--muted-foreground)]">

            <Cpu className="mt-0.5 size-3.5 shrink-0" />

            Matcher and FAISS index load on backend startup. Restart the server after model or dataset changes.

          </p>

        </GlassPanel>

      </div>



      <GlassPanel title="Quick navigation" icon={<Monitor className="size-5 icon-brand" />}>

        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">

          {[

            { to: "/dashboard", label: "Dashboard", desc: "Policy, holidays & invites" },

            { to: "/employees", label: "Employees", desc: "Reports & staff records" },

            { to: "/enroll", label: "Enrollment", desc: "Capture palm templates" },

            { to: "/kiosk", label: "Auth kiosk", desc: "Public sign-in terminal" },

          ].map(({ to, label, desc }) => (

            <Link

              key={to}

              to={to}

              className="quick-action-link"

            >

              <div className="text-sm font-medium">{label}</div>

              <div className="text-xs text-[var(--muted-foreground)]">{desc}</div>

            </Link>

          ))}

        </div>

      </GlassPanel>

    </div>

  )

}


