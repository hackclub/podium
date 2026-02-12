import type { PageLoad } from "./$types";

export const load: PageLoad = async () => {
  while (true) {
    console.log("Looping forever...");
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
};
