import { useNavigate } from "react-router-dom"
import { AuthLayout } from "@/components/AuthLayout"
import { PalmVeinLogo } from "@/components/PalmVeinLogo"
import { Button } from "@/components/ui/button"

export function Signup() {
  const navigate = useNavigate()
  return (
    <AuthLayout themePortal="employee" className="items-center justify-center p-6">
      <div className="glass-panel max-w-md p-8 text-center">
        <PalmVeinLogo variant="full" size={72} className="mx-auto mb-4" />
        <h1 className="text-xl font-bold">Registration moved</h1>
        <p className="mt-2 text-sm text-[var(--muted-foreground)]">
          New employees must register using an HR invite link. Contact your administrator.
        </p>
        <Button className="mt-4 w-full btn-brand" onClick={() => navigate("/employee/login")}>
          Employee login
        </Button>
        <Button variant="outline" className="mt-2 w-full" onClick={() => navigate("/login")}>
          Admin login
        </Button>
      </div>
    </AuthLayout>
  )
}
