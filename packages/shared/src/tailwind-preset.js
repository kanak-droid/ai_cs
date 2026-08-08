/**
 * Shared design tokens for both AstroHelp frontends. Colors, type scale, and
 * radii are defined once here and consumed via `presets: [astroHelpPreset]`
 * in each app's tailwind.config.ts — so visual drift between the chat app and
 * the admin dashboard is structurally impossible rather than a matter of
 * discipline.
 *
 * Palette: a muted "dusk sky" — deliberately not the cream+terracotta or
 * teal/purple-gradient look common in AI-generated apps, and not the
 * zodiac-wheel purple-and-gold cliché either. night/harbor/cloudline read as
 * calm and trustworthy for the astrologer-facing support chat; moss/ochre/clay
 * are restrained, universal status colors for the admin dashboard.
 *
 * @type {import('tailwindcss').Config}
 */
module.exports = {
  content: [],
  theme: {
    extend: {
      colors: {
        night: { DEFAULT: "#263449", 700: "#1D2938", 900: "#151D28" },
        harbor: { DEFAULT: "#4A7FA5", 100: "#E3ECF2", 700: "#39647F" },
        cloudline: { DEFAULT: "#EDF1F2" },
        moss: { DEFAULT: "#5C7A5A", 100: "#E4EAE3", 700: "#465F44" },
        ochre: { DEFAULT: "#B8863B", 100: "#F3E7D2", 700: "#8F6A2E" },
        clay: { DEFAULT: "#A6453B", 100: "#F3DEDB", 700: "#7E332B" },
        ink: { DEFAULT: "#1E2530" },
      },
      fontFamily: {
        sans: ["Inter", "Noto Sans", "system-ui", "sans-serif"],
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
