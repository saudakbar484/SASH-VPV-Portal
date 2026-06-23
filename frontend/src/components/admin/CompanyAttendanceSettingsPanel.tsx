import { useEffect, useState } from "react"



import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"



import { Settings2 } from "lucide-react"



import { GlassPanel } from "@/components/GlassPanel"



import { Button } from "@/components/ui/button"



import { Input } from "@/components/ui/input"



import { Label } from "@/components/ui/label"



import { endpoints } from "@/lib/api"



export function CompanyAttendanceSettingsPanel() {

  const queryClient = useQueryClient()

  const [settingsDraft, setSettingsDraft] = useState({

    work_day_start: "09:00",

    grace_minutes: 30,

    timezone: "UTC",

    require_palm_logout: true,

    exclude_weekends: true,

    half_day_hours: 4,

  })



  const settings = useQuery({

    queryKey: ["admin-attendance-settings"],

    queryFn: endpoints.admin.attendanceSettings,

  })



  useEffect(() => {

    if (settings.data) {

      setSettingsDraft({

        work_day_start: settings.data.work_day_start,

        grace_minutes: settings.data.grace_minutes,

        timezone: settings.data.timezone,

        require_palm_logout: settings.data.require_palm_logout,

        exclude_weekends: settings.data.exclude_weekends,

        half_day_hours: settings.data.half_day_hours,

      })

    }

  }, [settings.data])



  const saveSettings = useMutation({

    mutationFn: () => endpoints.admin.updateAttendanceSettings(settingsDraft),

    onSuccess: () => {

      queryClient.invalidateQueries({ queryKey: ["admin-attendance-settings"] })

    },

  })



  return (

    <GlassPanel title="Company attendance settings" icon={<Settings2 className="size-5 icon-brand" />}>

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">

        <div>

          <Label>Work day start</Label>

          <Input

            type="time"

            value={settingsDraft.work_day_start}

            onChange={(e) => setSettingsDraft((s) => ({ ...s, work_day_start: e.target.value }))}

            className="mt-1"

          />

        </div>

        <div>

          <Label>Grace period (minutes)</Label>

          <Input

            type="number"

            min={0}

            max={240}

            value={settingsDraft.grace_minutes}

            onChange={(e) =>

              setSettingsDraft((s) => ({ ...s, grace_minutes: Number(e.target.value) || 0 }))

            }

            className="mt-1"

          />

        </div>

        <div>

          <Label>Half-day threshold (hours)</Label>

          <Input

            type="number"

            min={0.5}

            max={12}

            step={0.5}

            value={settingsDraft.half_day_hours}

            onChange={(e) =>

              setSettingsDraft((s) => ({ ...s, half_day_hours: Number(e.target.value) || 4 }))

            }

            className="mt-1"

          />

        </div>

        <div>

          <Label>Timezone</Label>

          <Input

            value={settingsDraft.timezone}

            onChange={(e) => setSettingsDraft((s) => ({ ...s, timezone: e.target.value }))}

            placeholder="Asia/Karachi"

            className="mt-1"

          />

        </div>

      </div>

      <div className="mt-3 flex flex-wrap gap-4 text-sm">

        <label className="flex items-center gap-2">

          <input

            type="checkbox"

            checked={settingsDraft.require_palm_logout}

            onChange={(e) =>

              setSettingsDraft((s) => ({ ...s, require_palm_logout: e.target.checked }))

            }

          />

          Require palm logout

        </label>

        <label className="flex items-center gap-2">

          <input

            type="checkbox"

            checked={settingsDraft.exclude_weekends}

            onChange={(e) =>

              setSettingsDraft((s) => ({ ...s, exclude_weekends: e.target.checked }))

            }

          />

          Exclude weekends

        </label>

      </div>

      <div className="mt-3 flex flex-wrap gap-2">

        <Button

          className="btn-brand "

          disabled={saveSettings.isPending}

          onClick={() => saveSettings.mutate()}

        >

          Save settings

        </Button>

      </div>

    </GlassPanel>

  )

}


