import { create } from "zustand"
import { persist } from "zustand/middleware"

interface AppState {
  /** Bumping this changes the MJPEG <img> src and forces the browser
      to drop any stale connection (after /api/device/reconnect, etc). */
  streamKey: number
  bumpStreamKey: () => void

  /** UI dark mode, persisted in localStorage. */
  darkMode: boolean
  toggleDarkMode: () => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      streamKey: 0,
      bumpStreamKey: () => set((s) => ({ streamKey: s.streamKey + 1 })),
      darkMode: false,
      toggleDarkMode: () => set((s) => ({ darkMode: !s.darkMode })),
    }),
    {
      name: "palm-vein-ui",
      partialize: (s) => ({ darkMode: s.darkMode }),
    },
  ),
)
