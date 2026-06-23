import { create } from "zustand"
import { persist } from "zustand/middleware"

export type EmployeeTheme = "dark" | "light"

interface EmployeeThemeState {
  theme: EmployeeTheme
  setTheme: (theme: EmployeeTheme) => void
  toggleTheme: () => void
}

export const useEmployeeThemeStore = create<EmployeeThemeState>()(
  persist(
    (set, get) => ({
      theme: "dark",
      setTheme: (theme) => set({ theme }),
      toggleTheme: () => set({ theme: get().theme === "dark" ? "light" : "dark" }),
    }),
    { name: "palmvein-employee-theme" },
  ),
)
