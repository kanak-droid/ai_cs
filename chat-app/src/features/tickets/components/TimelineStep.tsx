type StepState = "done" | "current" | "upcoming";

interface TimelineStepProps {
  label: string;
  state: StepState;
  timestamp?: string;
  note?: string;
  isLast: boolean;
}

export function TimelineStep({ label, state, timestamp, note, isLast }: TimelineStepProps) {
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <span
          className={`flex h-6 w-6 items-center justify-center rounded-full border-2 ${
            state === "done"
              ? "border-moss bg-moss text-white"
              : state === "current"
                ? "border-ochre bg-white text-ochre"
                : "border-night/20 bg-white text-night/30"
          }`}
          aria-hidden="true"
        >
          {state === "done" ? (
            <svg viewBox="0 0 16 16" fill="none" className="h-3 w-3">
              <path
                d="M3 8.5 6 11.5 13 4.5"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          ) : (
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
          )}
        </span>
        {!isLast && (
          <span
            className={`mt-1 w-0.5 flex-1 ${state === "done" ? "bg-moss" : "bg-night/15"}`}
            aria-hidden="true"
          />
        )}
      </div>
      <div className={`pb-6 ${isLast ? "pb-0" : ""}`}>
        <p className={`text-sm font-medium ${state === "upcoming" ? "text-night/40" : "text-night"}`}>
          {label}
        </p>
        {timestamp && (
          <p className="text-xs text-night/40">
            {new Date(timestamp).toLocaleString(undefined, {
              day: "numeric",
              month: "short",
              hour: "numeric",
              minute: "2-digit",
            })}
          </p>
        )}
        {note && (
          <p className="mt-1 rounded-lg bg-cream px-2.5 py-1.5 text-sm text-ink">{note}</p>
        )}
      </div>
    </div>
  );
}
