/**
 * Shared design tokens for both AstroHelp frontends. Colors, type scale, and
 * radii are defined once here and consumed via `presets: [astroHelpPreset]`
 * in each app's tailwind.config.ts — so visual drift between the chat app and
 * the admin dashboard is structurally impossible rather than a matter of
 * discipline.
 *
 * Palette: matches the AstroLokal brand itself (warm cream + terracotta +
 * near-black, serif display headings) rather than a generic invented look —
 * the chat webview is opened directly from the AstroLokal app, so it should
 * read as a continuation of that product, not a visually disconnected tool.
 * moss/ochre/clay stay as restrained, universal status colors (success /
 * attention / error) — distinct enough from terracotta to stay legible as
 * status, not brand, color.
 *
 * @type {import('tailwindcss').Config}
 */
module.exports = {
  content: [],
  theme: {
    extend: {
      colors: {
        night: { DEFAULT: "#201C18", 700: "#141110", 900: "#0B0A08" },
        terracotta: { DEFAULT: "#DC5F2A", 100: "#FBE4D3", 700: "#B8481C" },
        cream: { DEFAULT: "#FBF3EA" },
        moss: { DEFAULT: "#5C7A5A", 100: "#E4EAE3", 700: "#465F44" },
        ochre: { DEFAULT: "#B8863B", 100: "#F3E7D2", 700: "#8F6A2E" },
        clay: { DEFAULT: "#A6453B", 100: "#F3DEDB", 700: "#7E332B" },
        ink: { DEFAULT: "#241F19" },
      },
      fontFamily: {
        sans: ["Inter", "Noto Sans", "system-ui", "sans-serif"],
        display: ["Playfair Display", "Georgia", "serif"],
      },
      fontSize: {
        xs: ["0.75rem", { lineHeight: "1rem" }],
        sm: ["0.875rem", { lineHeight: "1.25rem" }],
        base: ["1rem", { lineHeight: "1.5rem" }],
        lg: ["1.125rem", { lineHeight: "1.75rem" }],
        xl: ["1.25rem", { lineHeight: "1.75rem" }],
        "2xl": ["1.5rem", { lineHeight: "2rem" }],
        "3xl": ["1.875rem", { lineHeight: "2.375rem" }],
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "16px",
      },
      maxWidth: {
        content: "1200px",
      },
    },
  },
  plugins: [],
};
