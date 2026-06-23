import { useQuery } from "@tanstack/react-query"

import { CustomerPageHeader } from "@/components/customer/CustomerPageHeader"
import { endpoints } from "@/lib/api"

export function UserProfilePage() {
  const profile = useQuery({ queryKey: ["user-profile"], queryFn: endpoints.user.profile })

  if (profile.isPending || !profile.data) {
    return <div className="h-40 animate-pulse rounded-lg bg-[var(--muted)]" />
  }

  const p = profile.data

  return (
    <div>
      <CustomerPageHeader title="Profile" description="Your identity and enrollment status" />
      <dl className="customer-card divide-y divide-[var(--border)] text-sm">
        {[
          ["Full name", p.full_name],
          ["Email", p.email],
          ["Member since", new Date(p.registered_at).toLocaleDateString()],
          ["Dataset ID", `••••${p.dataset_id.slice(-2)}`],
          ["Left palm", p.left_enrolled ? "Enrolled" : "Missing"],
          ["Right palm", p.right_enrolled ? "Enrolled" : "Missing"],
        ].map(([k, v]) => (
          <div key={k} className="flex justify-between gap-4 px-4 py-3">
            <dt className="text-[var(--muted-foreground)]">{k}</dt>
            <dd className="font-medium">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
