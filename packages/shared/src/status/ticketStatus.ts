import type { TicketStatus } from "../types/ticket";

// Single source of truth for how a status is labeled and colored across both
// apps — a new status only ever needs to be added here.
export const STATUS_LABELS: Record<TicketStatus, string> = {
  submitted: "Submitted",
  assigned_to_kam: "Assigned",
  under_review: "Under Review",
  in_progress: "In Progress",
  resolved: "Resolved",
  closed: "Closed",
};

// Tailwind color tokens defined in tailwind-preset.js — never a raw hex here.
export const STATUS_COLOR_TOKEN: Record<TicketStatus, string> = {
  submitted: "terracotta",
  assigned_to_kam: "terracotta",
  under_review: "ochre",
  in_progress: "ochre",
  resolved: "moss",
  closed: "slate",
};

// Statuses an admin may set manually from the dashboard. submitted and
// assigned_to_kam only ever happen automatically on ticket creation.
// "closed" is deliberately excluded (2026-08-20): the only manual terminal
// state is "resolved" — closing now always comes from the astrologer
// confirming it's fixed, or the 48h auto-close if they never respond.
export const ADMIN_SETTABLE_STATUSES: TicketStatus[] = ["under_review", "in_progress", "resolved"];

export interface TimelineStep {
  key: string;
  label: string;
  statuses: TicketStatus[];
}

// The astrologer-facing tracker only ever shows 4 steps — under_review and
// in_progress collapse into one "In Progress" node, and closed reads as a
// continuation of "Resolved" rather than a 5th step.
export const TIMELINE_STEPS: TimelineStep[] = [
  { key: "submitted", label: "Submitted", statuses: ["submitted"] },
  { key: "assigned", label: "Assigned", statuses: ["assigned_to_kam"] },
  { key: "in_progress", label: "In Progress", statuses: ["under_review", "in_progress"] },
  { key: "resolved", label: "Resolved", statuses: ["resolved", "closed"] },
];

export function currentTimelineStepIndex(status: TicketStatus): number {
  return TIMELINE_STEPS.findIndex((step) => step.statuses.includes(status));
}
