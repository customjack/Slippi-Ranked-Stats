import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { nodePolyfills } from "vite-plugin-node-polyfills";

const host = process.env.TAURI_DEV_HOST;

export default defineConfig({
  plugins: [svelte(), nodePolyfills({ globals: { Buffer: true, global: true, process: true } })],
  optimizeDeps: {
    include: ["buffer"],
    // Tauri plugins use window.__TAURI_INTERNALS__ at module init time —
    // exclude from Vite's Node.js pre-bundler or it will crash on load.
    exclude: ["@tauri-apps/plugin-http"],
    esbuildOptions: {
      define: { global: "globalThis" },
    },
  },
  clearScreen: false,
  resolve: {
    dedupe: ["buffer"],
  },
  server: {
    port: 1420,
    strictPort: true,
    host: host || false,
    hmr: host
      ? {
          protocol: "ws",
          host,
          port: 1421,
        }
      : undefined,
    watch: {
      ignored: ["**/src-tauri/**"],
    },
  },
});
