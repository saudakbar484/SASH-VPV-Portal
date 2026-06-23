import { Layers } from "lucide-react"

import { MarketingPageHero } from "@/components/marketing/MarketingPageHero"
import { PortalCards } from "@/components/marketing/PortalCards"

export function SolutionsPage() {
  return (
    <div>
      <MarketingPageHero
        icon={Layers}
        eyebrow="Use cases"
        title="Solutions for every role"
        description="Whether you are enrolling members, tracking staff attendance, running a lobby kiosk, or operating the full biometric platform — each portal is tailored to the job."
      />

      <div className="mx-auto max-w-6xl px-6 py-12 pb-16">
        <PortalCards showHeader={false} />
      </div>
    </div>
  )
}
