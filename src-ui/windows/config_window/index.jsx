import React from "react";
import ReactDOM from "react-dom/client";
// import "../locales/config.js";
import { ConfigWindow } from "./ConfigWindow";
// import "./reset.css";
// import "./root.css";
// import { useWindow } from "@utils/useWindow";


ReactDOM.createRoot(document.getElementById("root")).render(
    <React.StrictMode>
        <ConfigWindow />
    </React.StrictMode>,
);

