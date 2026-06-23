import { Link } from "react-router-dom"

import { useQuery } from "@tanstack/react-query"

import { AdminPageHeader } from "@/components/AdminPageHeader"

import { CompanyAttendanceSettingsPanel } from "@/components/admin/CompanyAttendanceSettingsPanel"

import { HolidayCalendarPanel } from "@/components/admin/HolidayCalendarPanel"

import { InviteEmployeePanel } from "@/components/admin/InviteEmployeePanel"

import { endpoints } from "@/lib/api"

import { cn } from "@/lib/utils"



export function Dashboard() {

  const stats = useQuery({

    queryKey: ["dashboard-stats"],

    queryFn: endpoints.dashboard.stats,

    refetchInterval: 3000,

  })

  const device = useQuery({

    queryKey: ["device-status"],

    queryFn: endpoints.device.status,

    refetchInterval: 2000,

  })



  const connected = !!device.data?.connected



  return (

    <div className="space-y-6">

      <AdminPageHeader

        title="Operations Dashboard"

        description="Company attendance policy, holidays, employee invites, and quick access to enrollment tools."

      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">

        <StatCard

          label="Scanner Status"

          value={stats.data?.scanner_message ?? "—"}

          sub={connected ? "1 device detected" : "Check connection"}

          accent={connected ? "green" : "muted"}

        />

        <StatCard

          label="Enrolled Persons"

          value={String(stats.data?.enrolled_persons ?? 0)}

          sub={`${stats.data?.dataset_classes ?? 0} in dataset`}

          accent="purple"

        />

        <StatCard

          label="Image Resolution"

          value={stats.data?.image_resolution ?? "480×640"}

          sub="Portrait mode, grayscale"

          accent="muted"

        />

      </div>



      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">

        <div className="space-y-6">

          <CompanyAttendanceSettingsPanel />

          <HolidayCalendarPanel />

          <InviteEmployeePanel />

        </div>



        <div className="space-y-4">

          <div className="glass-panel p-5">

            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-brand-muted">

              Device Info

            </h3>

            <dl className="space-y-2 text-sm">

              <InfoRow label="Status" value={connected ? "Connected" : "Offline"} ok={connected} />

              <InfoRow label="Power" value={connected ? "Active" : "Standby"} />

              <InfoRow label="Image" value="480×640" />

              <InfoRow

                label="Feature"

                value={stats.data?.feature_size ? `${stats.data.feature_size}B` : "560B"}

              />

            </dl>

          </div>



          <div className="glass-panel p-5">

            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-brand-muted">

              Quick Actions

            </h3>

            <div className="space-y-2">

              <QuickAction to="/enroll" title="Enroll User" desc="Capture palm vein images" />

              <QuickAction to="/recognize" title="Scan & Identify" desc="Match against full dataset" />

              <QuickAction to="/kiosk" title="Auth Kiosk" desc="Public palm authentication terminal" />

              <QuickAction to="/identities" title="View Identities" desc="Browse all enrolled persons" />

              <QuickAction to="/employees" title="Manage Employees" desc="Attendance reports and staff records" />

            </div>

          </div>

        </div>

      </div>

    </div>

  )

}



function StatCard({

  label,

  value,

  sub,

  accent,

}: {

  label: string

  value: string

  sub: string

  accent: "green" | "purple" | "muted"

}) {

  const valueClass =

    accent === "green"

      ? "text-emerald-400"

      : accent === "purple"

        ? "text-brand-muted"

        : "text-[var(--foreground)]"

  return (

    <div className="glass-panel p-5">

      <div className="text-xs uppercase tracking-wider text-[var(--muted-foreground)]">

        {label}

      </div>

      <div className={cn("mt-1 text-3xl font-bold tabular-nums", valueClass)}>{value}</div>

      <div className="mt-1 text-xs text-[var(--muted-foreground)]">{sub}</div>

    </div>

  )

}



function InfoRow({ label, value, ok }: { label: string; value: string; ok?: boolean }) {

  return (

    <div className="flex justify-between gap-2">

      <dt className="text-[var(--muted-foreground)]">{label}</dt>

      <dd className={cn("font-medium", ok && "text-emerald-400")}>{value}</dd>

    </div>

  )

}



function QuickAction({ to, title, desc }: { to: string; title: string; desc: string }) {

  return (

    <Link

      to={to}

      className="quick-action-link"

    >

      <div className="font-medium text-sm">{title}</div>

      <div className="text-xs text-[var(--muted-foreground)]">{desc}</div>

    </Link>

  )

}


