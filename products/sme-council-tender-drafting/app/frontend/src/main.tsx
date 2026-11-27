import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { loadClientConfig } from "./api";
import "./index.css";

// Read the server's timeout once (falls back to 30 s), then render.
void loadClientConfig().then(() => {
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});
