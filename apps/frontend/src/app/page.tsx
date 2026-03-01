"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Alert, Card, CardContent, Stack, Typography } from "@mui/material";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { TimeWindowControls, WindowState } from "@/components/common/TimeWindowControls";
import { AppShell, DashboardSection } from "@/components/layout/AppShell";
import { env } from "@/config/env";
import { useCurrentUser } from "@/hooks/useAIOpsApi";
import { clearAccessToken, getAccessToken } from "@/lib/auth";
import { AlertsModule } from "@/modules/alerts/AlertsModule";
import { HealthModule } from "@/modules/health/HealthModule";
import { IncidentsModule } from "@/modules/incidents/IncidentsModule";
import { RcaJobsModule } from "@/modules/jobs/RcaJobsModule";
import { LogsModule } from "@/modules/logs/LogsModule";
import { TopologyModule } from "@/modules/topology/TopologyModule";
import { TimeWindowPayload } from "@/types/api";

dayjs.extend(utc);

const initialWindow: WindowState = {
  keyword: "",
  lookbackHours: 3,
  customWindow: false,
  startUtc: dayjs().utc().subtract(3, "hour").toISOString(),
  endUtc: dayjs().utc().toISOString(),
};

export default function Home() {
  const router = useRouter();
  const [section, setSection] = useState<DashboardSection>("incidents");
  const [windowState, setWindowState] = useState<WindowState>(initialWindow);
  const token = getAccessToken();
  const hasToken = Boolean(token);

  useEffect(() => {
    if (!hasToken) {
      router.replace("/login");
    }
  }, [hasToken, router]);

  const me = useCurrentUser(hasToken);
  const payload = useMemo<TimeWindowPayload>(() => {
    if (windowState.customWindow) {
      return {
        keyword: windowState.keyword.trim(),
        start_utc: windowState.startUtc,
        end_utc: windowState.endUtc,
      };
    }
    return {
      keyword: windowState.keyword.trim(),
      lookback_hours: Number(windowState.lookbackHours || 3),
    };
  }, [windowState]);

  if (!hasToken) return null;

  const keywordReady = Boolean(payload.keyword);

  return (
    <AppShell
      title="Enterprise AIOps Control Plane"
      section={section}
      onSectionChange={setSection}
      username={me.data?.display_name}
      onLogout={() => {
        clearAccessToken();
        router.push("/login");
      }}
    >
      <Stack spacing={2}>
        <Card>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 1 }}>
              Global Time Window & Scope
            </Typography>
            <TimeWindowControls value={windowState} onChange={setWindowState} />
          </CardContent>
        </Card>

        {env.demoMode && (
          <Alert severity="info">
            Demo mode is enabled. Data in all sections is synthetic and safe for walkthroughs.
          </Alert>
        )}

        {me.isError && (
          <Alert severity="error">
            Session check failed. Please re-authenticate.
          </Alert>
        )}

        {section === "incidents" && <IncidentsModule payload={payload} enabled />}
        {section === "alerts" && <AlertsModule payload={payload} enabled={keywordReady} />}
        {section === "health" && <HealthModule payload={payload} enabled={keywordReady} />}
        {section === "logs" && <LogsModule payload={payload} enabled={keywordReady} />}
        {section === "topology" && (
          <TopologyModule keyword={payload.keyword} enabled={keywordReady} />
        )}
        {section === "jobs" && <RcaJobsModule keyword={payload.keyword} enabled={keywordReady} />}
      </Stack>
    </AppShell>
  );
}
