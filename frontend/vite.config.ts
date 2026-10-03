import { defineConfig } from "vite";

// The client imports ../examples/*.json so it renders before the backend exists.
export default defineConfig({
  server: { port: 5173, fs: { allow: [".."] } },
});
