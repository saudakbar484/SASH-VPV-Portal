import { Link } from "react-router-dom"

import { useQuery } from "@tanstack/react-query"

import { Fingerprint, Hand, Shield } from "lucide-react"

import { CustomerPageHeader } from "@/components/customer/CustomerPageHeader"
import { Button } from "@/components/ui/button"
import { endpoints } from "@/lib/api"

export function UserDashboardPage() {
  const dash = useQuery({ queryKey: ["user-dashboard"], queryFn: endpoints.user.dashboard })

  if (dash.isPending || !dash.data) {
    return <div className="h-40 animate-pulse rounded-lg bg-[var(--muted)]" />
  }

  const d = dash.data
  const palmsComplete = d.left_enrolled && d.right_enrolled

  return (
    <div>
      <CustomerPageHeader
        title={`Welcome, ${d.full_name.split(" ")[0]}`}
        description="Your biometric member dashboard"
        action={
          palmsComplete ? (
            <Button asChild className="btn-brand">
              <Link to="/member/recognition">
                <Fingerprint className="size-4" />
                Scan & verify
              </Link>
            </Button>
          ) : (
            <Button asChild className="btn-brand">
              <Link to="/member/enrollment">
                <Hand className="size-4" />
                Enroll palm
              </Link>
            </Button>
          )
        }
      />

      {!palmsComplete && (
        <div className="customer-card mb-4 flex flex-col gap-3 border-[var(--primary)]/30 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-medium">Complete palm enrollment</p>
            <p className="text-sm text-[var(--muted-foreground)]">
              Enroll both palms to unlock palm sign-in and verification scans.
            </p>
          </div>
          <Button asChild variant="outline" className="shrink-0">
            <Link to="/user/enroll">Enroll now</Link>
          </Button>
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="customer-card p-4">
          <div className="text-xs uppercase text-[var(--muted-foreground)]">Left palm</div>
          <div className="mt-1 font-semibold">{d.left_enrolled ? "Enrolled ✓" : "Not enrolled"}</div>
        </div>
        <div className="customer-card p-4">
          <div className="text-xs uppercase text-[var(--muted-foreground)]">Right palm</div>
          <div className="mt-1 font-semibold">{d.right_enrolled ? "Enrolled ✓" : "Not enrolled"}</div>
        </div>
        <div className="customer-card p-4">
          <div className="text-xs uppercase text-[var(--muted-foreground)]">This week</div>
          <div className="mt-1 text-2xl font-bold tabular-nums">{d.verifications_this_week}</div>
          <div className="text-xs text-[var(--muted-foreground)]">verifications</div>
        </div>
        <div className="customer-card p-4">
          <div className="flex items-center gap-2 text-xs uppercase text-[var(--muted-foreground)]">
            <Shield className="size-4" />
            Security score
          </div>
          <div className="mt-1 text-2xl font-bold text-[var(--primary)]">{d.security_score}%</div>
        </div>
      </div>
    </div>
  )
}
