import { create } from "zustand"
import { persist } from "zustand/middleware"

export type CustomerTheme = "dark" | "light"

interface CustomerThemeState {
  theme: CustomerTheme
  setTheme: (theme: CustomerTheme) => void
  toggleTheme: () => void
}

export const useCustomerThemeStore = create<CustomerThemeState>()(
  persist(
    (set, get) => ({
      theme: "light",
      setTheme: (theme) => set({ theme }),
      toggleTheme: () => set({ theme: get().theme === "dark" ? "light" : "dark" }),
    }),
    { name: "palmvein-customer-theme" },
  ),
)
