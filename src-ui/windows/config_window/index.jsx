import React from "react";
import ReactDOM from "react-dom/client";
import "@root/locales/config.js";
import "@utils/root.css";

import { ConfigWindow } from "./ConfigWindow";

ReactDOM.createRoot(document.getElementById("root")).render(
    <React.StrictMode>
        <ConfigWindow />
    </React.StrictMode>,
);

