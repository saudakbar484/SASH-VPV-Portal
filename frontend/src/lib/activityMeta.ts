import {
  AlertCircle,
  CalendarCheck,
  Clock,
  LogIn,
  LogOut,
  ShieldCheck,
  UserCheck,
  type LucideIcon,
} from "lucide-react"

export interface ActivityMeta {
  label: string
  description: string
  icon: LucideIcon
  category: "auth" | "attendance" | "security" | "other"
}

const MAP: Record<string, ActivityMeta> = {
  login: {
    label: "Signed in",
    description: "Session started",
    icon: LogIn,
    category: "auth",
  },
  logout: {
    label: "Signed out",
    description: "Session ended",
    icon: LogOut,
    category: "auth",
  },
  logout_palm_verified: {
    label: "Palm logout",
    description: "Verified sign-out with palm scan",
    icon: ShieldCheck,
    category: "security",
  },
  logout_email_fallback: {
    label: "Password logout",
    description: "Signed out with email confirmation",
    icon: LogOut,
    category: "auth",
  },
  attendance_present: {
    label: "Marked present",
    description: "First check-in for the day",
    icon: UserCheck,
    category: "attendance",
  },
  attendance_late: {
    label: "Marked late",
    description: "Check-in after grace period",
    icon: Clock,
    category: "attendance",
  },
  attendance_absent: {
    label: "Marked absent",
    description: "No check-in recorded",
    icon: AlertCircle,
    category: "attendance",
  },
  attendance_manual: {
    label: "Attendance updated",
    description: "HR adjusted your record",
    icon: CalendarCheck,
    category: "attendance",
  },
  password_changed: {
    label: "Password changed",
    description: "Account security updated",
    icon: ShieldCheck,
    category: "security",
  },
}

export function getActivityMeta(eventType: string): ActivityMeta {
  return (
    MAP[eventType] ?? {
      label: eventType.replace(/_/g, " "),
      description: "System event",
      icon: AlertCircle,
      category: "other",
    }
  )
}

export const ACTIVITY_FILTERS = [
  { id: "all", label: "All" },
  { id: "auth", label: "Sign in/out" },
  { id: "attendance", label: "Attendance" },
  { id: "security", label: "Security" },
] as const
