import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    mode: "dark",
    primary: { main: "#3B82F6" },
    secondary: { main: "#F59E0B" },
    background: {
      default: "#0B1220",
      paper: "#0F1A2B"
    }
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily:
      'Inter, system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans", "Liberation Sans", sans-serif'
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          border: "1px solid rgba(148,163,184,0.18)",
          backgroundImage: "none"
        }
      }
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          borderBottom: "1px solid rgba(148,163,184,0.18)"
        }
      }
    }
  }
});

