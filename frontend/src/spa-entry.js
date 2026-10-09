// Client-only entry for the React Router SPA (was src/index.js under CRA).
import React from "react";
import "@/lib/backendUrlFallback";
import "@/lib/analytics";
import App from "@/App";

export default function SpaEntry() {
  return (
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}
