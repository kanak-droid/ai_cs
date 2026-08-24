import type { AdminTicket } from "@astrohelp/shared";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../../auth/AuthContext";
import { Modal } from "../../../components/Modal";
import { useAdminsLookup } from "../api/useAdminsLookup";
import { BulkReassignForm } from "./BulkReassignForm";
import { ReassignTicketForm } from "./ReassignTicketForm";
import { TicketStatusBadge } from "./TicketStatusBadge";

function PriorityBadge({ priority }: { priority: number | null }) {
  if (priority === null) return <span className="text-xs text-night/30">—</span>;
  const isVip = priority <= 2;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${
        isVip ? "bg-clay-100 text-clay-700" : "bg-slate-100 text-slate-600"
      }`}
    >
      P{priority}
    </span>
  );
}

function AssignedToCell({
  assignedAdminId,
  assignedCsId,
  canReassign,
  onReassignClick,
}: {
  assignedAdminId: number | null;
  assignedCsId: number | null;
  canReassign: boolean;
  onReassignClick: () => void;
}) {
  const { data: admins } = useAdminsLookup();
  const kam = admins?.find((a) => a.id === assignedAdminId);
  const cs = admins?.find((a) => a.id === assignedCsId);

  return (
    <div className="flex flex-col gap-0.5 text-xs">
      {kam ? (
        <span className="text-night">
          <span className="text-night/40">KAM </span>
          {kam.name}
        </span>
      ) : (
        !cs && <span className="text-night/30">—</span>
      )}
      {cs && (
        <span className="text-night">
          <span className="text-night/40">CS </span>
          {cs.name}
        </span>
      )}
      {canReassign && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onReassignClick();
          }}
          className="mt-0.5 text-left font-medium text-terracotta hover:underline"
        >
          Reassign
        </button>
      )}
    </div>
  );
}

export function TicketQueueTable({ tickets }: { tickets: AdminTicket[] }) {
  const navigate = useNavigate();
  const { admin } = useAuth();
  // Reassigning ownership is an ADMIN-access-level action (see the
  // matching backend gate on POST .../reassign) — a normal-access KAM/CS
  // shouldn't even see the option.
  const canReassign = admin?.accessLevel === "admin";
  // Tracks which ticket's reassign modal is open — a single piece of state
  // on the table rather than per-row, since only one modal can ever be
  // open at a time.
  const [reassigningTicketId, setReassigningTicketId] = useState<number | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkReassignOpen, setBulkReassignOpen] = useState(false);

  // Selection is scoped to whichever tickets are currently rendered in
  // THIS table instance — TicketQueuePage renders two of these (active vs
  // resolved/closed), and a filter change swapping the row set out from
  // under a stale selection would silently bulk-reassign the wrong tickets.
  useEffect(() => {
    setSelectedIds((prev) => {
      const visibleIds = new Set(tickets.map((t) => t.id));
      const next = new Set([...prev].filter((id) => visibleIds.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [tickets]);

  function toggleOne(ticketId: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(ticketId)) next.delete(ticketId);
      else next.add(ticketId);
      return next;
    });
  }

  function toggleAll() {
    setSelectedIds((prev) => (prev.size === tickets.length ? new Set() : new Set(tickets.map((t) => t.id))));
  }

  return (
    <div className="overflow-x-auto rounded-2xl bg-white shadow-sm">
      {canReassign && selectedIds.size > 0 && (
        <div className="flex items-center gap-3 border-b border-night/10 bg-cream/60 px-4 py-2.5">
          <p className="text-sm font-medium text-night">{selectedIds.size} selected</p>
          <button
            type="button"
            onClick={() => setBulkReassignOpen(true)}
            className="text-sm font-medium text-terracotta hover:underline"
          >
            Reassign selected
          </button>
          <button
            type="button"
            onClick={() => setSelectedIds(new Set())}
            className="text-sm font-medium text-night/40 hover:underline"
          >
            Clear selection
          </button>
        </div>
      )}
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-night/10 text-xs uppercase tracking-wide text-night/40">
            {canReassign && (
              <th className="px-4 py-3 font-medium">
                <input
                  type="checkbox"
                  aria-label="Select all tickets"
                  checked={selectedIds.size > 0 && selectedIds.size === tickets.length}
                  onChange={toggleAll}
                  className="h-4 w-4 rounded border-night/30"
                />
              </th>
            )}
            <th className="px-4 py-3 font-medium">Astrologer</th>
            <th className="px-4 py-3 font-medium">Issue</th>
            <th className="px-4 py-3 font-medium">Priority</th>
            <th className="px-4 py-3 font-medium">Assigned to</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Created</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket) => (
            <tr
              key={ticket.id}
              onClick={() => navigate(`/tickets/${ticket.id}`)}
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter") navigate(`/tickets/${ticket.id}`);
              }}
              className="cursor-pointer border-b border-night/5 last:border-0 hover:bg-cream/60"
            >
              {canReassign && (
                <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    aria-label={`Select ticket #${ticket.id}`}
                    checked={selectedIds.has(ticket.id)}
                    onChange={() => toggleOne(ticket.id)}
                    className="h-4 w-4 rounded border-night/30"
                  />
                </td>
              )}
              <td className="px-4 py-3">
                <p className="font-medium text-night">{ticket.astrologer.name}</p>
                <p className="text-xs text-night/40">
                  #{ticket.astrologer_id} · Expert ID {ticket.astrologer.expert_id ?? "not linked"}
                </p>
              </td>
              <td className="px-4 py-3">
                <p className="capitalize text-night">{ticket.category.replace(/_/g, " ")}</p>
                <p className="max-w-xs truncate text-xs text-night/50">{ticket.description_en}</p>
              </td>
              <td className="px-4 py-3">
                <PriorityBadge priority={ticket.astrologer.priority} />
              </td>
              <td className="px-4 py-3">
                <AssignedToCell
                  assignedAdminId={ticket.assigned_admin_id}
                  assignedCsId={ticket.assigned_cs_id}
                  canReassign={canReassign}
                  onReassignClick={() => setReassigningTicketId(ticket.id)}
                />
              </td>
              <td className="px-4 py-3">
                <div className="flex flex-col gap-1">
                  <TicketStatusBadge status={ticket.status} />
                  {ticket.escalated_to_kam && (
                    <span className="inline-flex w-fit items-center rounded-full bg-ochre/15 px-2.5 py-1 text-xs font-medium text-ochre-700">
                      Escalated to KAM
                    </span>
                  )}
                </div>
              </td>
              <td className="px-4 py-3 text-xs text-night/50">
                {new Date(ticket.created_at).toLocaleDateString(undefined, {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {reassigningTicketId !== null && (
        <Modal title={`Reassign ticket #${reassigningTicketId}`} onClose={() => setReassigningTicketId(null)}>
          <ReassignTicketForm
            ticketId={reassigningTicketId}
            onDone={() => setReassigningTicketId(null)}
            onCancel={() => setReassigningTicketId(null)}
          />
        </Modal>
      )}

      {bulkReassignOpen && (
        <Modal title="Reassign selected tickets" onClose={() => setBulkReassignOpen(false)}>
          <BulkReassignForm
            ticketIds={[...selectedIds]}
            onDone={() => {
              setBulkReassignOpen(false);
              setSelectedIds(new Set());
            }}
            onCancel={() => setBulkReassignOpen(false)}
          />
        </Modal>
      )}
    </div>
  );
}
