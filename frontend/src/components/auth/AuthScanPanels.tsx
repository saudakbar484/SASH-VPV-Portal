import { Camera, Mail } from "lucide-react"

import { LiveFeed } from "@/components/LiveFeed"
import { LiveFeedToolbar } from "@/components/LiveFeedToolbar"
import { cn } from "@/lib/utils"

type AuthScanPanelsProps = {
  probeUrl?: string | null
  probePlaceholder?: string
  className?: string
}

/** Side-by-side live scanner + captured probe for auth pages. */
export function AuthScanPanels({
  probeUrl,
  probePlaceholder = "Press Capture to scan your palm and run the matcher",
  className,
}: AuthScanPanelsProps) {
  return (
    <div className={cn("grid gap-4 sm:grid-cols-2", className)}>
      <div className="auth-scan-panel">
        <LiveFeedToolbar />
        <div className="auth-scan-viewport">
          <LiveFeed fill className="rounded-none border-0" />
        </div>
      </div>

      <div className="auth-scan-panel">
        <p className="auth-scan-label">Captured probe</p>
        <div className="auth-scan-viewport auth-scan-viewport--probe">
          {probeUrl ? (
            <img src={probeUrl} alt="Last palm capture" className="max-h-full max-w-full object-contain" />
          ) : (
            <p className="auth-scan-placeholder">{probePlaceholder}</p>
          )}
        </div>
      </div>
    </div>
  )
}

type AuthMethodTabsProps = {
  value: "palm" | "email"
  onChange: (value: "palm" | "email") => void
  palmLabel?: string
  emailLabel?: string
  showPalm?: boolean
}

export function AuthMethodTabs({
  value,
  onChange,
  palmLabel = "Palm login",
  emailLabel = "Email",
  showPalm = true,
}: AuthMethodTabsProps) {
  if (!showPalm) {
    return null
  }

  return (
    <div className="auth-tab-list" role="tablist" aria-label="Sign in method">
      <button
        type="button"
        role="tab"
        aria-selected={value === "palm"}
        className={cn("auth-tab-trigger", value === "palm" && "auth-tab-trigger--active")}
        onClick={() => onChange("palm")}
      >
        <Camera className="size-4" />
        {palmLabel}
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={value === "email"}
        className={cn("auth-tab-trigger", value === "email" && "auth-tab-trigger--active")}
        onClick={() => onChange("email")}
      >
        <Mail className="size-4" />
        {emailLabel}
      </button>
    </div>
  )
}
