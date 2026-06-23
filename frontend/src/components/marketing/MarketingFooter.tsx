import { Link } from "react-router-dom"

import { PalmVeinLogo } from "@/components/PalmVeinLogo"
import { PROJECT_UNIVERSITY } from "@/lib/projectTeam"

const PRODUCT_LINKS = [
  { to: "/", label: "Home", hint: "Overview & live stats" },
  { to: "/technology", label: "Technology", hint: "AI vein pipeline" },
  { to: "/how-it-works", label: "How it works", hint: "Step-by-step journey" },
  { to: "/security", label: "Security", hint: "Privacy & compliance" },
  { to: "/solutions", label: "Solutions", hint: "Portals & use cases" },
] as const

const SUPPORT_LINKS = [
  { to: "/contact", label: "Contact us", hint: "Team & support" },
  { to: { pathname: "/", hash: "#faq" }, label: "FAQ", hint: "Common questions" },
] as const

type MarketingFooterProps = {
  isMember?: boolean
}

export function MarketingFooter({ isMember = false }: MarketingFooterProps) {
  return (
    <footer className="border-t border-[var(--border)] bg-[color-mix(in_srgb,var(--background)_92%,transparent)] backdrop-blur-md">
      <div className="mx-auto grid max-w-6xl gap-8 px-6 py-10 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-2">
          <PalmVeinLogo variant="header" size={32} subtitle="SASH-VPV Portal" />
          <p className="mt-3 max-w-md text-sm leading-relaxed text-[var(--muted-foreground)]">
            Enterprise-grade NIR palm vein biometrics for secure, contactless identity verification.
            Built on the custom SASH-VPV dataset with EfficientNet-B0 + ArcFace metric learning at{" "}
            {PROJECT_UNIVERSITY.name}.
          </p>
        </div>
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">Explore</h4>
          <ul className="mt-3 space-y-3 text-sm">
            {PRODUCT_LINKS.map(({ to, label, hint }) => (
              <li key={to}>
                <Link to={to} className="font-medium hover:text-[var(--primary)]">
                  {label}
                </Link>
                <p className="text-xs text-[var(--muted-foreground)]">{hint}</p>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">Support</h4>
          <ul className="mt-3 space-y-3 text-sm">
            {SUPPORT_LINKS.map(({ to, label, hint }) => (
              <li key={label}>
                <Link to={to} className="font-medium hover:text-[var(--primary)]">
                  {label}
                </Link>
                <p className="text-xs text-[var(--muted-foreground)]">{hint}</p>
              </li>
            ))}
            <li>
              <Link
                to={isMember ? "/member/enrollment" : "/user/signup"}
                className="font-medium hover:text-[var(--primary)]"
              >
                {isMember ? "Palm enrollment" : "Get started"}
              </Link>
              <p className="text-xs text-[var(--muted-foreground)]">
                {isMember ? "Register both palms" : "Create a member account"}
              </p>
            </li>
            {isMember ? (
              <li>
                <Link to="/member/recognition" className="font-medium hover:text-[var(--primary)]">
                  Recognition
                </Link>
                <p className="text-xs text-[var(--muted-foreground)]">Live 1:1 palm verify</p>
              </li>
            ) : (
              <li>
                <Link to="/user/login" className="font-medium hover:text-[var(--primary)]">
                  Member sign in
                </Link>
                <p className="text-xs text-[var(--muted-foreground)]">Existing accounts</p>
              </li>
            )}
          </ul>
        </div>
      </div>
      <div className="border-t border-[var(--border)] px-6 py-4 text-center text-xs text-[var(--muted-foreground)]">
        <p>© {new Date().getFullYear()} SASH-VPV Portal. All rights reserved.</p>
        <p className="mt-1">
          {PROJECT_UNIVERSITY.name} · {PROJECT_UNIVERSITY.location}
        </p>
      </div>
    </footer>
  )
}
