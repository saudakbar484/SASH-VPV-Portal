import { useMemo, useState } from "react"

import { useQuery } from "@tanstack/react-query"

import { ClipboardList, Search } from "lucide-react"

import { EmployeePageHeader } from "@/components/employee/EmployeePageHeader"

import { EmployeePanel } from "@/components/employee/EmployeePanel"

import { EmployeeStatCard } from "@/components/employee/EmployeeStatCard"

import { Input } from "@/components/ui/input"

import { ACTIVITY_FILTERS, getActivityMeta } from "@/lib/activityMeta"

import { endpoints } from "@/lib/api"

import { fmtDateTime } from "@/lib/employeeFormat"

import { cn } from "@/lib/utils"

type FilterId = (typeof ACTIVITY_FILTERS)[number]["id"]

function groupByDate(activities: { id: number; event_type: string; detail: string | null; created_at: string }[]) {
  const groups: Record<string, typeof activities> = {}
  for (const a of activities) {
    const key = new Date(a.created_at).toLocaleDateString([], {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    })
    if (!groups[key]) groups[key] = []
    groups[key].push(a)
  }
  return Object.entries(groups)
}

export function EmployeeActivityPage() {
  const [filter, setFilter] = useState<FilterId>("all")
  const [search, setSearch] = useState("")

  const { data, isPending } = useQuery({
    queryKey: ["employee-activity"],
    queryFn: endpoints.employee.activity,
  })

  const filtered = useMemo(() => {
    let list = data?.activities ?? []
    if (filter !== "all") {
      list = list.filter((a) => getActivityMeta(a.event_type).category === filter)
    }
    const q = search.trim().toLowerCase()
    if (q) {
      list = list.filter(
        (a) =>
          a.event_type.toLowerCase().includes(q) ||
          (a.detail ?? "").toLowerCase().includes(q) ||
          getActivityMeta(a.event_type).label.toLowerCase().includes(q),
      )
    }
    return list
  }, [data, filter, search])

  const groups = useMemo(() => groupByDate(filtered), [filtered])

  const loginCount = (data?.activities ?? []).filter((a) =>
    ["login", "logout", "logout_palm_verified", "logout_email_fallback"].includes(a.event_type),
  ).length

  const attendanceCount = (data?.activities ?? []).filter((a) =>
    a.event_type.startsWith("attendance_"),
  ).length

  return (
    <div className="space-y-5 sm:space-y-6">
      <EmployeePageHeader
        title="Activity log"
        description="Audit trail of sign-ins, sign-outs, attendance events, and account security actions."
      />

      <div className="grid gap-3 sm:grid-cols-3 sm:gap-4">
        <EmployeeStatCard label="Total events" value={String(data?.count ?? 0)} icon={<ClipboardList className="size-4" />} />
        <EmployeeStatCard label="Session events" value={String(loginCount)} accent="purple" />
        <EmployeeStatCard label="Attendance events" value={String(attendanceCount)} accent="info" />
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          {ACTIVITY_FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setFilter(f.id)}
              className={cn(
                "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                filter === f.id
                  ? "border-[var(--primary)]/50 bg-[color-mix(in_srgb,var(--primary)_15%,transparent)] text-[var(--primary)]"
                  : "border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--accent)]",
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="relative w-full sm:max-w-xs">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-[var(--muted-foreground)]" />
          <Input
            placeholder="Search activity…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      <EmployeePanel title="Timeline" description={`Showing ${filtered.length} events`} icon={<ClipboardList className="size-4" />}>
        {isPending ? (
          <p className="text-sm text-[var(--muted-foreground)]">Loading activity…</p>
        ) : groups.length === 0 ? (
          <div className="rounded-lg border border-dashed border-[var(--border)] py-12 text-center">
            <p className="text-sm font-medium">No activity found</p>
            <p className="mt-1 text-xs text-[var(--muted-foreground)]">
              Try a different filter or sign in to generate events.
            </p>
          </div>
        ) : (
          <div className="space-y-8">
            {groups.map(([dateLabel, items]) => (
              <div key={dateLabel}>
                <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
                  {dateLabel}
                </h3>
                <ol className="relative space-y-0 border-l border-[var(--border)] pl-6">
                  {items.map((a) => {
                    const meta = getActivityMeta(a.event_type)
                    const Icon = meta.icon
                    return (
                      <li key={a.id} className="relative pb-6 last:pb-0">
                        <span className="absolute -left-[1.65rem] flex size-7 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--card)]">
                          <Icon className="size-3.5 text-[var(--primary)]" />
                        </span>
                        <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)]/20 px-4 py-3">
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div>
                              <p className="text-sm font-semibold">{meta.label}</p>
                              <p className="text-xs text-[var(--muted-foreground)]">{meta.description}</p>
                            </div>
                            <time className="shrink-0 font-mono text-xs text-[var(--muted-foreground)]">
                              {fmtDateTime(a.created_at)}
                            </time>
                          </div>
                          {a.detail && (
                            <p className="mt-2 rounded-md bg-[var(--card)] px-2 py-1.5 font-mono text-[11px] text-[var(--muted-foreground)]">
                              {a.detail}
                            </p>
                          )}
                        </div>
                      </li>
                    )
                  })}
                </ol>
              </div>
            ))}
          </div>
        )}
      </EmployeePanel>
    </div>
  )
}
