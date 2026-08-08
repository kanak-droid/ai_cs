import sharedPreset from "@astrohelp/shared/tailwind-preset";
export default {
    presets: [sharedPreset],
    content: ["./index.html", "./src/**/*.{ts,tsx}"],
};
