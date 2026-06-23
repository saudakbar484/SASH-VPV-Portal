import { useMemo, useState } from "react"

import { useQuery } from "@tanstack/react-query"

import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react"

import { AttendanceStatusBadge } from "@/components/employee/AttendanceStatusBadge"

import { EmployeePageHeader } from "@/components/employee/EmployeePageHeader"

import { EmployeePanel } from "@/components/employee/EmployeePanel"

import { EmployeeStatCard } from "@/components/employee/EmployeeStatCard"

import { Button } from "@/components/ui/button"

import { Input } from "@/components/ui/input"

import { endpoints } from "@/lib/api"

import { fmtDuration, fmtHoursDecimal, fmtTime } from "@/lib/employeeFormat"

function shiftMonth(ym: string, delta: number): string {
  const [y, m] = ym.split("-").map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`
}

export function EmployeeAttendancePage() {
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7))

  const { data, isPending } = useQuery({
    queryKey: ["employee-attendance", month],
    queryFn: () => endpoints.employee.attendance(month),
  })

  const summary = useQuery({
    queryKey: ["employee-attendance-summary", month],
    queryFn: () => endpoints.employee.attendanceSummary(month),
  })

  const monthLabel = useMemo(() => {
    const [y, m] = month.split("-").map(Number)
    return new Date(y, m - 1, 1).toLocaleDateString([], { month: "long", year: "numeric" })
  }, [month])

  return (
    <div className="space-y-5 sm:space-y-6">
      <EmployeePageHeader
        title="Attendance"
        description="Monthly timesheet with check-in times, hours on site, and status for each work day."
        action={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={() => setMonth((m) => shiftMonth(m, -1))}>
              <ChevronLeft className="size-4" />
            </Button>
            <Input
              type="month"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              className="w-[160px]"
            />
            <Button variant="outline" size="icon" onClick={() => setMonth((m) => shiftMonth(m, 1))}>
              <ChevronRight className="size-4" />
            </Button>
          </div>
        }
      />

      {summary.data && (
        <div className="grid gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-5">
          <EmployeeStatCard label="Present" value={String(summary.data.present)} accent="success" />
          <EmployeeStatCard label="Late" value={String(summary.data.late)} accent="warning" />
          <EmployeeStatCard label="Absent" value={String(summary.data.absent)} accent="danger" />
          <EmployeeStatCard label="Half day" value={String(summary.data.half_day)} accent="info" />
          <EmployeeStatCard
            label="Total hours"
            value={`${fmtHoursDecimal(summary.data.total_seconds)}h`}
            sub={fmtDuration(summary.data.total_seconds)}
            accent="purple"
          />
        </div>
      )}

      <EmployeePanel
        title={monthLabel}
        description={`${data?.records.length ?? 0} days with records`}
        icon={<CalendarDays className="size-4" />}
      >
        {isPending ? (
          <p className="text-sm text-[var(--muted-foreground)]">Loading attendance…</p>
        ) : !data?.records.length ? (
          <div className="rounded-lg border border-dashed border-[var(--border)] py-12 text-center">
            <p className="text-sm font-medium">No records for this month</p>
            <p className="mt-1 text-xs text-[var(--muted-foreground)]">
              Check-ins will appear here after you sign in at the office.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted-foreground)]">
                  <th className="pb-3 pr-4 font-medium">Date</th>
                  <th className="pb-3 pr-4 font-medium">Day</th>
                  <th className="pb-3 pr-4 font-medium">Status</th>
                  <th className="pb-3 pr-4 font-medium">Check in</th>
                  <th className="pb-3 pr-4 font-medium">Check out</th>
                  <th className="pb-3 pr-4 font-medium text-center">Sessions</th>
                  <th className="pb-3 font-medium text-right">On site</th>
                </tr>
              </thead>
              <tbody>
                {data.records.map((r) => {
                  const dayName = new Date(r.work_date + "T12:00:00").toLocaleDateString([], {
                    weekday: "short",
                  })
                  return (
                    <tr key={r.work_date} className="border-b border-[var(--border)]/60 last:border-0">
                      <td className="py-3.5 pr-4 font-mono text-xs">{r.work_date}</td>
                      <td className="py-3.5 pr-4 text-[var(--muted-foreground)]">{dayName}</td>
                      <td className="py-3.5 pr-4">
                        <AttendanceStatusBadge status={r.status} />
                      </td>
                      <td className="py-3.5 pr-4 font-mono text-xs">{fmtTime(r.first_login_at)}</td>
                      <td className="py-3.5 pr-4 font-mono text-xs">{fmtTime(r.last_logout_at)}</td>
                      <td className="py-3.5 pr-4 text-center tabular-nums">{r.session_count}</td>
                      <td className="py-3.5 text-right font-medium tabular-nums">
                        {fmtDuration(r.total_seconds)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </EmployeePanel>
    </div>
  )
}
