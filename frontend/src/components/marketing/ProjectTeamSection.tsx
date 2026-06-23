import { GraduationCap, Mail, UserRound } from "lucide-react"

import { PROJECT_MEMBERS, PROJECT_SUPERVISOR, PROJECT_UNIVERSITY } from "@/lib/projectTeam"
import { cn } from "@/lib/utils"

type ProjectTeamSectionProps = {
  className?: string
  compact?: boolean
}

export function ProjectTeamSection({ className, compact = false }: ProjectTeamSectionProps) {
  return (
    <section className={cn("space-y-6", className)} aria-labelledby="project-team-heading">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--primary)]">NUTECH · Islamabad</p>
        <h2 id="project-team-heading" className="mt-2 text-2xl font-bold tracking-tight">
          Project team
        </h2>
        <p className="mx-auto mt-2 max-w-2xl text-sm text-[var(--muted-foreground)]">
          {PROJECT_UNIVERSITY.name} — final-year research project on custom NIR palm vein recognition.
        </p>
      </div>

      <div
        className={cn(
          "grid gap-4",
          compact ? "sm:grid-cols-2" : "sm:grid-cols-2 lg:grid-cols-3",
        )}
      >
        {PROJECT_MEMBERS.map((member) => (
          <article key={member.email} className="customer-card flex flex-col gap-3 p-5">
            <div className="flex items-start gap-3">
              <div className="marketing-icon-ring flex size-10 shrink-0 items-center justify-center rounded-full">
                <UserRound className="size-5 text-[var(--primary)]" />
              </div>
              <div className="min-w-0">
                <h3 className="font-semibold leading-snug">{member.name}</h3>
                {"role" in member && member.role ? (
                  <p className="mt-0.5 text-xs font-medium text-[var(--primary)]">{member.role}</p>
                ) : (
                  <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">Project member</p>
                )}
              </div>
            </div>
            <a
              href={`mailto:${member.email}`}
              className="inline-flex items-center gap-2 text-sm text-[var(--muted-foreground)] transition-colors hover:text-[var(--primary)]"
            >
              <Mail className="size-3.5 shrink-0" />
              <span className="truncate">{member.email}</span>
            </a>
          </article>
        ))}
      </div>

      <article className="customer-card flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-4">
          <div className="marketing-icon-ring flex size-12 shrink-0 items-center justify-center rounded-full">
            <GraduationCap className="size-6 text-[var(--primary)]" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-[var(--primary)]">Supervisor</p>
            <h3 className="mt-1 text-lg font-semibold">{PROJECT_SUPERVISOR.name}</h3>
            <p className="text-sm text-[var(--muted-foreground)]">{PROJECT_SUPERVISOR.title}</p>
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">{PROJECT_UNIVERSITY.name}</p>
          </div>
        </div>
        <a
          href={`mailto:${PROJECT_SUPERVISOR.email}`}
          className="inline-flex items-center gap-2 text-sm font-medium text-[var(--primary)] hover:underline sm:shrink-0"
        >
          <Mail className="size-4" />
          {PROJECT_SUPERVISOR.email}
        </a>
      </article>
    </section>
  )
}
