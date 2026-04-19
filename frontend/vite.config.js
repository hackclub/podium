import { sentrySvelteKit } from "@sentry/sveltekit";
import { sveltekit } from "@sveltejs/kit/vite";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [
    tailwindcss(),
    sentrySvelteKit({
      sourceMapsUploadOptions: {
        org: "angad-b",
        project: "podium",
      },
    }),
    sveltekit(),
  ],
  server: {
    host: true,
    strictPort: true,
    allowedHosts: [".ngrok-free.app", ".ngrok.app"],
  },
});
