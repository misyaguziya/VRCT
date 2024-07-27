import React from "react";
import ReactDOM from "react-dom/client";
import "@root/locales/config.js";
import "@utils/root.css";

import { MainWindow } from "./MainWindow";

ReactDOM.createRoot(document.getElementById("root")).render(
    <React.StrictMode>
        <MainWindow />
    </React.StrictMode>,
);