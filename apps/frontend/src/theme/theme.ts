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
});

