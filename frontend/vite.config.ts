import { defineConfig } from "vite";
import viteReact from "@vitejs/plugin-react";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import tailwindcss from "@tailwindcss/vite";
import tsConfigPaths from "vite-tsconfig-paths";

// Deploy target: "vercel" on Vercel builds (TANSTACK_TARGET=vercel), default local otherwise.
const target = process.env.TANSTACK_TARGET;

export default defineConfig({
  plugins: [tsConfigPaths(), tailwindcss(), tanstackStart(target ? { target } : {}), viteReact()],
  server: { port: 3000 },
});
