import type { ChatTraceStep } from "@astrohelp/shared";

// Deliberately quiet: no color, no animation, no icons that compete with the
// reply itself — just a small line confirming what happened, so the astrologer
// never wonders "did it actually check?" without it reading as a second,
// noisier notification stream.
export function ToolActionIndicator({ trace }: { trace: ChatTraceStep[] }) {
  if (trace.length === 0) return null;

  return (
    <ul className="mb-1 flex flex-col gap-0.5 self-start pl-1 text-xs text-night/45">
      {trace.map((step, i) => (
        <li key={`${step.tool}-${i}`}>{step.ok ? step.summary : `Couldn't complete: ${step.summary}`}</li>
      ))}
    </ul>
  );
}
