"use client";

import { Box, FormControlLabel, Switch, TextField } from "@mui/material";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import { useMemo } from "react";

import { TimeWindowPayload } from "@/types/api";

dayjs.extend(utc);

export type WindowState = {
  keyword: string;
  lookbackHours: number;
  customWindow: boolean;
  startUtc: string;
  endUtc: string;
};

type Props = {
  value: WindowState;
  onChange: (next: WindowState) => void;
};

export function TimeWindowControls({ value, onChange }: Props) {
  const payload = useMemo<TimeWindowPayload>(() => {
    if (value.customWindow) {
      return {
        keyword: value.keyword,
        start_utc: value.startUtc,
        end_utc: value.endUtc,
      };
    }
    return { keyword: value.keyword, lookback_hours: value.lookbackHours };
  }, [value]);

  return (
    <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr" }}>
      <TextField
        label="Keyword / Service"
        value={value.keyword}
        onChange={(e) => onChange({ ...value, keyword: e.target.value })}
        placeholder="airflow, scheduler, rabbitmq..."
      />
      <TextField
        label="Lookback hours"
        type="number"
        disabled={value.customWindow}
        value={value.lookbackHours}
        inputProps={{ min: 1, max: 168 }}
        onChange={(e) =>
          onChange({
            ...value,
            lookbackHours: Number(e.target.value || 1),
          })
        }
      />
      <FormControlLabel
        label="Custom window"
        control={
          <Switch
            checked={value.customWindow}
            onChange={(e) => onChange({ ...value, customWindow: e.target.checked })}
          />
        }
      />
      <TextField
        label="Start UTC"
        type="datetime-local"
        disabled={!value.customWindow}
        value={dayjs(value.startUtc).utc().format("YYYY-MM-DDTHH:mm")}
        onChange={(e) =>
          onChange({
            ...value,
            startUtc: dayjs.utc(e.target.value).toISOString(),
          })
        }
      />
      <TextField
        label="End UTC"
        type="datetime-local"
        disabled={!value.customWindow}
        value={dayjs(value.endUtc).utc().format("YYYY-MM-DDTHH:mm")}
        onChange={(e) =>
          onChange({
            ...value,
            endUtc: dayjs.utc(e.target.value).toISOString(),
          })
        }
      />
      <Box sx={{ gridColumn: "1 / -1", opacity: 0.75, fontSize: 12 }}>
        API payload preview: {JSON.stringify(payload)}
      </Box>
    </Box>
  );
}

