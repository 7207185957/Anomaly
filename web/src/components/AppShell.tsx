import { PropsWithChildren, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
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
  Typography
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import NotificationsActiveIcon from "@mui/icons-material/NotificationsActive";
import FactCheckIcon from "@mui/icons-material/FactCheck";

const drawerWidth = 280;

export function AppShell({ children }: PropsWithChildren) {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const nav = [
    { to: "/incidents", label: "Incidents", icon: <WarningAmberIcon /> },
    { to: "/alerts", label: "Alerts", icon: <NotificationsActiveIcon /> },
    { to: "/rca", label: "RCA Report", icon: <FactCheckIcon /> }
  ];

  const drawer = (
    <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <Box sx={{ px: 2, py: 2 }}>
        <Typography variant="subtitle2" sx={{ opacity: 0.7 }}>
          Real time AIOps
        </Typography>
        <Typography variant="h6" component={Link} to="/incidents" sx={{ textDecoration: "none", color: "inherit" }}>
          Executive Console
        </Typography>
      </Box>
      <List sx={{ px: 1 }}>
        {nav.map((n) => (
          <ListItemButton
            key={n.to}
            component={NavLink}
            to={n.to}
            selected={location.pathname === n.to}
            sx={{ borderRadius: 2, mb: 0.5 }}
          >
            <ListItemIcon sx={{ minWidth: 42 }}>{n.icon}</ListItemIcon>
            <ListItemText primary={n.label} />
          </ListItemButton>
        ))}
      </List>
      <Box sx={{ flex: 1 }} />
      <Box sx={{ px: 2, py: 2, opacity: 0.7 }}>
        <Typography variant="caption">API: {import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:9010"}</Typography>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <AppBar position="fixed" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }}>
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={() => setMobileOpen((v) => !v)}
            sx={{ mr: 2, display: { md: "none" } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div">
            Real time AIOps
          </Typography>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: "block", md: "none" },
            "& .MuiDrawer-paper": { width: drawerWidth }
          }}
        >
          {drawer}
        </Drawer>

        <Drawer
          variant="permanent"
          sx={{
            display: { xs: "none", md: "block" },
            "& .MuiDrawer-paper": { width: drawerWidth, boxSizing: "border-box" }
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Box component="main" sx={{ flexGrow: 1, p: 3, pt: 10 }}>
        {children}
      </Box>
    </Box>
  );
}

