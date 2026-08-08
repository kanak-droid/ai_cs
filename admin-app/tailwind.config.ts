import sharedPreset from "@astrohelp/shared/tailwind-preset";
import forms from "@tailwindcss/forms";
import type { Config } from "tailwindcss";

export default {
  presets: [sharedPreset],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  plugins: [forms({ strategy: "class" })],
} satisfies Config;
