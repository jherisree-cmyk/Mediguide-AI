import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server forwards /api/* to the FastAPI backend, so the browser sees ONE origin:
// the httpOnly session cookie then works without any cross-site settings.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
  test: { environment: "jsdom", setupFiles: "./src/test/setup.js", globals: true },
});
