import { Box, FormControlLabel, Stack, Switch, TextField, Typography } from "@mui/material";
import { DateTimePicker, LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import type { Dayjs } from "dayjs";

import type { TimeWindowState } from "../utils/timeWindow";

export function TimeWindowControls(props: {
  value: TimeWindowState;
  onChange: (next: TimeWindowState) => void;
}) {
  const { value, onChange } = props;

  const set = (patch: Partial<TimeWindowState>) => onChange({ ...value, ...patch });

  return (
    <Box>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        Time window controls
      </Typography>
      <Stack spacing={1.5}>
        <TextField
          label="Lookback hours (used when Date/Time picker is OFF)"
          type="number"
          value={value.lookbackHours}
          onChange={(e) => set({ lookbackHours: Number(e.target.value) })}
          inputProps={{ min: 1, max: 168, step: 1 }}
          fullWidth
        />

        <FormControlLabel
          control={
            <Switch
              checked={value.useDateTimePicker}
              onChange={(e) => set({ useDateTimePicker: e.target.checked })}
            />
          }
          label="Use Date/Time picker (overrides lookback_hours)"
        />

        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
            <DateTimePicker
              label="Start (local)"
              value={value.startLocal as Dayjs | null}
              onChange={(d) => set({ startLocal: d })}
              disabled={!value.useDateTimePicker}
              slotProps={{ textField: { fullWidth: true } }}
            />
            <DateTimePicker
              label="End (local)"
              value={value.endLocal as Dayjs | null}
              onChange={(d) => set({ endLocal: d })}
              disabled={!value.useDateTimePicker}
              slotProps={{ textField: { fullWidth: true } }}
            />
          </Stack>
        </LocalizationProvider>

        <TextField
          label="Local timezone"
          value={value.localTz}
          onChange={(e) => set({ localTz: e.target.value })}
          helperText="Used to convert the Date/Time picker window to UTC."
          fullWidth
        />
      </Stack>
    </Box>
  );
}

