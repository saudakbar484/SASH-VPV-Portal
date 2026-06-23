import { useState } from "react"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { CalendarOff, Trash2 } from "lucide-react"

import { GlassPanel } from "@/components/GlassPanel"

import { Button } from "@/components/ui/button"

import { Input } from "@/components/ui/input"

import { Label } from "@/components/ui/label"

import { endpoints } from "@/lib/api"

export function HolidayCalendarPanel() {
  const queryClient = useQueryClient()
  const [holidayDate, setHolidayDate] = useState("")
  const [holidayName, setHolidayName] = useState("")

  const holidays = useQuery({
    queryKey: ["admin-holidays"],
    queryFn: endpoints.admin.holidays,
  })

  const addHoliday = useMutation({
    mutationFn: () => endpoints.admin.createHoliday({ holiday_date: holidayDate, name: holidayName }),
    onSuccess: () => {
      setHolidayDate("")
      setHolidayName("")
      queryClient.invalidateQueries({ queryKey: ["admin-holidays"] })
    },
  })

  const removeHoliday = useMutation({
    mutationFn: (id: number) => endpoints.admin.deleteHoliday(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-holidays"] }),
  })

  return (
    <GlassPanel title="Holiday calendar" icon={<CalendarOff className="size-5 icon-brand" />}>
      <div className="grid gap-3 md:grid-cols-[auto_1fr_auto] md:items-end">
        <div>
          <Label>Date</Label>
          <Input type="date" value={holidayDate} onChange={(e) => setHolidayDate(e.target.value)} className="mt-1" />
        </div>
        <div>
          <Label>Name</Label>
          <Input
            value={holidayName}
            onChange={(e) => setHolidayName(e.target.value)}
            placeholder="Eid, Independence Day…"
            className="mt-1"
          />
        </div>
        <Button
          className="btn-brand "
          disabled={!holidayDate || !holidayName || addHoliday.isPending}
          onClick={() => addHoliday.mutate()}
        >
          Add holiday
        </Button>
      </div>
      <div className="mt-3 max-h-40 space-y-1 overflow-y-auto text-xs">
        {(holidays.data?.holidays ?? []).map((h) => (
          <div key={h.id} className="flex items-center justify-between rounded border border-white/5 px-2 py-1">
            <span>
              <span className="font-mono">{h.holiday_date}</span> · {h.name}
            </span>
            <Button size="sm" variant="ghost" onClick={() => removeHoliday.mutate(h.id)}>
              <Trash2 className="size-3.5" />
            </Button>
          </div>
        ))}
        {!holidays.data?.holidays.length && (
          <p className="text-[var(--muted-foreground)]">No holidays configured.</p>
        )}
      </div>
    </GlassPanel>
  )
}
