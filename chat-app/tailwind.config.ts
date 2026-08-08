import sharedPreset from "@astrohelp/shared/tailwind-preset";
import type { Config } from "tailwindcss";

export default {
  presets: [sharedPreset],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
} satisfies Config;
