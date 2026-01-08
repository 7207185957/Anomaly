import dayjs, { Dayjs } from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";

dayjs.extend(utc);
dayjs.extend(timezone);

export type TimeWindowState = {
  lookbackHours: number;
  useDateTimePicker: boolean;
  startLocal: Dayjs | null;
  endLocal: Dayjs | null;
  localTz: string;
};

export function defaultTimeWindow(): TimeWindowState {
  const localTz = "America/Denver";
  const now = dayjs().tz(localTz);
  return {
    lookbackHours: 3,
    useDateTimePicker: false,
    startLocal: now.subtract(1, "day").startOf("day"),
    endLocal: now.endOf("day"),
    localTz
  };
}

export function toUtcIso(d: Dayjs, localTz: string): string {
  return d.tz(localTz).utc().toISOString();
}

export function buildWindowPayload(window: TimeWindowState): {
  lookback_hours: number;
  start_utc?: string;
  end_utc?: string;
} {
  const lookback_hours = Math.max(1, Math.min(168, Math.floor(window.lookbackHours || 3)));

  if (!window.useDateTimePicker || !window.startLocal || !window.endLocal) {
    return { lookback_hours };
  }

  let start = window.startLocal;
  let end = window.endLocal;
  if (end.isBefore(start)) {
    const tmp = start;
    start = end;
    end = tmp;
  }

  return {
    lookback_hours,
    start_utc: toUtcIso(start, window.localTz),
    end_utc: toUtcIso(end, window.localTz)
  };
}

