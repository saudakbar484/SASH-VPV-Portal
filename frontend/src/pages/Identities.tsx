import { Fragment, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ChevronDown, ChevronRight, Database, Trash2, UserCheck } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { AdminPageHeader } from "@/components/AdminPageHeader"
import { GlassPanel } from "@/components/GlassPanel"
import { endpoints, type RegisteredIdentity } from "@/lib/api"
import { cn } from "@/lib/utils"

export function Identities() {
  const queryClient = useQueryClient()
  const [expanded, setExpanded] = useState<number | null>(null)
  const [pending, setPending] = useState<RegisteredIdentity | null>(null)

  const registered = useQuery({
    queryKey: ["admin-registered-identities"],
    queryFn: endpoints.admin.registeredIdentities,
  })

  const dataset = useQuery({
    queryKey: ["admin-dataset-registry"],
    queryFn: endpoints.admin.datasetRegistry,
  })

  const del = useMutation({
    mutationFn: (id: number) => endpoints.admin.deleteEmployee(id),
    onSuccess: () => {
      setPending(null)
      queryClient.invalidateQueries({ queryKey: ["admin-registered-identities"] })
      queryClient.invalidateQueries({ queryKey: ["admin-dataset-registry"] })
      queryClient.invalidateQueries({ queryKey: ["admin-employees"] })
    },
  })

  const rows = registered.data?.identities ?? []
  const registry = dataset.data?.entries ?? []

  return (
    <div className="space-y-6">
      <AdminPageHeader
        title="Identities"
        description="Registered employees from signup — one identity per person with Left and Right hand sub-records."
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatChip label="Total enrolled" value={String(rows.length)} accent="purple" />
        <StatChip label="Registered accounts" value={String(rows.length)} accent="green" />
        <StatChip label="Admin-only enrollments" value="0" accent="muted" />
      </div>

      <GlassPanel
        title="Enrolled identities"
        description="Signup-registered users only. Expand a row to see Left / Right hand details."
        icon={<UserCheck className="size-5 icon-brand" />}
        headerExtra={
          <Badge className="badge-brand text-[var(--foreground)]">{rows.length}</Badge>
        }
      >
        {registered.isPending ? (
          <p className="text-sm text-[var(--muted-foreground)]">Loading…</p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-[var(--muted-foreground)]">No registered identities yet.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-white/10">
            <Table>
              <TableHeader>
                <TableRow className="border-white/10 hover:bg-transparent">
                  <TableHead className="w-8" />
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Folder</TableHead>
                  <TableHead>Hands</TableHead>
                  <TableHead>Samples</TableHead>
                  <TableHead>Registered</TableHead>
                  <TableHead className="w-12" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((person) => {
                  const isOpen = expanded === person.account_id
                  const left = person.hands.find((h) => h.hand === "Left")
                  const right = person.hands.find((h) => h.hand === "Right")
                  return (
                    <Fragment key={person.account_id}>
                      <TableRow
                        key={person.account_id}
                        className="border-white/10 cursor-pointer hover:bg-white/5"
                        onClick={() =>
                          setExpanded(isOpen ? null : person.account_id)
                        }
                      >
                        <TableCell>
                          {isOpen ? (
                            <ChevronDown className="size-4 text-brand-muted" />
                          ) : (
                            <ChevronRight className="size-4 text-[var(--muted-foreground)]" />
                          )}
                        </TableCell>
                        <TableCell className="font-medium">{person.full_name}</TableCell>
                        <TableCell className="font-mono text-xs text-[var(--muted-foreground)]">
                          {person.email}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="border-[var(--primary)]/30 font-mono">
                            {person.dataset_id}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <HandBadge hand="Left" ok={!!left?.enrolled} count={left?.sample_count ?? 0} />
                            <HandBadge hand="Right" ok={!!right?.enrolled} count={right?.sample_count ?? 0} />
                          </div>
                        </TableCell>
                        <TableCell className="font-mono">{person.total_samples}</TableCell>
                        <TableCell className="font-mono text-xs text-[var(--muted-foreground)]">
                          {new Date(person.registered_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Button
                            size="icon"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation()
                              setPending(person)
                            }}
                          >
                            <Trash2 className="size-4 text-red-400" />
                          </Button>
                        </TableCell>
                      </TableRow>
                      {isOpen && (
                        <TableRow key={`${person.account_id}-detail`} className="border-white/10 bg-white/[0.02]">
                          <TableCell colSpan={8}>
                            <div className="grid gap-3 py-2 sm:grid-cols-2">
                              <HandDetail
                                hand="Left"
                                enrolled={!!left?.enrolled}
                                samples={left?.sample_count ?? 0}
                                userId={left?.user_id}
                              />
                              <HandDetail
                                hand="Right"
                                enrolled={!!right?.enrolled}
                                samples={right?.sample_count ?? 0}
                                userId={right?.user_id}
                              />
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </Fragment>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </GlassPanel>

      <GlassPanel
        title="Dataset registered"
        description="On-disk palm image folders for signup users (data/dataset/{id}/)."
        icon={<Database className="size-5 icon-brand" />}
        headerExtra={
          <Badge className="badge-brand text-[var(--foreground)]">{registry.length}</Badge>
        }
      >
        {registry.length === 0 ? (
          <p className="text-sm text-[var(--muted-foreground)]">No dataset folders registered.</p>
        ) : (
          <div className="space-y-3">
            {registry.map((entry) => (
              <div
                key={entry.folder_id}
                className="rounded-lg border border-white/10 bg-white/[0.03] p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <span className="font-mono text-brand-muted">{entry.folder_id}</span>
                    <span className="mx-2 text-[var(--muted-foreground)]">·</span>
                    <span className="font-medium">{entry.full_name}</span>
                  </div>
                  <span className="font-mono text-xs text-[var(--muted-foreground)]">
                    {entry.email}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap gap-3">
                  {entry.hands.map((h) => (
                    <div
                      key={h.hand}
                      className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-xs"
                    >
                      <span className="font-semibold text-[var(--foreground)]">{h.hand}</span>
                      <span className="ml-2 text-[var(--muted-foreground)]">
                        {h.image_count} images
                      </span>
                      {h.files.length > 0 && (
                        <span className="ml-2 font-mono text-[10px] text-white/40">
                          {h.files[0]}…{h.files[h.files.length - 1]}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </GlassPanel>

      <Dialog open={!!pending} onOpenChange={(v) => !v && setPending(null)}>
        <DialogContent className="border-white/10 bg-[var(--card)]">
          <DialogHeader>
            <DialogTitle>Delete {pending?.full_name}?</DialogTitle>
            <DialogDescription>
              Removes the account, both hand templates, dataset folder {pending?.dataset_id}, and
              CSV mapping. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPending(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={del.isPending}
              onClick={() => pending && del.mutate(pending.account_id)}
            >
              {del.isPending ? "Deleting…" : "Delete employee"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function HandBadge({
  hand,
  ok,
  count,
}: {
  hand: string
  ok: boolean
  count: number
}) {
  return (
    <span
      className={cn(
        "rounded px-1.5 py-0.5 text-[10px] font-medium",
        ok ? "bg-emerald-500/20 text-emerald-300" : "bg-white/10 text-white/40",
      )}
    >
      {hand} {count > 0 ? count : "—"}
    </span>
  )
}

function HandDetail({
  hand,
  enrolled,
  samples,
  userId,
}: {
  hand: string
  enrolled: boolean
  samples: number
  userId?: number | null
}) {
  return (
    <div className="rounded-lg border border-white/10 p-3">
      <div className="text-xs uppercase tracking-wider text-brand-muted">{hand} hand</div>
      <dl className="mt-2 grid grid-cols-[90px_1fr] gap-1 text-xs">
        <dt className="text-[var(--muted-foreground)]">Status</dt>
        <dd>{enrolled ? "Enrolled" : "Missing"}</dd>
        <dt className="text-[var(--muted-foreground)]">Samples</dt>
        <dd className="font-mono">{samples}</dd>
        {userId && (
          <>
            <dt className="text-[var(--muted-foreground)]">Gallery ID</dt>
            <dd className="font-mono">{userId}</dd>
          </>
        )}
      </dl>
    </div>
  )
}

function StatChip({
  label,
  value,
  accent,
}: {
  label: string
  value: string
  accent: "purple" | "green" | "muted"
}) {
  const valueClass =
    accent === "purple"
      ? "text-brand-muted"
      : accent === "green"
        ? "text-emerald-400"
        : "text-[var(--foreground)]"
  return (
    <div className="glass-panel p-4">
      <div className="text-xs uppercase tracking-wider text-[var(--muted-foreground)]">
        {label}
      </div>
      <div className={cn("mt-1 text-2xl font-bold tabular-nums", valueClass)}>{value}</div>
    </div>
  )
}
