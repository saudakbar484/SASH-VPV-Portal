import { useQuery } from "@tanstack/react-query"

import {

  Bar,

  BarChart,

  CartesianGrid,

  Cell,

  Line,

  LineChart,

  Pie,

  PieChart,

  ResponsiveContainer,

  Tooltip,

  XAxis,

  YAxis,

} from "recharts"

import { CheckCircle2, ClipboardList, XCircle } from "lucide-react"

import { Badge } from "@/components/ui/badge"

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

import { endpoints } from "@/lib/api"

import { cn } from "@/lib/utils"



const PIE_COLORS = ["#34d399", "#f87171", "#a78bfa", "#60a5fa", "#fbbf24"]



export function Logs() {

  const analytics = useQuery({

    queryKey: ["admin-logs-analytics"],

    queryFn: () => endpoints.admin.logsAnalytics(7),

    refetchInterval: 10000,

  })



  const recognition = useQuery({

    queryKey: ["recognition-logs"],

    queryFn: () => endpoints.recognize.logs({ limit: 100 }),

    refetchInterval: 5000,

  })



  const a = analytics.data

  const recRows = recognition.data?.logs ?? []



  const pieData = a

    ? [

        { name: "Accepted", value: a.accepted },

        { name: "Rejected", value: a.rejected },

      ]

    : []



  return (

    <div className="space-y-6">

      <AdminPageHeader

        title="Audit & Activity Logs"

        description="Recognition analytics and event history. Employee sessions are managed in the Employees tab."

      />



      {a && (

        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">

          <MiniStat label="Recognition" value={String(a.total_recognition)} />

          <MiniStat label="Accepted" value={String(a.accepted)} accent="green" />

          <MiniStat label="Rejected" value={String(a.rejected)} accent="red" />

          <MiniStat label="Logins (7d)" value={String(a.total_logins)} accent="purple" />

          <MiniStat label="Online now" value={String(a.active_sessions)} accent="green" />

        </div>

      )}



      {a && (

        <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">

          <GlassPanel title="Recognition activity" className="xl:col-span-2">

            <div className="h-56">

              <ResponsiveContainer width="100%" height="100%">

                <LineChart data={a.recognition_by_day}>

                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff15" />

                  <XAxis dataKey="label" tick={{ fill: "#888", fontSize: 11 }} />

                  <YAxis tick={{ fill: "#888", fontSize: 11 }} allowDecimals={false} />

                  <Tooltip

                    contentStyle={{

                      background: "#1a1025",

                      border: "1px solid #ffffff20",

                      borderRadius: 8,

                    }}

                  />

                  <Line type="monotone" dataKey="count" stroke="#a78bfa" strokeWidth={2} dot={{ fill: "#c084fc", r: 4 }} />

                </LineChart>

              </ResponsiveContainer>

            </div>

          </GlassPanel>



          <GlassPanel title="Accept vs reject">

            <div className="h-56">

              <ResponsiveContainer width="100%" height="100%">

                <PieChart>

                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={3}>

                    {pieData.map((_, i) => (

                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />

                    ))}

                  </Pie>

                  <Tooltip contentStyle={{ background: "#1a1025", border: "1px solid #ffffff20", borderRadius: 8 }} />

                </PieChart>

              </ResponsiveContainer>

            </div>

          </GlassPanel>



          <GlassPanel title="Activity by type" className="xl:col-span-2">

            <div className="h-52">

              <ResponsiveContainer width="100%" height="100%">

                <BarChart data={a.activity_by_type}>

                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff15" />

                  <XAxis dataKey="label" tick={{ fill: "#888", fontSize: 10 }} />

                  <YAxis tick={{ fill: "#888", fontSize: 11 }} allowDecimals={false} />

                  <Tooltip contentStyle={{ background: "#1a1025", border: "1px solid #ffffff20", borderRadius: 8 }} />

                  <Bar dataKey="count" fill="#9333ea" radius={[4, 4, 0, 0]} />

                </BarChart>

              </ResponsiveContainer>

            </div>

          </GlassPanel>



          <GlassPanel title="Events by employee">

            <div className="h-52">

              <ResponsiveContainer width="100%" height="100%">

                <BarChart data={a.events_by_employee} layout="vertical">

                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff15" />

                  <XAxis type="number" tick={{ fill: "#888", fontSize: 11 }} />

                  <YAxis type="category" dataKey="label" width={80} tick={{ fill: "#888", fontSize: 10 }} />

                  <Tooltip contentStyle={{ background: "#1a1025", border: "1px solid #ffffff20", borderRadius: 8 }} />

                  <Bar dataKey="count" fill="#34d399" radius={[0, 4, 4, 0]} />

                </BarChart>

              </ResponsiveContainer>

            </div>

          </GlassPanel>

        </div>

      )}



      <GlassPanel title="Recognition history" icon={<ClipboardList className="size-5 icon-brand" />}>

        {recRows.length === 0 ? (

          <p className="py-8 text-center text-sm text-[var(--muted-foreground)]">No recognition events yet.</p>

        ) : (

          <div className="overflow-x-auto rounded-lg border border-white/10">

            <Table>

              <TableHeader>

                <TableRow className="border-white/10">

                  <TableHead>Time</TableHead>

                  <TableHead>Mode</TableHead>

                  <TableHead>Claimed</TableHead>

                  <TableHead>Matched</TableHead>

                  <TableHead className="text-right">Similarity</TableHead>

                  <TableHead>Result</TableHead>

                  <TableHead className="text-right">ms</TableHead>

                </TableRow>

              </TableHeader>

              <TableBody>

                {recRows.map((row) => (

                  <TableRow key={row.id} className="border-white/10">

                    <TableCell className="whitespace-nowrap font-mono text-xs text-[var(--muted-foreground)]">

                      {new Date(row.created_at).toLocaleString()}

                    </TableCell>

                    <TableCell><Badge variant="outline" className="font-mono text-xs">{row.mode}</Badge></TableCell>

                    <TableCell className="font-mono text-xs">{row.claimed_name ?? "—"}</TableCell>

                    <TableCell className="font-mono text-xs">{row.matched_name ?? "—"}</TableCell>

                    <TableCell className="text-right font-mono text-xs">{row.similarity.toFixed(4)}</TableCell>

                    <TableCell>

                      {row.matched ? <CheckCircle2 className="size-4 text-emerald-400" /> : <XCircle className="size-4 text-red-400" />}

                    </TableCell>

                    <TableCell className="text-right font-mono text-xs">{row.latency_ms}</TableCell>

                  </TableRow>

                ))}

              </TableBody>

            </Table>

          </div>

        )}

      </GlassPanel>

    </div>

  )

}



function MiniStat({ label, value, accent }: { label: string; value: string; accent?: "green" | "red" | "purple" }) {

  const cls =

    accent === "green" ? "text-emerald-400" : accent === "red" ? "text-red-400" : accent === "purple" ? "text-brand-muted" : "text-[var(--foreground)]"

  return (

    <div className="glass-panel p-3">

      <div className="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)]">{label}</div>

      <div className={cn("mt-0.5 text-lg font-bold tabular-nums", cls)}>{value}</div>

    </div>

  )

}


