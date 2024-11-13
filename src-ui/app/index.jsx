import React from "react";
import ReactDOM from "react-dom/client";
import "@root/locales/config.js";
import "./_index_css/root.css";

import { App } from "./App";

ReactDOM.createRoot(document.getElementById("root")).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>,
);