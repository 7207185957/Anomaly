"use client";

import DashboardIcon from "@mui/icons-material/Dashboard";
import HubIcon from "@mui/icons-material/Hub";
import InsightsIcon from "@mui/icons-material/Insights";
import LoginIcon from "@mui/icons-material/Login";
import ReportIcon from "@mui/icons-material/Report";
import SearchIcon from "@mui/icons-material/Search";
import StorageIcon from "@mui/icons-material/Storage";
import {
  AppBar,
  Box,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
} from "@mui/material";
import { PropsWithChildren, ReactNode } from "react";

export type DashboardSection =
  | "incidents"
  | "alerts"
  | "health"
  | "logs"
  | "topology"
  | "jobs";

const drawerWidth = 250;

const sections: Array<{ id: DashboardSection; label: string; icon: ReactNode }> = [
  { id: "incidents", label: "Incident Command", icon: <ReportIcon /> },
  { id: "alerts", label: "Alerts Explorer", icon: <SearchIcon /> },
  { id: "health", label: "Health Dashboards", icon: <InsightsIcon /> },
  { id: "logs", label: "Logs Insight", icon: <StorageIcon /> },
  { id: "topology", label: "Topology", icon: <HubIcon /> },
  { id: "jobs", label: "RCA Jobs", icon: <DashboardIcon /> },
];

type AppShellProps = PropsWithChildren<{
  section: DashboardSection;
  onSectionChange: (section: DashboardSection) => void;
  title: string;
  onLogout: () => void;
  username?: string;
}>;

export function AppShell({
  section,
  onSectionChange,
  title,
  children,
  onLogout,
  username,
}: AppShellProps) {
  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <AppBar
        position="fixed"
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 1,
          borderBottom: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <Toolbar sx={{ display: "flex", justifyContent: "space-between" }}>
          <Typography variant="h6">{title}</Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              {username || "Unknown User"}
            </Typography>
            <IconButton color="inherit" onClick={onLogout} title="Logout">
              <LoginIcon />
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: {
            width: drawerWidth,
            boxSizing: "border-box",
            borderRight: "1px solid rgba(255,255,255,0.08)",
            background: "#0B1220",
          },
        }}
      >
        <Toolbar />
        <Box sx={{ p: 1 }}>
          <List>
            {sections.map((item) => (
              <ListItemButton
                key={item.id}
                selected={section === item.id}
                onClick={() => onSectionChange(item.id)}
                sx={{ borderRadius: 2, mb: 0.5 }}
              >
                <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItemButton>
            ))}
          </List>
        </Box>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        {children}
      </Box>
    </Box>
  );
}

