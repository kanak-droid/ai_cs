interface TranscriptLine {
  role: "astrologer" | "agent";
  text: string;
}

function parseTranscript(raw: string): TranscriptLine[] {
  const lines: TranscriptLine[] = [];
  const regex = /^(Astrologer|Agent): ([\s\S]*?)(?=\n(?:Astrologer|Agent): |$)/gm;
  let match;
  while ((match = regex.exec(raw)) !== null) {
    const text = match[2].trim();
    if (!text) continue;
    lines.push({
      role: match[1] === "Astrologer" ? "astrologer" : "agent",
      text,
    });
  }
  return lines;
}

export function TranscriptCard({ transcript }: { transcript: string | null }) {
  const lines = transcript ? parseTranscript(transcript) : [];

  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm">
      <h2 className="mb-4 text-sm font-semibold text-night">Transcript</h2>
      {lines.length === 0 ? (
        <p className="text-sm text-night/40">No transcript available for this call.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {lines.map((line, i) => (
            <div
              key={i}
              className={`flex ${line.role === "astrologer" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-lg rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  line.role === "astrologer"
                    ? "bg-terracotta text-white"
                    : "border border-night/10 bg-cream text-ink"
                }`}
              >
                <p
                  className={`mb-1 text-xs font-semibold ${
                    line.role === "astrologer" ? "text-white/70" : "text-night/40"
                  }`}
                >
                  {line.role === "astrologer" ? "Caller" : "AI Agent"}
                </p>
                {line.text}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
