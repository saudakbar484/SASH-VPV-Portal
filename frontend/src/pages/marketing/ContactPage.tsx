import { useState } from "react"

import { Link } from "react-router-dom"

import { useMutation } from "@tanstack/react-query"

import { Loader2, Mail } from "lucide-react"

import { MarketingPageHero } from "@/components/marketing/MarketingPageHero"
import { ProjectTeamSection } from "@/components/marketing/ProjectTeamSection"
import { Button } from "@/components/ui/button"
import { Input, fieldClassName } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { endpoints } from "@/lib/api"

export function ContactPage() {
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [organization, setOrganization] = useState("")
  const [subject, setSubject] = useState("Sales")
  const [message, setMessage] = useState("")
  const [sent, setSent] = useState<string | null>(null)

  const submit = useMutation({
    mutationFn: () =>
      endpoints.public.contact({ name, email, organization: organization || undefined, subject, message }),
    onSuccess: (data) => setSent(data.message),
  })

  return (
    <div>
      <MarketingPageHero
        icon={Mail}
        eyebrow="Get in touch"
        title="Contact us"
        description="Reach the NUTECH palm vein research team for academic inquiries, technical support, and partnership opportunities."
      />
      <div className="mx-auto max-w-6xl space-y-14 px-6 py-12">
        <div className="grid gap-8 lg:grid-cols-5">
          <form
            className="customer-card space-y-4 p-6 lg:col-span-3"
            onSubmit={(e) => {
              e.preventDefault()
              submit.mutate()
            }}
          >
            <h2 className="text-lg font-semibold">Send a message</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="name">Name</Label>
                <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="org">Organization</Label>
              <Input id="org" value={organization} onChange={(e) => setOrganization(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="subject">Subject</Label>
              <select
                id="subject"
                className={fieldClassName}
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
              >
                <option>Sales</option>
                <option>Support</option>
                <option>Partnership</option>
                <option>Academic inquiry</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="message">Message</Label>
              <textarea
                id="message"
                className={fieldClassName}
                rows={5}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                required
              />
            </div>
            <Button type="submit" className="btn-brand w-full" disabled={submit.isPending}>
              {submit.isPending ? <Loader2 className="animate-spin" /> : "Send message"}
            </Button>
            {sent && <p className="text-sm text-emerald-600">{sent}</p>}
          </form>

          <aside className="customer-card space-y-6 p-6 lg:col-span-2">
            <div>
              <h2 className="font-semibold">Support hours</h2>
              <p className="mt-2 text-sm text-[var(--muted-foreground)]">Mon–Fri, 9:00–18:00 (PKT)</p>
            </div>
            <div>
              <h2 className="font-semibold">Direct email</h2>
              <p className="mt-2 text-sm text-[var(--muted-foreground)]">
                For project-related questions, email any team member listed below or use the contact form.
              </p>
            </div>
            <div>
              <h2 className="font-semibold">Documentation</h2>
              <p className="mt-2 text-sm text-[var(--muted-foreground)]">
                See{" "}
                <Link to="/how-it-works" className="text-[var(--primary)] hover:underline">
                  How it works
                </Link>{" "}
                and{" "}
                <Link to="/security" className="text-[var(--primary)] hover:underline">
                  Security
                </Link>{" "}
                for technical details.
              </p>
            </div>
          </aside>
        </div>

        <ProjectTeamSection />
      </div>
    </div>
  )
}
