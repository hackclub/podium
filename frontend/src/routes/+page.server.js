import { redirect } from "@sveltejs/kit";

export function load() {
	if (import.meta.env.DEV) { 
		console.log("In dev, not redirecting to hack.club/submit");
		return;
	}
	redirect(307, "https://hack.club/submit");
}