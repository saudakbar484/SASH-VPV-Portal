import { CustomerPageHeader } from "@/components/customer/CustomerPageHeader"
import { PalmRecognitionPanel } from "@/components/customer/PalmRecognitionPanel"

export function UserScanPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
      <CustomerPageHeader title="Recognition" description="Verify your identity with a live palm scan" />
      <PalmRecognitionPanel />
    </div>
  )
}
