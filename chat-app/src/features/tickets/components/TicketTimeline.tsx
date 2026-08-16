import { currentTimelineStepIndex, TIMELINE_STEPS, type Ticket } from "@astrohelp/shared";

import { TimelineStep } from "./TimelineStep";

function findStepTimestamp(history: Ticket["history"], statuses: string[]): string | undefined {
  const matches = history.filter((h) => statuses.includes(h.status));
  if (matches.length === 0) return undefined;
  return matches.reduce((earliest, h) => (h.changed_at < earliest ? h.changed_at : earliest), matches[0].changed_at);
}

// Only a real admin actually typed this — "system" (auto-assign on ticket
// creation) and "astrologer" (their own satisfaction response) both carry
// internal or self-authored notes, never meant to be shown back as if an
// admin wrote them (system notes can even name an internal admin id, e.g.
// "Auto-assigned to admin #24"). Picks the most recent one, since a step
// like "In Progress" can cover more than one status (under_review AND
// in_progress) with more than one note across them.
function findStepNote(history: Ticket["history"], statuses: string[]): string | undefined {
  const matches = history.filter(
    (h) => statuses.includes(h.status) && h.note && h.changed_by !== "system" && h.changed_by !== "astrologer",
  );
  if (matches.length === 0) return undefined;
  return matches.reduce((latest, h) => (h.changed_at > latest.changed_at ? h : latest), matches[0]).note ?? undefined;
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
          note={findStepNote(ticket.history, step.statuses)}
          isLast={index === TIMELINE_STEPS.length - 1}
        />
      ))}
    </div>
  );
}
