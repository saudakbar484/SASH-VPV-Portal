import { useMemo, useState } from "react"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { Briefcase, Clock, Download, Trash2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"

import { Button } from "@/components/ui/button"

import { Input, fieldClassName } from "@/components/ui/input"

import { Label } from "@/components/ui/label"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

import { AdminPageHeader } from "@/components/AdminPageHeader"

import { GlassPanel } from "@/components/GlassPanel"

import { endpoints, type EmployeeSummary } from "@/lib/api"

import { cn } from "@/lib/utils"

function fmtDuration(sec: number) {
  if (sec < 60) return `${sec}s`
  const m = Math.floor(sec / 60)
  const h = Math.floor(m / 60)
  if (h > 0) return `${h}h ${m % 60}m`
  return `${m}m`
}

function statusBadge(status?: string | null) {
  if (!status) return null
  const cls =
    status === "present" || status === "online"
      ? "text-emerald-400 border-emerald-500/40"
      : status === "late"
        ? "text-amber-400 border-amber-500/40"
        : status === "absent"
          ? "text-red-400 border-red-500/40"
          : "text-brand-muted border-[var(--primary)]/40"
  return (
    <Badge variant="outline" className={cn("text-[10px] capitalize", cls)}>
      {status}
    </Badge>
  )
}

export function Employees() {
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [reportFrom, setReportFrom] = useState(() => {
    const d = new Date()
    d.setDate(1)
    return d.toISOString().slice(0, 10)
  })
  const [reportTo, setReportTo] = useState(() => new Date().toISOString().slice(0, 10))
  const [closeDayDate, setCloseDayDate] = useState("")
  const [overrideDate, setOverrideDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [overrideStatus, setOverrideStatus] = useState("present")
  const [overrideNote, setOverrideNote] = useState("")

  const queryClient = useQueryClient()
  const month = useMemo(() => new Date().toISOString().slice(0, 7), [])

  const employees = useQuery({
    queryKey: ["admin-employees"],
    queryFn: endpoints.admin.employees,
    refetchInterval: 10000,
  })

  const invites = useQuery({
    queryKey: ["admin-invites"],
    queryFn: endpoints.admin.invites,
  })

  const detail = useQuery({
    queryKey: ["admin-employee-detail", selectedId],
    queryFn: () => endpoints.admin.employeeDetail(selectedId!),
    enabled: selectedId != null,
  })

  const attendance = useQuery({
    queryKey: ["admin-employee-attendance", selectedId, month],
    queryFn: () => endpoints.admin.employeeAttendance(selectedId!, month),
    enabled: selectedId != null,
  })

  const report = useQuery({
    queryKey: ["admin-attendance-report", reportFrom, reportTo],
    queryFn: () => endpoints.admin.attendanceReport(reportFrom, reportTo),
    enabled: reportFrom <= reportTo,
  })

  const deleteEmp = useMutation({
    mutationFn: (id: number) => endpoints.admin.deleteEmployee(id),
    onSuccess: () => {
      setSelectedId(null)
      queryClient.invalidateQueries({ queryKey: ["admin-employees"] })
    },
  })

  const closeDay = useMutation({
    mutationFn: () => endpoints.admin.closeAttendanceDay(closeDayDate || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-employees"] })
      queryClient.invalidateQueries({ queryKey: ["admin-attendance-report"] })
      queryClient.invalidateQueries({ queryKey: ["admin-employee-attendance"] })
    },
  })

  const overrideAtt = useMutation({
    mutationFn: () =>
      endpoints.admin.overrideAttendance(selectedId!, {
        work_date: overrideDate,
        status: overrideStatus,
        note: overrideNote || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-employees"] })
      queryClient.invalidateQueries({ queryKey: ["admin-employee-attendance"] })
      queryClient.invalidateQueries({ queryKey: ["admin-attendance-report"] })
    },
  })

  const empList = employees.data?.employees ?? []
  const onlineCount = empList.filter((e) => e.is_online).length
  const presentToday = empList.filter((e) => e.today_status === "present" || e.today_status === "late").length

  return (
    <div className="space-y-6">
      <AdminPageHeader
        title="Employees"
        description="Attendance reports, employee records, sessions, and activity."
      />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <MiniStat label="Total employees" value={String(empList.length)} accent="purple" />
        <MiniStat label="Present today" value={String(presentToday)} accent="green" />
        <MiniStat label="Online now" value={String(onlineCount)} accent="green" />
        <MiniStat label="Total sessions" value={String(empList.reduce((n, e) => n + e.total_sessions, 0))} />
        <MiniStat
          label="Pending invites"
          value={String(invites.data?.invites.filter((i) => i.status === "pending").length ?? 0)}
        />
      </div>

      <GlassPanel title="Attendance report" icon={<Download className="size-5 icon-brand" />}>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <Label>From</Label>
            <Input type="date" value={reportFrom} onChange={(e) => setReportFrom(e.target.value)} className="mt-1" />
          </div>
          <div>
            <Label>To</Label>
            <Input type="date" value={reportTo} onChange={(e) => setReportTo(e.target.value)} className="mt-1" />
          </div>
          <Button
            variant="outline"
            onClick={() => endpoints.admin.downloadAttendanceCsv(reportFrom, reportTo)}
          >
            <Download className="size-4" />
            Export CSV
          </Button>
          <div className="ml-auto flex flex-wrap items-end gap-2">
            <div>
              <Label>Close day (optional date)</Label>
              <Input
                type="date"
                value={closeDayDate}
                onChange={(e) => setCloseDayDate(e.target.value)}
                className="mt-1"
                placeholder="Today if empty"
              />
            </div>
            <Button
              variant="outline"
              disabled={closeDay.isPending}
              onClick={() => closeDay.mutate()}
            >
              Mark absences
            </Button>
          </div>
        </div>
        {closeDay.data && (
          <p className="mt-2 text-xs text-emerald-400">
            {closeDay.data.skipped
              ? `Skipped ${closeDay.data.work_date}: ${closeDay.data.reason}`
              : `Marked ${closeDay.data.marked_absent} absent, ${closeDay.data.half_days ?? 0} half-day for ${closeDay.data.work_date}`}
          </p>
        )}
        <div className="mt-4 overflow-x-auto rounded-lg border border-white/10">
          <Table>
            <TableHeader>
              <TableRow className="border-white/10">
                <TableHead>Date</TableHead>
                <TableHead>Employee</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Hours</TableHead>
                <TableHead>Marked by</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(report.data?.rows ?? []).slice(0, 50).map((r) => (
                <TableRow key={`${r.account_id}-${r.work_date}`} className="border-white/10">
                  <TableCell className="font-mono text-xs">{r.work_date}</TableCell>
                  <TableCell>{r.full_name}</TableCell>
                  <TableCell className="capitalize">{r.status}</TableCell>
                  <TableCell>{fmtDuration(r.total_seconds)}</TableCell>
                  <TableCell className="capitalize text-xs text-[var(--muted-foreground)]">{r.marked_by}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {(report.data?.count ?? 0) > 50 && (
            <p className="p-2 text-xs text-[var(--muted-foreground)]">
              Showing 50 of {report.data?.count} rows. Export CSV for full report.
            </p>
          )}
        </div>
      </GlassPanel>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
        <GlassPanel title="Employee list" icon={<Briefcase className="size-5 icon-brand" />}>
          <div className="max-h-[520px] space-y-2 overflow-y-auto">
            {empList.map((emp) => (
              <EmployeeRow
                key={emp.account_id}
                emp={emp}
                active={selectedId === emp.account_id}
                onClick={() => setSelectedId(emp.account_id)}
              />
            ))}
            {empList.length === 0 && (
              <p className="text-sm text-[var(--muted-foreground)]">No employees registered.</p>
            )}
          </div>
        </GlassPanel>

        <GlassPanel title={detail.data?.full_name ?? "Employee detail"}>
          {!selectedId ? (
            <p className="py-12 text-center text-sm text-[var(--muted-foreground)]">
              Select an employee to view their history.
            </p>
          ) : detail.isPending ? (
            <p className="text-sm text-[var(--muted-foreground)]">Loading…</p>
          ) : detail.data ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <MiniStat label="Total time" value={fmtDuration(detail.data.total_time_seconds)} accent="purple" />
                <MiniStat label="Sessions" value={String(detail.data.sessions.length)} />
                <MiniStat
                  label="Today"
                  value={fmtDuration(empList.find((e) => e.account_id === selectedId)?.today_seconds ?? 0)}
                  accent="green"
                />
                <MiniStat
                  label="Today status"
                  value={empList.find((e) => e.account_id === selectedId)?.today_status ?? "—"}
                />
              </div>

              <div className="rounded-lg border border-white/10 p-3">
                <h4 className="mb-2 text-sm font-semibold text-[var(--foreground)]">Manual attendance override</h4>
                <div className="grid gap-2 md:grid-cols-[auto_auto_1fr_auto] md:items-end">
                  <div>
                    <Label>Date</Label>
                    <Input
                      type="date"
                      value={overrideDate}
                      onChange={(e) => setOverrideDate(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label>Status</Label>
                    <select
                      value={overrideStatus}
                      onChange={(e) => setOverrideStatus(e.target.value)}
                      className={cn("mt-1", fieldClassName)}
                    >
                      <option value="present">Present</option>
                      <option value="late">Late</option>
                      <option value="half_day">Half day</option>
                      <option value="absent">Absent</option>
                      <option value="leave">Leave</option>
                    </select>
                  </div>
                  <div>
                    <Label>Note (optional)</Label>
                    <Input
                      value={overrideNote}
                      onChange={(e) => setOverrideNote(e.target.value)}
                      className="mt-1"
                      placeholder="Reason for override"
                    />
                  </div>
                  <Button
                    className="btn-brand "
                    disabled={overrideAtt.isPending}
                    onClick={() => overrideAtt.mutate()}
                  >
                    Apply
                  </Button>
                </div>
              </div>

              <div>
                <h4 className="mb-2 text-sm font-semibold text-[var(--foreground)]">Attendance ({month})</h4>
                <div className="overflow-x-auto rounded-lg border border-white/10">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-white/10">
                        <TableHead>Date</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>In</TableHead>
                        <TableHead>Hours</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(attendance.data ?? []).map((r) => (
                        <TableRow key={r.work_date} className="border-white/10">
                          <TableCell className="font-mono text-xs">{r.work_date}</TableCell>
                          <TableCell className="capitalize">{r.status}</TableCell>
                          <TableCell className="font-mono text-xs">
                            {r.first_login_at ? new Date(r.first_login_at).toLocaleTimeString() : "—"}
                          </TableCell>
                          <TableCell>{fmtDuration(r.total_seconds)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>

              <div>
                <h4 className="mb-2 flex items-center gap-2 text-sm font-semibold text-[var(--foreground)]">
                  <Clock className="size-4" />
                  Sessions
                </h4>
                <div className="overflow-x-auto rounded-lg border border-white/10">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-white/10">
                        <TableHead>Login</TableHead>
                        <TableHead>Logout</TableHead>
                        <TableHead>Method</TableHead>
                        <TableHead>Duration</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {detail.data.sessions.map((s) => (
                        <TableRow key={s.id} className="border-white/10">
                          <TableCell className="font-mono text-xs">
                            {new Date(s.login_at).toLocaleString()}
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {s.logout_at ? new Date(s.logout_at).toLocaleString() : "—"}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-xs">
                              {s.login_method}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {s.duration_seconds != null
                              ? fmtDuration(s.duration_seconds)
                              : s.is_active
                                ? "Active"
                                : "—"}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>

              {detail.data.role !== "admin" && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => deleteEmp.mutate(detail.data!.account_id)}
                  disabled={deleteEmp.isPending}
                >
                  <Trash2 className="size-4" />
                  Delete employee
                </Button>
              )}
            </div>
          ) : null}
        </GlassPanel>
      </div>
    </div>
  )
}

function EmployeeRow({
  emp,
  active,
  onClick,
}: {
  emp: EmployeeSummary
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full rounded-lg border px-3 py-3 text-left transition",
        active
          ? "border-[var(--primary)]/50 bg-[color-mix(in_srgb,var(--primary)_15%,transparent)]"
          : "border-white/10 bg-white/[0.02] hover:border-[var(--primary)]/30",
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium">{emp.full_name}</span>
        <div className="flex items-center gap-1">
          {statusBadge(emp.today_status)}
          {emp.is_online && <span className="text-[10px] text-emerald-400">● Online</span>}
        </div>
      </div>
      <div className="mt-1 font-mono text-[10px] text-[var(--muted-foreground)]">{emp.email}</div>
      <div className="mt-2 flex gap-3 text-xs text-[var(--muted-foreground)]">
        <span>{fmtDuration(emp.today_seconds ?? 0)} today</span>
        <span>{emp.total_sessions} sessions</span>
      </div>
    </button>
  )
}

function MiniStat({
  label,
  value,
  accent,
}: {
  label: string
  value: string
  accent?: "green" | "purple"
}) {
  const cls =
    accent === "green" ? "text-emerald-400" : accent === "purple" ? "text-brand-muted" : "text-[var(--foreground)]"
  return (
    <div className="glass-panel p-3">
      <div className="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">{label}</div>
      <div className={cn("mt-0.5 text-lg font-bold tabular-nums capitalize", cls)}>{value}</div>
    </div>
  )
}
