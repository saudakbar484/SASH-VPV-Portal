import { create } from "zustand"
import { persist } from "zustand/middleware"
import { api } from "@/lib/api"

export interface AuthUser {
  account_id: number
  email: string
  full_name: string
  dataset_id: string
  dataset_name: string
  role?: string
  session_id?: number | null
}

interface AuthState {
  token: string | null
  user: AuthUser | null
  setAuth: (token: string, user: AuthUser) => void
  clearAuth: () => void
  logout: () => Promise<void>
  isAuthenticated: () => boolean
  isAdmin: () => boolean
  isEmployee: () => boolean
  isCustomer: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      setAuth: (token, user) => set({ token, user }),
      clearAuth: () => set({ token: null, user: null }),
      logout: async () => {
        const { user, isAdmin } = get()
        try {
          if (user?.session_id && isAdmin()) {
            await api.post("/api/auth/logout", { session_id: user.session_id })
          }
        } catch {
          /* best-effort — employees use palm logout dialog */
        }
        set({ token: null, user: null })
      },
      isAuthenticated: () => !!get().token,
      isAdmin: () => get().user?.role === "admin",
      isEmployee: () => get().user?.role === "employee",
      isCustomer: () => get().user?.role === "customer",
    }),
    { name: "palmvein-auth" },
  ),
)
