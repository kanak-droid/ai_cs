import type { Astrologer } from "@astrohelp/shared";

export function ContactInfoCard({ astrologer }: { astrologer: Astrologer }) {
  return (
    <div className="rounded-xl border border-night/10 p-4">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-night/40">Astrologer</p>
      <p className="text-sm font-medium text-night">{astrologer.name}</p>
      <p className="text-sm text-night/60">{astrologer.phone}</p>
      <p className="text-xs text-night/40">Prefers {astrologer.language}</p>
      {astrologer.priority !== null && (
        <p className="text-xs text-night/40">
          Priority P{astrologer.priority}
          {astrologer.priority <= 2 ? " (VIP)" : ""}
        </p>
      )}
      <p className="mt-1 text-xs text-night/30">
        ID #{astrologer.id} · Expert ID {astrologer.expert_id ?? "not linked"}
      </p>
    </div>
  );
}
