import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

// Самохостинг шрифтов (без внешних <link> на Google Fonts).
// Latin + Cyrillic сабсеты — иначе кириллица упадёт на системный шрифт.
import "@fontsource/unbounded/700.css";
import "@fontsource/unbounded/800.css";
import "@fontsource/unbounded/900.css";
import "@fontsource/unbounded/cyrillic-700.css";
import "@fontsource/unbounded/cyrillic-800.css";
import "@fontsource/unbounded/cyrillic-900.css";
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
import "@fontsource/permanent-marker/400.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
