import { Link, Outlet, useNavigate } from "react-router-dom"

import {
  Fingerprint,
  Hand,
  Home,
  Mail,
  ScanFace,
  Shield,
  Sparkles,
} from "lucide-react"

import { CustomerThemeToggle } from "@/components/customer/CustomerThemeToggle"
import { MarketingFooter } from "@/components/marketing/MarketingFooter"
import { SidebarLayout, type SidebarNavItem } from "@/components/SidebarLayout"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { useAuthStore } from "@/store/useAuthStore"
import { useCustomerThemeStore } from "@/store/useCustomerThemeStore"

const MARKETING_NAV: SidebarNavItem[] = [
  { to: "/", label: "Home", icon: Home, end: true, subtitle: "Overview & live stats" },
  { to: "/technology", label: "Technology", icon: Sparkles, subtitle: "AI vein pipeline" },
  { to: "/how-it-works", label: "How it works", icon: ScanFace, subtitle: "Step-by-step journey" },
  { to: "/security", label: "Security", icon: Shield, subtitle: "Privacy & compliance" },
  { to: "/solutions", label: "Solutions", icon: Hand, subtitle: "Portals & use cases" },
  { to: "/contact", label: "Contact", icon: Mail, subtitle: "Sales & support" },
]

const MEMBER_NAV: SidebarNavItem[] = [
  { to: "/member/enrollment", label: "Enrollment", icon: Hand, subtitle: "Register both palms" },
  { to: "/member/recognition", label: "Recognition", icon: Fingerprint, subtitle: "Live 1:1 verify" },
]

export function MarketingShell() {
  const token = useAuthStore((s) => s.token)
  const isCustomer = useAuthStore((s) => s.isCustomer())
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const theme = useCustomerThemeStore((s) => s.theme)
  const navigate = useNavigate()
  const isLight = theme === "light"
  const isMemberSession = Boolean(isCustomer && token)

  const handleSignOut = () => {
    void logout().then(() => navigate("/"))
  }

  return (
    <div className="flex min-h-screen flex-col">
      <SidebarLayout
        navItems={MARKETING_NAV}
        logoLink="/"
        logoSubtitle="SASH-VPV Portal"
        portalClassName="marketing-portal customer-portal"
        themeClassName={cn(isLight ? "customer-theme-light" : "customer-theme-dark")}
        backgroundVariant={isLight ? "light" : "dark"}
        sidebarClassName="customer-sidebar border-[var(--border)] bg-[color-mix(in_srgb,var(--card)_95%,transparent)]"
        headerClassName="border-[var(--border)] bg-[color-mix(in_srgb,var(--background)_88%,transparent)] backdrop-blur-xl"
        mainClassName="!px-0 !py-0"
        headerNavItems={isMemberSession ? MEMBER_NAV : undefined}
        userName={isMemberSession ? user?.full_name : undefined}
        userMeta={isMemberSession ? user?.email : undefined}
        onSignOut={isMemberSession ? handleSignOut : undefined}
        headerEnd={
          !isMemberSession ? (
            <div className="flex items-center gap-2">
              <CustomerThemeToggle />
              <Button asChild variant="outline" size="sm" className="hidden sm:inline-flex">
                <Link to="/user/login">Sign in</Link>
              </Button>
              <Button asChild size="sm" className="btn-brand">
                <Link to="/user/signup">Get started</Link>
              </Button>
            </div>
          ) : (
            <CustomerThemeToggle />
          )
        }
      >
        <Outlet />
      </SidebarLayout>
      <MarketingFooter isMember={isMemberSession} />
    </div>
  )
}
