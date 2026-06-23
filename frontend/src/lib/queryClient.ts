import { QueryClient } from "@tanstack/react-query"

/**
 * App-wide TanStack Query client. We keep cache time generous since most
 * data (identities, logs) doesn't change rapidly, but stream-status and
 * device-status polls use short intervals configured per-hook.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 10_000,
    },
    mutations: {
      retry: 0,
    },
  },
})
