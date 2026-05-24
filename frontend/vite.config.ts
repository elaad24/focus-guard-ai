import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backendPort = process.env.FOCUS_GUARD_PORT ?? "8787";
const backendTarget = `http://127.0.0.1:${backendPort}`;

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5700,
    strictPort: true,
    host: "127.0.0.1",
    proxy: {
      "/api": {
        target: backendTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/ws": {
        target: backendTarget,
        ws: true,
      },
    },
  },
});
