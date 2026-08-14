// Astrologer profile names are usually "<practice-title> <personal name>"
// ("Astro Hemant", "Face Reader Priyam", "Tarot Zeenie") rather than a plain
// personal name — stripped so the welcome greeting uses the name a person
// actually goes by, not their professional branding. Mirrors the same list
// in backend/app/agent/prompt.py (kept in sync manually, not shared code —
// this one only needs to run once per page load, not worth wiring up a
// shared package entry for).
const TITLE_PREFIXES = new Set([
  "astro", "tarot", "acharya", "aacharya", "acharjee", "numero", "palmist",
  "palmistry", "facereader", "face", "reader", "vedic", "pandit", "life",
  "mystic", "jyotish", "jyotishi", "guruji", "guruma", "prashana", "vastu",
  "nadi", "dr", "psychic", "taraputra",
]);

export function casualFirstName(fullName: string): string {
  const tokens = fullName.trim().split(/[\s-]+/).filter(Boolean);
  if (tokens.length === 0) return fullName;
  let i = 0;
  while (i < tokens.length - 1 && TITLE_PREFIXES.has(tokens[i].toLowerCase())) {
    i++;
  }
  return tokens[i];
}
