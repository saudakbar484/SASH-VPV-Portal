import { useState } from "react"

import { useQuery } from "@tanstack/react-query"

import { CustomerPageHeader } from "@/components/customer/CustomerPageHeader"
import { fieldClassName } from "@/components/ui/input"
import { endpoints } from "@/lib/api"

export function UserAccessPage() {
  const [days, setDays] = useState(30)
  const activity = useQuery({
    queryKey: ["user-activity", days],
    queryFn: () => endpoints.user.activity(days),
  })

  return (
    <div>
      <CustomerPageHeader
        title="My access"
        description="Your verification and sign-in history"
        action={
          <select
            className={fieldClassName}
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        }
      />
      {activity.isPending ? (
        <div className="h-40 animate-pulse rounded-lg bg-[var(--muted)]" />
      ) : (
        <div className="customer-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-xs uppercase text-[var(--muted-foreground)]">
                <th className="p-3">Time</th>
                <th className="p-3">Event</th>
                <th className="p-3">Detail</th>
              </tr>
            </thead>
            <tbody>
              {(activity.data?.activities ?? []).map((a) => (
                <tr key={a.id} className="border-b border-[var(--border)]">
                  <td className="p-3 font-mono text-xs">{new Date(a.created_at).toLocaleString()}</td>
                  <td className="p-3">{a.event_type.replace(/_/g, " ")}</td>
                  <td className="p-3 text-[var(--muted-foreground)]">{a.detail ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
