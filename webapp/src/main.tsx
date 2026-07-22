import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

// Самохостинг шрифтов (без внешних <link> на Google Fonts).
// Latin + Cyrillic сабсеты — иначе кириллица упадёт на системный шрифт.
// Comfortaa — округлый дисплейный (ближайший к леттерингу афиши),
// Caveat — рукописный акцент («что в программе?» на афише).
import "@fontsource/comfortaa/400.css";
import "@fontsource/comfortaa/700.css";
import "@fontsource/comfortaa/cyrillic-400.css";
import "@fontsource/comfortaa/cyrillic-700.css";
import "@fontsource/caveat/400.css";
import "@fontsource/caveat/700.css";
import "@fontsource/caveat/cyrillic-400.css";
import "@fontsource/caveat/cyrillic-700.css";
import "@fontsource/manrope/400.css";
import "@fontsource/manrope/500.css";
import "@fontsource/manrope/700.css";
import "@fontsource/manrope/800.css";
import "@fontsource/manrope/cyrillic-400.css";
import "@fontsource/manrope/cyrillic-500.css";
import "@fontsource/manrope/cyrillic-700.css";
import "@fontsource/manrope/cyrillic-800.css";
import "@fontsource/jetbrains-mono/500.css";
import "@fontsource/jetbrains-mono/700.css";
import "@fontsource/jetbrains-mono/cyrillic-500.css";
import "@fontsource/jetbrains-mono/cyrillic-700.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
