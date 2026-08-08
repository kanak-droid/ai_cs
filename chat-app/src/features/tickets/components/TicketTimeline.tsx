import { currentTimelineStepIndex, TIMELINE_STEPS, type Ticket } from "@astrohelp/shared";

import { TimelineStep } from "./TimelineStep";

function findStepTimestamp(history: Ticket["history"], statuses: string[]): string | undefined {
  const matches = history.filter((h) => statuses.includes(h.status));
  if (matches.length === 0) return undefined;
  return matches.reduce((earliest, h) => (h.changed_at < earliest ? h.changed_at : earliest), matches[0].changed_at);
}

export function TicketTimeline({ ticket }: { ticket: Ticket }) {
  const currentIndex = currentTimelineStepIndex(ticket.status);

  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm">
      {TIMELINE_STEPS.map((step, index) => (
        <TimelineStep
          key={step.key}
          label={step.label}
          state={index < currentIndex ? "done" : index === currentIndex ? "current" : "upcoming"}
          timestamp={findStepTimestamp(ticket.history, step.statuses)}
          isLast={index === TIMELINE_STEPS.length - 1}
        />
      ))}
    </div>
  );
}
