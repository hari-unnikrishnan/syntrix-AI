import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode, command }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiUrlValue = env.VITE_API_URL?.trim();

  if (command === "build") {
    if (!apiUrlValue) {
      throw new Error(
        "Missing VITE_API_URL. Set it to the deployed Django HTTPS API URL ending in /api (GitHub Actions repository variable or frontend/.env.production); do not use localhost.",
      );
    }

    let apiUrl;
    try {
      apiUrl = new URL(apiUrlValue);
    } catch {
      throw new Error("VITE_API_URL must be an absolute HTTPS URL ending in /api.");
    }

    const localHosts = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);
    if (
      apiUrl.protocol !== "https:" ||
      localHosts.has(apiUrl.hostname.toLowerCase()) ||
      apiUrl.pathname.replace(/\/+$/, "") !== "/api"
    ) {
      throw new Error(
        "Production VITE_API_URL must use HTTPS and point to the deployed Django /api endpoint, not localhost.",
      );
    }
  }

  return {
    base:
      process.env.GITHUB_ACTIONS === "true"
        ? "/syntrix-AI/"
        : env.VITE_BASE_PATH || "/",
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
    },
  };
});
