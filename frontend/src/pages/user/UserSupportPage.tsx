import { Link } from "react-router-dom"

import { useQuery } from "@tanstack/react-query"

import { CustomerPageHeader } from "@/components/customer/CustomerPageHeader"
import { endpoints } from "@/lib/api"

export function UserSupportPage() {
  const device = useQuery({ queryKey: ["device-status"], queryFn: endpoints.device.status })

  return (
    <div>
      <CustomerPageHeader title="Support" description="Help and system status" />
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="customer-card p-5">
          <h3 className="font-semibold">Scanner status</h3>
          <p className="mt-2 text-sm">
            {device.data?.connected ? (
              <span className="text-emerald-600">Online — ready for verification</span>
            ) : (
              <span className="text-amber-600">Offline — check sensor connection</span>
            )}
          </p>
        </div>
        <div className="customer-card p-5">
          <h3 className="font-semibold">Documentation</h3>
          <ul className="mt-2 space-y-1 text-sm text-[var(--primary)]">
            <li><Link to="/how-it-works" className="hover:underline">How it works</Link></li>
            <li><Link to="/security" className="hover:underline">Security</Link></li>
            <li>
              <Link to={{ pathname: "/", hash: "#faq" }} className="hover:underline">
                FAQ
              </Link>
            </li>
            <li><Link to="/contact" className="hover:underline">Contact us</Link></li>
          </ul>
        </div>
      </div>
    </div>
  )
}
