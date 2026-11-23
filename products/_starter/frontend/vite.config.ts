import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

// In dev and preview, the API is proxied so the browser sees one origin and the session cookie just works.
const api = process.env.API_URL ?? "http://127.0.0.1:8000";
const proxy = { "/api": api, "/healthz": api };

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173, proxy },
  preview: { port: 4173, proxy },
});
