import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },
    },
    allowedHosts:"86e34084d9c4.ngrok-free.app"
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
