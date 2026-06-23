interface AdminPageHeaderProps {
  title: string
  description: string
}

export function AdminPageHeader({ title, description }: AdminPageHeaderProps) {
  return (
    <div className="border-b border-[var(--border)] pb-5">
      <div className="flex items-center gap-2">
        <span className="rounded-md bg-[color-mix(in_srgb,var(--primary)_18%,transparent)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--primary-muted)]">
          Admin
        </span>
      </div>
      <h1 className="mt-2 text-2xl font-bold tracking-tight text-[var(--foreground)]">{title}</h1>
      <p className="mt-1 max-w-2xl text-sm leading-relaxed text-[var(--muted-foreground)]">{description}</p>
    </div>
  )
}
