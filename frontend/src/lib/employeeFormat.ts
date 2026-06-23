export function fmtDuration(sec: number): string {
  if (sec <= 0) return "0m"
  const m = Math.floor(sec / 60)
  const h = Math.floor(m / 60)
  if (h > 0) return `${h}h ${m % 60}m`
  return `${m}m`
}

export function fmtHoursDecimal(sec: number): string {
  return (sec / 3600).toFixed(1)
}

export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—"
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

export function fmtDate(iso: string): string {
  return new Date(iso + "T12:00:00").toLocaleDateString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
  })
}

export function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function greetingName(name: string): string {
  const h = new Date().getHours()
  const first = name.split(" ")[0] ?? name
  if (h < 12) return `Good morning, ${first}`
  if (h < 17) return `Good afternoon, ${first}`
  return `Good evening, ${first}`
}

export type AttendanceStatus =
  | "present"
  | "late"
  | "absent"
  | "half_day"
  | "leave"
  | "not_checked_in"
  | string

export function statusMeta(status: AttendanceStatus) {
  switch (status) {
    case "present":
      return { label: "Present", tone: "success" as const }
    case "late":
      return { label: "Late", tone: "warning" as const }
    case "half_day":
      return { label: "Half day", tone: "info" as const }
    case "absent":
      return { label: "Absent", tone: "danger" as const }
    case "leave":
      return { label: "Leave", tone: "muted" as const }
    case "not_checked_in":
      return { label: "Not checked in", tone: "muted" as const }
    default:
      return { label: status.replace(/_/g, " "), tone: "muted" as const }
  }
}
