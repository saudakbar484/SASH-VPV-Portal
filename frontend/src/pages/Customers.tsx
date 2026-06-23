import { useState } from "react"

import { useMutation, useQuery } from "@tanstack/react-query"

import { AdminPageHeader } from "@/components/AdminPageHeader"
import { Button } from "@/components/ui/button"
import { endpoints } from "@/lib/api"
import { cn } from "@/lib/utils"

export function Customers() {
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const list = useQuery({ queryKey: ["admin-customers"], queryFn: endpoints.admin.customers })
  const detail = useQuery({
    queryKey: ["admin-customer", selectedId],
    queryFn: () => endpoints.admin.customerDetail(selectedId!),
    enabled: selectedId != null,
  })

  const remove = useMutation({
    mutationFn: (id: number) => endpoints.admin.deleteCustomer(id),
    onSuccess: () => {
      setSelectedId(null)
      void list.refetch()
    },
  })

  const customers = list.data?.customers ?? []
  const enrolledBoth = customers.filter((c) => c.left_enrolled && c.right_enrolled).length

  return (
    <div className="space-y-6">
      <AdminPageHeader
        title="Customers"
        description="External member accounts — not on employee payroll or attendance."
      />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[
          { label: "Total", value: customers.length },
          { label: "Fully enrolled", value: enrolledBoth },
          { label: "Active (7d)", value: customers.filter((c) => c.last_activity_at).length },
          { label: "New this month", value: customers.length },
        ].map(({ label, value }) => (
          <div key={label} className="glass-panel p-4">
            <div className="text-xs uppercase text-[var(--muted-foreground)]">{label}</div>
            <div className="mt-1 text-2xl font-bold tabular-nums">{value}</div>
          </div>
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <div className="glass-panel max-h-[70vh] overflow-y-auto p-2">
          {list.isPending ? (
            <p className="p-4 text-sm text-[var(--muted-foreground)]">Loading…</p>
          ) : customers.length === 0 ? (
            <p className="p-4 text-sm text-[var(--muted-foreground)]">No customers yet.</p>
          ) : (
            customers.map((c) => (
              <button
                key={c.account_id}
                type="button"
                onClick={() => setSelectedId(c.account_id)}
                className={cn(
                  "mb-1 w-full rounded-lg border px-3 py-3 text-left transition",
                  selectedId === c.account_id
                    ? "border-[var(--primary)]/40 bg-[color-mix(in_srgb,var(--primary)_10%,transparent)]"
                    : "border-transparent hover:bg-[var(--accent)]",
                )}
              >
                <div className="font-medium">{c.full_name}</div>
                <div className="text-xs text-[var(--muted-foreground)]">{c.email}</div>
              </button>
            ))
          )}
        </div>
        <div className="glass-panel min-h-[320px] p-5">
          {!selectedId ? (
            <p className="text-sm text-[var(--muted-foreground)]">Select a customer to view details.</p>
          ) : detail.isPending || !detail.data ? (
            <p className="text-sm text-[var(--muted-foreground)]">Loading detail…</p>
          ) : (
            <div className="space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-bold">{detail.data.full_name}</h2>
                  <p className="text-sm text-[var(--muted-foreground)]">{detail.data.email}</p>
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  disabled={remove.isPending}
                  onClick={() => {
                    if (confirm("Delete this customer account?")) remove.mutate(selectedId)
                  }}
                >
                  Delete
                </Button>
              </div>
              <dl className="grid gap-2 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-[var(--muted-foreground)]">Registered</dt>
                  <dd>{new Date(detail.data.registered_at).toLocaleString()}</dd>
                </div>
                <div>
                  <dt className="text-[var(--muted-foreground)]">Enrollment</dt>
                  <dd>
                    L: {detail.data.left_enrolled ? "✓" : "—"} / R: {detail.data.right_enrolled ? "✓" : "—"}
                  </dd>
                </div>
              </dl>
              <div>
                <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-brand-muted">Activity</h3>
                <div className="max-h-64 overflow-y-auto rounded-lg border border-[var(--border)]">
                  <table className="w-full text-xs">
                    <tbody>
                      {detail.data.activities.map((a) => (
                        <tr key={a.id} className="border-b border-[var(--border)]">
                          <td className="p-2 font-mono">{new Date(a.created_at).toLocaleString()}</td>
                          <td className="p-2">{a.event_type}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
