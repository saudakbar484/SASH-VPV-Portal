import { Link } from "react-router-dom"

import { useQuery } from "@tanstack/react-query"

import {
  ArrowRight,
  CalendarDays,
  Clock,
  Timer,
  TrendingUp,
  UserCheck,
} from "lucide-react"

import { AttendanceStatusBadge } from "@/components/employee/AttendanceStatusBadge"

import { EmployeePageHeader } from "@/components/employee/EmployeePageHeader"

import { EmployeePanel } from "@/components/employee/EmployeePanel"

import { EmployeeStatCard } from "@/components/employee/EmployeeStatCard"

import { Button } from "@/components/ui/button"

import { endpoints } from "@/lib/api"

import { cn } from "@/lib/utils"

import {
  fmtDate,
  fmtDuration,
  fmtHoursDecimal,
  fmtTime,
  greetingName,
} from "@/lib/employeeFormat"

export function EmployeeDashboardPage() {
  const month = new Date().toISOString().slice(0, 7)

  const dashboard = useQuery({
    queryKey: ["employee-dashboard"],
    queryFn: endpoints.employee.dashboard,
    refetchInterval: 15000,
  })

  const monthSummary = useQuery({
    queryKey: ["employee-attendance-summary", month],
    queryFn: () => endpoints.employee.attendanceSummary(month),
  })

  const monthRecords = useQuery({
    queryKey: ["employee-attendance", month],
    queryFn: () => endpoints.employee.attendance(month),
  })

  const policy = useQuery({
    queryKey: ["employee-company-policy"],
    queryFn: endpoints.employee.companyPolicy,
  })

  if (dashboard.isPending || !dashboard.data) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 animate-pulse rounded-lg bg-[var(--muted)]" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="employee-card h-28 animate-pulse bg-[var(--muted)]/50" />
          ))}
        </div>
      </div>
    )
  }

  const d = dashboard.data
  const summary = monthSummary.data
  const recent = (monthRecords.data?.records ?? []).slice(0, 5)
  const graceEnd = policy.data
    ? `${policy.data.work_day_start} + ${policy.data.grace_minutes}m grace`
    : `${d.work_day_start} + ${d.grace_minutes}m grace`

  return (
    <div className="space-y-5 sm:space-y-6">
      <EmployeePageHeader
        title={greetingName(d.full_name)}
        description={`Today is ${fmtDate(d.work_date)} · Company work day starts at ${d.work_day_start} (${d.grace_minutes} min grace).`}
        action={
          <Link
            to="/employee/attendance"
            className={cn(
              "group inline-flex max-w-full items-center gap-3 rounded-xl border border-[var(--primary)]/20",
              "bg-[color-mix(in_srgb,var(--primary)_8%,transparent)] px-3.5 py-2.5 shadow-sm transition-all",
              "hover:border-[var(--primary)]/35 hover:bg-[color-mix(in_srgb,var(--primary)_14%,transparent)] hover:shadow-md",
            )}
          >
            <span
              className={cn(
                "flex size-9 shrink-0 items-center justify-center rounded-lg",
                "bg-[color-mix(in_srgb,var(--primary)_15%,transparent)] text-[var(--primary)] transition-colors group-hover:bg-[color-mix(in_srgb,var(--primary)_25%,transparent)]",
              )}
            >
              <CalendarDays className="size-4" />
            </span>
            <span className="min-w-0 text-left leading-tight">
              <span className="block text-sm font-semibold text-[var(--foreground)]">
                Full attendance
              </span>
              <span className="block text-xs font-normal text-[var(--muted-foreground)]">
                Timesheet & history
              </span>
            </span>
            <ArrowRight
              className="ml-0.5 size-4 shrink-0 text-[var(--primary)]/70 transition-transform group-hover:translate-x-0.5"
            />
          </Link>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 sm:gap-4 xl:grid-cols-4">
        <div className="employee-card flex flex-col justify-between gap-2 p-3.5 sm:p-4">
          <div className="flex items-start justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-[var(--muted-foreground)]">
              Today's status
            </span>
            <UserCheck className="size-4 text-[var(--muted-foreground)]" />
          </div>
          <div>
            <AttendanceStatusBadge status={d.status} className="text-sm" />
            <p className="mt-2 text-xs text-[var(--muted-foreground)]">
              {d.first_login_at
                ? `Checked in at ${fmtTime(d.first_login_at)}`
                : d.is_online
                  ? "Active session"
                  : "No check-in yet today"}
            </p>
          </div>
        </div>
        <EmployeeStatCard
          label="Hours today"
          value={fmtDuration(d.total_seconds_today)}
          sub={`${d.session_count} session${d.session_count === 1 ? "" : "s"} · ${fmtHoursDecimal(d.total_seconds_today)}h total`}
          icon={<Clock className="size-4" />}
          accent="purple"
        />
        <EmployeeStatCard
          label="Session"
          value={d.is_online ? "Active" : "Offline"}
          sub={
            d.is_online && d.active_session?.login_at
              ? `Since ${fmtTime(d.active_session.login_at)}`
              : "Sign in to start tracking time"
          }
          icon={<Timer className="size-4" />}
          accent={d.is_online ? "success" : "default"}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-5 lg:gap-5">
        <EmployeePanel
          className="lg:col-span-3"
          title="This month at a glance"
          description={month}
          icon={<TrendingUp className="size-4" />}
          headerAction={
            summary && (
              <span className="text-xs font-medium text-[var(--muted-foreground)]">
                {summary.total_days} recorded days
              </span>
            )
          }
        >
          {monthSummary.isPending ? (
            <p className="text-sm text-[var(--muted-foreground)]">Loading summary…</p>
          ) : summary ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {[
                { label: "Present", value: summary.present, tone: "text-emerald-600 dark:text-emerald-400" },
                { label: "Late", value: summary.late, tone: "text-amber-600 dark:text-amber-400" },
                { label: "Absent", value: summary.absent, tone: "text-red-600 dark:text-red-400" },
                { label: "Half day", value: summary.half_day, tone: "text-sky-600 dark:text-sky-400" },
                { label: "Leave", value: summary.leave, tone: "text-[var(--muted-foreground)]" },
                {
                  label: "Total hours",
                  value: fmtHoursDecimal(summary.total_seconds) + "h",
                  tone: "text-[var(--primary)]",
                },
              ].map((item) => (
                <div
                  key={item.label}
                  className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/30 px-3 py-2.5 sm:px-4 sm:py-3"
                >
                  <div className="text-xs text-[var(--muted-foreground)]">{item.label}</div>
                  <div className={cn("mt-1 text-xl font-bold tabular-nums", item.tone)}>{item.value}</div>
                </div>
              ))}
            </div>
          ) : null}
          {summary && summary.avg_seconds_per_day > 0 && (
            <p className="mt-4 text-xs text-[var(--muted-foreground)]">
              Average {fmtDuration(summary.avg_seconds_per_day)} per recorded day this month.
            </p>
          )}
        </EmployeePanel>

        <EmployeePanel
          className="lg:col-span-2"
          title="Company policy"
          description="Rules applied to your attendance"
          icon={<Clock className="size-4" />}
        >
          {policy.data ? (
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between gap-4 border-b border-[var(--border)] pb-2">
                <dt className="text-[var(--muted-foreground)]">Work day start</dt>
                <dd className="font-mono font-medium">{policy.data.work_day_start}</dd>
              </div>
              <div className="flex justify-between gap-4 border-b border-[var(--border)] pb-2">
                <dt className="text-[var(--muted-foreground)]">Late after</dt>
                <dd className="font-medium">{graceEnd}</dd>
              </div>
              <div className="flex justify-between gap-4 border-b border-[var(--border)] pb-2">
                <dt className="text-[var(--muted-foreground)]">Half-day below</dt>
                <dd className="font-medium">{policy.data.half_day_hours}h on site</dd>
              </div>
              <div className="flex justify-between gap-4 border-b border-[var(--border)] pb-2">
                <dt className="text-[var(--muted-foreground)]">Timezone</dt>
                <dd className="font-medium">{policy.data.timezone}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--muted-foreground)]">Palm logout</dt>
                <dd className="font-medium">{policy.data.require_palm_logout ? "Required" : "Optional"}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-[var(--muted-foreground)]">Loading policy…</p>
          )}
          <Button asChild variant="link" className="mt-3 h-auto p-0 text-[var(--primary)]">
            <Link to="/employee/settings">
              View all settings
              <ArrowRight className="ml-1 size-3.5" />
            </Link>
          </Button>
        </EmployeePanel>
      </div>

      <EmployeePanel
        title="Recent attendance"
        description="Latest days from your timesheet"
        icon={<CalendarDays className="size-4" />}
        headerAction={
          <Button asChild variant="ghost" size="sm" className="text-xs">
            <Link to="/employee/attendance">View all</Link>
          </Button>
        }
      >
        {recent.length === 0 ? (
          <p className="text-sm text-[var(--muted-foreground)]">No attendance records this month yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[480px] text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted-foreground)]">
                  <th className="pb-3 pr-4 font-medium">Date</th>
                  <th className="pb-3 pr-4 font-medium">Status</th>
                  <th className="pb-3 pr-4 font-medium">In</th>
                  <th className="pb-3 pr-4 font-medium">Out</th>
                  <th className="pb-3 font-medium text-right">Hours</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((r) => (
                  <tr key={r.work_date} className="border-b border-[var(--border)]/60 last:border-0">
                    <td className="py-3 pr-4 font-medium">{fmtDate(r.work_date)}</td>
                    <td className="py-3 pr-4">
                      <AttendanceStatusBadge status={r.status} />
                    </td>
                    <td className="py-3 pr-4 font-mono text-xs">{fmtTime(r.first_login_at)}</td>
                    <td className="py-3 pr-4 font-mono text-xs">{fmtTime(r.last_logout_at)}</td>
                    <td className="py-3 text-right font-mono tabular-nums">{fmtDuration(r.total_seconds)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </EmployeePanel>
    </div>
  )
}
