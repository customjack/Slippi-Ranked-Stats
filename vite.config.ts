import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { nodePolyfills } from "vite-plugin-node-polyfills";
import { resolve } from "path";

const host = process.env.TAURI_DEV_HOST;

export default defineConfig({
  plugins: [svelte(), nodePolyfills({ globals: { Buffer: true, global: true, process: true } })],
  optimizeDeps: {
    include: ["buffer", "@slippi/slippi-js"],
    // Tauri plugins use window.__TAURI_INTERNALS__ at module init time —
    // exclude from Vite's Node.js pre-bundler or it will crash on load.
    exclude: ["@tauri-apps/plugin-http"],
    esbuildOptions: {
      define: { global: "globalThis" },
      plugins: [
        {
          // Stub Node-only / server-only packages that slippi-js pulls in transitively.
          name: "stub-node-modules",
          setup(build) {
            build.onResolve(
              { filter: /^(ws|enet|reconnect-core|dns|tls)$/ },
              (args) => ({ path: args.path, namespace: "node-stub" })
            );
            build.onLoad({ filter: /.*/, namespace: "node-stub" }, () => ({
              contents: "module.exports = {}; module.exports.default = {};",
              loader: "js",
            }));
          },
        },
      ],
    },
  },
  clearScreen: false,
  resolve: {
    dedupe: ["buffer"],
    alias: {
      // slippi-js uses iconv-lite to decode Shift_JIS player names during _process().
      // The real iconv-lite requires Node.js; this stub uses the browser's native TextDecoder.
      "iconv-lite": resolve(__dirname, "src/stubs/iconv-lite.ts"),
    },
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
