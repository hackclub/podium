// import adapter from '@sveltejs/adapter-static';
import adapter from "@sveltejs/adapter-vercel";

/** @type {import('@sveltejs/kit').Config} */
const config = {
  kit: {
    // See https://kit.svelte.dev/docs/adapters for more information about adapters.
    // adapter: adapter({
    // 	// https://khromov.se/the-missing-guide-to-understanding-adapter-static-in-sveltekit/
    // 	// npm run build && npx http-server ./build
    // 	pages: 'build',
    // 	assets: 'build',
    // 	fallback: "404.html",
    // 	precompress: false,
    // 	strict: true
    // }),
    adapter: adapter({ runtime: 'nodejs22.x' }),
    alias: {
      $lib: "src/lib",
    },
  },
};

export default config;
