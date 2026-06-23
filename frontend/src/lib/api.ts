import axios, { type AxiosInstance } from "axios"
import { useAuthStore } from "@/store/useAuthStore"

/**
 * Single axios instance for all backend calls. The dev server proxies
 * /api/* to FastAPI (see vite.config.ts), so we always use relative paths.
 */
export const api: AxiosInstance = axios.create({
  baseURL: "",
  timeout: 60_000,
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// --- Shared payload types ---------------------------------------------------

export interface DeviceStatus {
  loaded: boolean
  connected: boolean
  img_size?: string | null
  feat_size?: number | null
  sdk_dir?: string | null
  xrtech_visible_on_usb?: boolean
}

export interface StreamStatus {
  connected: boolean
  fps: number
  last_frame_age_seconds: number | null
}

export interface HardwareInfo {
  connected: boolean
  serial: string | null
  fw_version: string | null
  sdk_version: string | null
}

export interface PalmDistance {
  distance_mm: number | null
  in_range: boolean
}

export interface IdentitySummary {
  id: number
  name: string
  hand: "Left" | "Right"
  sample_count: number
  template_dim: number
  created_at: string
  account_id?: number | null
  account_email?: string | null
  dataset_id?: string | null
  enrollment_source?: "registered" | "admin"
}

export interface IdentitySample {
  id: number
  image_path: string
  captured_at: string
}

export interface IdentityDetail extends IdentitySummary {
  samples: IdentitySample[]
}

export interface IdentitiesListResponse {
  count: number
  identities: IdentitySummary[]
}

export interface DatasetClass {
  class_id: string
  user_id: string
  hand: "Left" | "Right"
  class_idx: number
}

export interface DatasetLookupResponse {
  total: number
  matches: number
  limit: number
  offset: number
  results: DatasetClass[]
}

export interface VerifyResponse {
  matched: boolean
  similarity: number
  threshold: number
  confidence: number
  user_id: number
  claimed_name: string
  hand: "Left" | "Right"
  latency_ms: number
  captured_at: string
  log_id: number
  probe_image_path?: string | null
  rejected_reason?: string | null
}

export interface IdentifyCandidate {
  user_id: number
  name: string
  hand: "Left" | "Right"
  similarity: number
  confidence: number
}

export interface IdentifyResponse {
  matched: boolean
  best_user_id: number | null
  threshold: number
  candidates: IdentifyCandidate[]
  latency_ms: number
  captured_at: string
  log_id: number
  probe_image_path?: string | null
  rejected_reason?: string | null
}

export interface RecognitionLogEntry {
  id: number
  mode: "verify" | "identify"
  claimed_name: string | null
  matched_name: string | null
  user_id: number | null
  similarity: number
  matched: boolean
  threshold: number
  latency_ms: number
  created_at: string
  probe_image_path?: string | null
  rejected_reason?: string | null
}

export interface RecognitionLogsResponse {
  count: number
  accepted: number
  rejected: number
  limit: number
  offset: number
  logs: RecognitionLogEntry[]
  enabled?: boolean
}

export interface AuthUser {
  account_id: number
  email: string
  full_name: string
  dataset_id: string
  dataset_name: string
  role?: string
  session_id?: number | null
}

export interface DashboardStats {
  scanner_connected: boolean
  scanner_message: string
  enrolled_persons: number
  dataset_classes: number
  image_resolution: string
  feature_size: number | null
}

export interface RegisteredHandInfo {
  hand: "Left" | "Right"
  user_id?: number | null
  sample_count: number
  enrolled: boolean
}

export interface RegisteredIdentity {
  account_id: number
  full_name: string
  email: string
  dataset_id: string
  dataset_name: string
  role: string
  registered_at: string
  hands: RegisteredHandInfo[]
  total_samples: number
}

export interface DatasetRegistryEntry {
  folder_id: string
  dataset_name: string
  email: string
  full_name: string
  account_id: number
  hands: { hand: string; image_count: number; files: string[] }[]
}

export interface EmployeeSummary {
  account_id: number
  full_name: string
  email: string
  dataset_id: string
  role: string
  registered_at: string
  total_sessions: number
  total_time_seconds: number
  last_login_at: string | null
  is_online: boolean
  activity_count: number
  today_status?: string | null
  today_seconds?: number
}

export interface EmployeeInviteEntry {
  id: number
  token: string
  email: string
  full_name: string
  status: string
  expires_at: string
  created_at: string
  signup_url: string
}

export interface EmployeeDashboard {
  full_name: string
  work_date: string
  status: string
  first_login_at: string | null
  total_seconds_today: number
  session_count: number
  is_online: boolean
  work_day_start: string
  grace_minutes: number
  active_session?: {
    session_id: number | null
    login_at: string | null
    is_active: boolean
  } | null
}

export interface EmployeeCompanyPolicy {
  work_day_start: string
  grace_minutes: number
  timezone: string
  half_day_hours: number
  require_palm_logout: boolean
  exclude_weekends: boolean
}

export interface AttendanceMonthSummary {
  month: string
  total_days: number
  present: number
  late: number
  absent: number
  half_day: number
  leave: number
  total_seconds: number
  avg_seconds_per_day: number
}

export interface EmployeeProfile {
  account_id: number
  email: string
  full_name: string
  dataset_id: string
  dataset_name: string
  role: string
  registered_at: string
  left_enrolled: boolean
  right_enrolled: boolean
}

export interface AttendanceDay {
  work_date: string
  status: string
  first_login_at: string | null
  last_logout_at: string | null
  total_seconds: number
  session_count: number
}

export interface CompanyAttendanceSettings {
  work_day_start: string
  grace_minutes: number
  timezone: string
  require_palm_logout: boolean
  exclude_weekends: boolean
  half_day_hours: number
  notify_absent: boolean
  notify_weekly_summary: boolean
  admin_notify_email: string | null
  smtp_configured: boolean
}

export interface CompanyHolidayEntry {
  id: number
  holiday_date: string
  name: string
  created_at: string
}

export interface AttendanceReportRow {
  account_id: number
  full_name: string
  email: string
  work_date: string
  status: string
  first_login_at: string | null
  last_logout_at: string | null
  total_seconds: number
  session_count: number
  marked_by: string
  note: string | null
}

export interface InvitePreview {
  valid: boolean
  full_name?: string | null
  email?: string | null
  expires_at?: string | null
  message?: string | null
}

export interface PalmLogoutResponse {
  success: boolean
  matched: boolean
  similarity: number
  threshold: number
  message?: string | null
  probe_image_url?: string | null
}

export interface EmployeeDetail {
  account_id: number
  full_name: string
  email: string
  dataset_id: string
  dataset_name: string
  role: string
  registered_at: string
  total_time_seconds: number
  sessions: {
    id: number
    login_method: string
    login_at: string
    logout_at: string | null
    duration_seconds: number | null
    is_active: boolean
  }[]
  activities: { id: number; event_type: string; detail: string | null; created_at: string }[]
  recognition_events: number
}

export interface LogsAnalytics {
  total_recognition: number
  accepted: number
  rejected: number
  total_logins: number
  active_sessions: number
  recognition_by_day: { label: string; count: number }[]
  activity_by_type: { label: string; count: number }[]
  events_by_employee: { label: string; count: number }[]
}

export interface TrainingStatusResponse {
  last_trained_at: string | null
  pending_images: number
  pending_sources: Record<string, number>
  days_since_train: number
  show_reminder_banner: boolean
  training_in_progress: boolean
  last_run_status: string | null
  last_val_eer: number | null
  last_val_rank1: number | null
  images_ingested_last: number | null
}

export interface EnrollLookupMatch {
  name: string
  folder_id?: string | null
  source: string
  left_samples: number
  right_samples: number
  left_enrolled: boolean
  right_enrolled: boolean
  account_email?: string | null
  match_type: string
}

export interface EnrollLookupResult {
  query: string
  exact_match: EnrollLookupMatch | null
  similar: EnrollLookupMatch[]
  message?: string | null
  can_enroll_left: boolean
  can_enroll_right: boolean
}

export interface RegisterSessionStatus {
  register_session_id: string
  full_name: string
  email: string
  dataset_name: string
  folder_id: string
  current_hand: "Left" | "Right"
  left_captured: number
  right_captured: number
  target_per_hand: number
  left_complete: boolean
  right_complete: boolean
  both_complete: boolean
  last_error?: string | null
}

export type RegisterCaptureResult = RegisterSessionStatus & {
  captured: boolean
  reason?: string | null
  last_capture_index?: number | null
  last_capture_hand?: string | null
  last_image_url?: string | null
  embedding_norm?: number | null
  message?: string | null
}

export interface PalmLoginResponse {
  success: boolean
  matched: boolean
  similarity: number
  threshold: number
  access_token?: string | null
  account_id?: number | null
  email?: string | null
  full_name?: string | null
  dataset_id?: string | null
  dataset_name?: string | null
  hand?: string | null
  latency_ms: number
  probe_image_url?: string | null
  message?: string | null
  role?: string | null
  session_id?: number | null
}

export interface GoogleAuthResponse {
  status: "authenticated" | "needs_enrollment"
  access_token?: string | null
  account_id?: number | null
  email?: string | null
  full_name?: string | null
  dataset_id?: string | null
  dataset_name?: string | null
  role?: string | null
  session_id?: number | null
  register_session_id?: string | null
  message?: string | null
}

// --- Typed endpoint helpers -------------------------------------------------

export const endpoints = {
  auth: {
    captcha: () =>
      api.get<{ captcha_id: string; question: string }>("/api/auth/captcha").then((r) => r.data),
    registerStart: (body: {
      full_name: string
      email: string
      password: string
      confirm_password: string
      captcha_id: string
      captcha_answer: number
      invite_token?: string
    }) => api.post("/api/auth/register/start", body).then((r) => r.data),
    previewInvite: (token: string) =>
      api.get<InvitePreview>(`/api/auth/invite/${token}`).then((r) => r.data),
    registerPalmStart: (
      registerSessionId: string,
      firstHand: "Left" | "Right",
      datasetName?: string,
    ) =>
      api
        .post<RegisterSessionStatus>("/api/auth/register/palm/start", {
          register_session_id: registerSessionId,
          first_hand: firstHand,
          ...(datasetName ? { dataset_name: datasetName } : {}),
        })
        .then((r) => r.data),
    registerPalmCapture: (registerSessionId: string) =>
      api
        .post<RegisterCaptureResult>(
          "/api/auth/register/palm/capture",
          { register_session_id: registerSessionId },
        )
        .then((r) => r.data),
    registerSwitchHand: (registerSessionId: string, nextHand: "Left" | "Right") =>
      api
        .post<RegisterSessionStatus>("/api/auth/register/palm/switch-hand", {
          register_session_id: registerSessionId,
          next_hand: nextHand,
        })
        .then((r) => r.data),
    registerComplete: (registerSessionId: string) =>
      api
        .post<{
          success: boolean
          account_id: number
          email: string
          full_name: string
          dataset_id: string
          dataset_name: string
          access_token?: string | null
          role?: string
          session_id?: number | null
          verification_required?: boolean
          email_sent?: boolean
        }>("/api/auth/register/complete", { register_session_id: registerSessionId })
        .then((r) => r.data),
    login: (email: string, password: string) =>
      api
        .post<{ access_token: string; user: AuthUser }>("/api/auth/login", { email, password })
        .then((r) => r.data),
    loginCustomer: (email: string, password: string) =>
      api
        .post<{ access_token: string; user: AuthUser }>("/api/auth/login/customer", { email, password })
        .then((r) => r.data),
    registerCustomerStart: (body: {
      username: string
      email: string
      password: string
      confirm_password: string
      captcha_id: string
      captcha_answer: number
    }) =>
      api
        .post<{
          message: string
          email?: string
          verification_required: boolean
          email_sent: boolean
        }>("/api/auth/register/customer/start", body)
        .then((r) => r.data),
    registerCustomerVerify: (email: string, code: string) =>
      api
        .post<{
          success: boolean
          access_token: string
          user: AuthUser
          message: string
          username?: string
        }>("/api/auth/register/customer/verify", { email, code })
        .then((r) => r.data),
    verifyEmail: (email: string, code: string) =>
      api
        .post<{
          success: boolean
          access_token: string
          user: AuthUser
          message: string
          username?: string
        }>("/api/auth/verify-email", { email, code })
        .then((r) => r.data),
    resendVerification: (email: string) =>
      api
        .post<{ success: boolean; email_sent: boolean; message: string }>(
          "/api/auth/resend-verification",
          { email },
        )
        .then((r) => r.data),
    forgotPassword: (email: string) =>
      api
        .post<{ success: boolean; email_sent: boolean; message: string }>(
          "/api/auth/password/forgot",
          { email },
        )
        .then((r) => r.data),
    resetPassword: (body: {
      email: string
      code: string
      password: string
      confirm_password: string
    }) =>
      api
        .post<{ success: boolean; role: string; email: string; message: string }>(
          "/api/auth/password/reset",
          body,
        )
        .then((r) => r.data),
    registerCustomerResendCode: (email: string) =>
      api
        .post<{ success: boolean; email_sent: boolean; message: string }>(
          "/api/auth/register/customer/resend-code",
          { email },
        )
        .then((r) => r.data),
    customerSignInOptions: (email: string) =>
      api
        .get<{
          exists: boolean
          email_verified?: boolean
          palms_enrolled?: boolean
          username?: string | null
        }>("/api/auth/customer/sign-in-options", { params: { email } })
        .then((r) => r.data),
    registerEnrollStart: (firstHand: "Left" | "Right") =>
      api
        .post<RegisterSessionStatus>("/api/auth/register/enroll/start", { first_hand: firstHand })
        .then((r) => r.data),
    loginCustomerPalm: () =>
      api
        .post<PalmLoginResponse>("/api/auth/login/customer/palm", undefined, { timeout: 120_000 })
        .then((r) => r.data),
    googleConfig: () =>
      api.get<{ enabled: boolean; client_id?: string | null }>("/api/auth/google/config").then((r) => r.data),
    googleAuth: (credential: string, intent: "login" | "signup") =>
      api
        .post<GoogleAuthResponse>("/api/auth/google", { credential, intent })
        .then((r) => r.data),
    loginPalm: () =>
      api
        .post<PalmLoginResponse>("/api/auth/login/palm", undefined, { timeout: 120_000 })
        .then((r) => r.data),
    me: () => api.get<AuthUser>("/api/auth/me").then((r) => r.data),
    logout: (body?: {
      session_id?: number | null
      email_fallback?: boolean
      password?: string
    }) => api.post("/api/auth/logout", body ?? {}).then((r) => r.data),
    logoutPalm: (sessionId?: number | null) =>
      api
        .post<PalmLogoutResponse>(
          "/api/auth/logout/palm",
          { session_id: sessionId ?? null },
          { timeout: 120_000 },
        )
        .then((r) => r.data),
    changePassword: (body: {
      current_password: string
      new_password: string
      confirm_password: string
    }) => api.post<{ success: boolean }>("/api/auth/change-password", body).then((r) => r.data),
  },
  employee: {
    dashboard: () => api.get<EmployeeDashboard>("/api/employee/dashboard").then((r) => r.data),
    attendance: (month: string) =>
      api
        .get<{ month: string; records: AttendanceDay[] }>("/api/employee/attendance", {
          params: { month },
        })
        .then((r) => r.data),
    attendanceSummary: (month: string) =>
      api
        .get<AttendanceMonthSummary>("/api/employee/attendance/summary", { params: { month } })
        .then((r) => r.data),
    activity: () =>
      api
        .get<{ count: number; activities: { id: number; event_type: string; detail: string | null; created_at: string }[] }>(
          "/api/employee/activity",
        )
        .then((r) => r.data),
    profile: () => api.get<EmployeeProfile>("/api/employee/profile").then((r) => r.data),
    companyPolicy: () => api.get<EmployeeCompanyPolicy>("/api/employee/company-policy").then((r) => r.data),
  },
  user: {
    dashboard: () =>
      api
        .get<{
          full_name: string
          email: string
          left_enrolled: boolean
          right_enrolled: boolean
          last_verification_at: string | null
          verifications_this_week: number
          member_since: string
          security_score: number
        }>("/api/user/dashboard")
        .then((r) => r.data),
    profile: () =>
      api
        .get<{
          account_id: number
          email: string
          full_name: string
          dataset_id: string
          dataset_name: string
          role: string
          registered_at: string
          left_enrolled: boolean
          right_enrolled: boolean
        }>("/api/user/profile")
        .then((r) => r.data),
    activity: (days = 30) =>
      api
        .get<{
          count: number
          activities: { id: number; event_type: string; detail: string | null; created_at: string }[]
        }>("/api/user/activity", { params: { days } })
        .then((r) => r.data),
    verifyPalm: () =>
      api
        .post<{
          success: boolean
          matched: boolean
          similarity: number
          threshold: number
          hand?: string | null
          latency_ms: number
          probe_image_url?: string | null
          message?: string | null
        }>("/api/user/verify-palm")
        .then((r) => r.data),
    deleteAccount: () =>
      api.delete<{ success: boolean; message: string }>("/api/user/account").then((r) => r.data),
  },
  public: {
    stats: () =>
      api
        .get<{
          total_customers: number
          total_employees: number
          enrolled_identities: number
          match_threshold: number
        }>("/api/public/stats")
        .then((r) => r.data),
    contact: (body: {
      name: string
      email: string
      organization?: string
      subject: string
      message: string
    }) => api.post<{ success: boolean; message: string }>("/api/public/contact", body).then((r) => r.data),
  },
  admin: {
    registeredIdentities: () =>
      api.get<{ count: number; identities: RegisteredIdentity[] }>("/api/admin/registered-identities").then((r) => r.data),
    datasetRegistry: () =>
      api.get<{ count: number; entries: DatasetRegistryEntry[] }>("/api/admin/dataset-registry").then((r) => r.data),
    employees: () =>
      api.get<{ count: number; employees: EmployeeSummary[] }>("/api/admin/employees").then((r) => r.data),
    employeeDetail: (id: number) =>
      api.get<EmployeeDetail>(`/api/admin/employees/${id}`).then((r) => r.data),
    employeeAttendance: (id: number, month: string) =>
      api
        .get<AttendanceDay[]>(`/api/admin/employees/${id}/attendance`, { params: { month } })
        .then((r) => r.data),
    invites: () =>
      api.get<{ count: number; invites: EmployeeInviteEntry[] }>("/api/admin/invites").then((r) => r.data),
    createInvite: (body: { full_name: string; email: string }) =>
      api.post<{ success: boolean; invite: EmployeeInviteEntry }>("/api/admin/invites", body).then((r) => r.data),
    revokeInvite: (id: number) => api.post(`/api/admin/invites/${id}/revoke`).then((r) => r.data),
    attendanceSettings: () =>
      api.get<CompanyAttendanceSettings>("/api/admin/settings/attendance").then((r) => r.data),
    updateAttendanceSettings: (body: Partial<CompanyAttendanceSettings>) =>
      api.patch<CompanyAttendanceSettings>("/api/admin/settings/attendance", body).then((r) => r.data),
    closeAttendanceDay: (work_date?: string) =>
      api
        .post<{
          success: boolean
          work_date: string
          marked_absent: number
          half_days?: number
          skipped?: boolean
          reason?: string | null
        }>("/api/admin/attendance/close-day", work_date ? { work_date } : {})
        .then((r) => r.data),
    sendWeeklySummary: () =>
      api
        .post<{ sent: boolean; to?: string; date_from?: string; date_to?: string; reason?: string }>(
          "/api/admin/attendance/weekly-summary",
        )
        .then((r) => r.data),
    notificationSettings: () =>
      api
        .get<{
          admin_notify_email: string | null
          notify_absent: boolean
          notify_weekly_summary: boolean
          smtp_configured: boolean
          smtp_password_set: boolean
          smtp_host: string | null
          smtp_from: string | null
          resolved_recipient: string | null
        }>("/api/admin/notifications/settings")
        .then((r) => r.data),
    testNotificationEmail: () =>
      api
        .post<{ sent: boolean; to?: string; reason?: string }>("/api/admin/notifications/test-email", {})
        .then((r) => r.data),
    holidays: () =>
      api.get<{ count: number; holidays: CompanyHolidayEntry[] }>("/api/admin/holidays").then((r) => r.data),
    createHoliday: (body: { holiday_date: string; name: string }) =>
      api.post<CompanyHolidayEntry>("/api/admin/holidays", body).then((r) => r.data),
    deleteHoliday: (id: number) => api.delete(`/api/admin/holidays/${id}`).then((r) => r.data),
    overrideAttendance: (
      accountId: number,
      body: { work_date: string; status: string; note?: string },
    ) =>
      api
        .post<AttendanceDay>(`/api/admin/employees/${accountId}/attendance/override`, body)
        .then((r) => r.data),
    attendanceReport: (date_from: string, date_to: string) =>
      api
        .get<{ count: number; date_from: string; date_to: string; rows: AttendanceReportRow[] }>(
          "/api/admin/attendance/report",
          { params: { date_from, date_to } },
        )
        .then((r) => r.data),
    downloadAttendanceCsv: async (date_from: string, date_to: string) => {
      const r = await api.get("/api/admin/attendance/report.csv", {
        params: { date_from, date_to },
        responseType: "blob",
      })
      const url = URL.createObjectURL(r.data)
      const a = document.createElement("a")
      a.href = url
      a.download = `attendance_${date_from}_${date_to}.csv`
      a.click()
      URL.revokeObjectURL(url)
    },
    deleteEmployee: (id: number) =>
      api.delete(`/api/admin/employees/${id}`).then((r) => r.data),
    customers: () =>
      api
        .get<{
          count: number
          customers: {
            account_id: number
            full_name: string
            email: string
            dataset_id: string
            registered_at: string
            left_enrolled: boolean
            right_enrolled: boolean
            activity_count: number
            last_activity_at: string | null
          }[]
        }>("/api/admin/customers")
        .then((r) => r.data),
    customerDetail: (id: number) =>
      api
        .get<{
          account_id: number
          full_name: string
          email: string
          dataset_id: string
          dataset_name: string
          role: string
          registered_at: string
          left_enrolled: boolean
          right_enrolled: boolean
          activities: { id: number; event_type: string; detail: string | null; created_at: string }[]
        }>(`/api/admin/customers/${id}`)
        .then((r) => r.data),
    deleteCustomer: (id: number) => api.delete(`/api/admin/customers/${id}`).then((r) => r.data),
    logsAnalytics: (days = 7) =>
      api.get<LogsAnalytics>("/api/admin/logs/analytics", { params: { days } }).then((r) => r.data),
    trainingStatus: () =>
      api
        .get<TrainingStatusResponse>("/api/admin/training/status")
        .then((r) => r.data),
    runTraining: () =>
      api
        .post<{ message: string; run_id: number | null }>("/api/admin/training/run")
        .then((r) => r.data),
  },
  dashboard: {
    stats: () => api.get<DashboardStats>("/api/dashboard/stats").then((r) => r.data),
  },
  device: {
    status: () => api.get<DeviceStatus>("/api/device/status").then((r) => r.data),
    streamStatus: () => api.get<StreamStatus>("/api/device/stream-status").then((r) => r.data),
    init: () => api.post("/api/device/init").then((r) => r.data),
    deinit: () => api.post("/api/device/deinit").then((r) => r.data),
    reconnect: () => api.post("/api/device/reconnect").then((r) => r.data),
  },
  hardware: {
    info: () => api.get<HardwareInfo>("/api/hardware/info").then((r) => r.data),
    palmDistance: () => api.get<PalmDistance>("/api/hardware/palm-distance").then((r) => r.data),
    setLedPreset: (preset: string) =>
      api.post("/api/hardware/led/preset", { preset }).then((r) => r.data),
    setLed: (r: number, g: number, b: number) =>
      api.post("/api/hardware/led", { r, g, b }).then((r) => r.data),
    setVolume: (level: number) =>
      api.post("/api/hardware/volume", { level }).then((r) => r.data),
    setSleep: (enabled: boolean) =>
      api.post("/api/hardware/sleep", { enabled }).then((r) => r.data),
  },
  identities: {
    list: () =>
      api.get<IdentitiesListResponse>("/api/identities").then((r) => r.data),
    get: (id: number) =>
      api.get<IdentityDetail>(`/api/identities/${id}`).then((r) => r.data),
    delete: (id: number) =>
      api.delete(`/api/identities/${id}`).then((r) => r.data),
    datasetLookup: (q?: string, limit = 50, offset = 0) =>
      api
        .get<DatasetLookupResponse>("/api/dataset/lookup", {
          params: { q, limit, offset },
        })
        .then((r) => r.data),
  },
  enroll: {
    start: (name: string, hand: "Left" | "Right", targetCount: number) =>
      api
        .post("/api/enroll/session/start", { name, hand, target_count: targetCount })
        .then((r) => r.data),
    capture: (sessionId: string) =>
      api.post("/api/enroll/session/capture", { session_id: sessionId }).then((r) => r.data),
    finish: (sessionId: string) =>
      api.post("/api/enroll/session/finish", { session_id: sessionId }).then((r) => r.data),
    cancel: (sessionId: string) =>
      api.post("/api/enroll/session/cancel", { session_id: sessionId }).then((r) => r.data),
    status: (sessionId: string) =>
      api.get(`/api/enroll/session/${sessionId}/status`).then((r) => r.data),
    lookup: (q: string) =>
      api.get<EnrollLookupResult>("/api/enroll/lookup", { params: { q } }).then((r) => r.data),
  },
  recognize: {
    verify: (userId: number) =>
      api
        .post<VerifyResponse>("/api/recognize/verify", { user_id: userId }, { timeout: 120_000 })
        .then((r) => r.data),
    verifyAccount: (accountId: number) =>
      api
        .post<VerifyResponse>(
          "/api/recognize/verify",
          { account_id: accountId },
          { timeout: 120_000 },
        )
        .then((r) => r.data),
    identify: (topK = 5) =>
      api
        .post<IdentifyResponse>(
          "/api/recognize/identify",
          { top_k: topK },
          { timeout: 120_000 },
        )
        .then((r) => r.data),
    logs: (params?: {
      mode?: "verify" | "identify"
      user_id?: number
      since?: string
      limit?: number
      offset?: number
    }) =>
      api
        .get<RecognitionLogsResponse>("/api/recognize/logs", { params })
        .then((r) => r.data),
  },
}
