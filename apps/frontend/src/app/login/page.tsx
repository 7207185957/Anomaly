"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Alert, Box, Button, Card, CardContent, CircularProgress, Stack, TextField, Typography } from "@mui/material";
import { AxiosError } from "axios";

import { env } from "@/config/env";
import { useAuthMode, useLogin } from "@/hooks/useAIOpsApi";
import { getAccessToken, setAccessToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const login = useLogin();
  const authMode = useAuthMode();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const loginErrorText = useMemo(() => {
    if (!login.error) return "";
    const err = login.error as AxiosError<{ detail?: string }>;
    return err.response?.data?.detail || err.message || "Login failed";
  }, [login.error]);

  useEffect(() => {
    if (getAccessToken()) {
      router.replace("/");
    }
  }, [router]);

  return (
    <Box sx={{ display: "grid", placeItems: "center", minHeight: "100vh" }}>
      <Card sx={{ width: 460 }}>
        <CardContent>
          <Typography variant="h5" sx={{ mb: 2 }}>
            Enterprise AIOps Login
          </Typography>
          <Typography variant="body2" sx={{ opacity: 0.8, mb: 3 }}>
            Authenticate using LDAP credentials.
          </Typography>
          {authMode.data?.demo_mode ? (
            <Alert severity="info" sx={{ mb: 2 }}>
              Backend is in Demo Mode. Demo username hint:{" "}
              <strong>{authMode.data.demo_username_hint || env.demoUsername}</strong>
            </Alert>
          ) : (
            env.demoMode && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                Frontend demo mode is enabled, but backend reports LDAP mode. Set{" "}
                <code>DEMO_MODE=true</code> for backend and rebuild.
              </Alert>
            )
          )}
          {env.demoMode && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Demo mode active. Use <strong>{env.demoUsername}</strong> /{" "}
              <strong>{env.demoPassword}</strong> or click Auto-fill.
            </Alert>
          )}
          <Stack spacing={2}>
            <TextField
              label="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
            <TextField
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
            {env.demoMode && (
              <Button
                variant="outlined"
                onClick={() => {
                  setUsername(env.demoUsername);
                  setPassword(env.demoPassword);
                }}
              >
                Auto-fill demo credentials
              </Button>
            )}
            <Button
              variant="contained"
              disabled={!username || !password || login.isPending}
              onClick={async () => {
                try {
                  const data = await login.mutateAsync({ username, password });
                  setAccessToken(data.access_token);
                  router.push("/");
                } catch {
                  // Error handled below
                }
              }}
            >
              Sign in
            </Button>
            {login.isPending && <CircularProgress size={22} />}
            {login.isError && <Alert severity="error">Login failed: {loginErrorText}</Alert>}
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}

