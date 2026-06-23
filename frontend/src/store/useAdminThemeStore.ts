import { create } from "zustand"
import { persist } from "zustand/middleware"

export type AdminTheme = "dark" | "light"

interface AdminThemeState {
  theme: AdminTheme
  setTheme: (theme: AdminTheme) => void
  toggleTheme: () => void
}

export const useAdminThemeStore = create<AdminThemeState>()(
  persist(
    (set, get) => ({
      theme: "dark",
      setTheme: (theme) => set({ theme }),
      toggleTheme: () => set({ theme: get().theme === "dark" ? "light" : "dark" }),
    }),
    { name: "palmvein-admin-theme" },
  ),
)
