import sharedPreset from "@astrohelp/shared/tailwind-preset";
import forms from "@tailwindcss/forms";
export default {
    presets: [sharedPreset],
    content: ["./index.html", "./src/**/*.{ts,tsx}"],
    plugins: [forms({ strategy: "class" })],
};
