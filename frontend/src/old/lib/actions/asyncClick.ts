import type { Action } from "svelte/action";

export const asyncClick: Action<
  HTMLButtonElement,
  (e: MouseEvent) => Promise<void>
> = (node, handler) => {
  let currentHandler = handler;
  let running = false;

  async function onClick(e: MouseEvent) {
    if (running || !currentHandler) return;
    running = true;

    const wasDisabled = node.disabled;
    if (!wasDisabled) node.disabled = true;
    node.setAttribute("aria-busy", "true");

    try {
      await currentHandler(e);
    } catch (err) {
      console.error("asyncClick handler error:", err);
    } finally {
      running = false;
      node.removeAttribute("aria-busy");
      if (!wasDisabled) node.disabled = false;
    }
  }

  node.addEventListener("click", onClick);

  return {
    update(newHandler) {
      currentHandler = newHandler;
    },
    destroy() {
      node.removeEventListener("click", onClick);
    },
  };
};
