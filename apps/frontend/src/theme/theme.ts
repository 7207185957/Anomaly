import { createTheme } from "@mui/material/styles";

export const appTheme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#00B8D9",
    },
    secondary: {
      main: "#FFAB00",
    },
    background: {
      default: "#0D1117",
      paper: "#161B22",
    },
  },
  shape: {
    borderRadius: 10,
  },
  typography: {
    fontFamily: "Inter, Arial, Helvetica, sans-serif",
    h4: {
      fontWeight: 700,
    },
    h5: {
      fontWeight: 700,
    },
    h6: {
      fontWeight: 700,
    },
  },
  components: {
    MuiAppBar: {
      styleOverrides: {
        root: {
          background: "rgba(11, 18, 32, 0.80)",
          backdropFilter: "blur(8px)",
          boxShadow: "0 10px 24px rgba(0,0,0,0.28)",
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          border: "1px solid rgba(148, 163, 184, 0.14)",
          background: "linear-gradient(145deg, rgba(22,27,34,0.93) 0%, rgba(17,24,39,0.95) 100%)",
          boxShadow: "0 10px 28px rgba(0,0,0,0.28)",
          backdropFilter: "blur(6px)",
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          "&.Mui-selected": {
            background: "linear-gradient(140deg, rgba(0,184,217,0.28) 0%, rgba(66,165,245,0.18) 100%)",
          },
        },
      },
    },
  },
});

