import { Link, useParams } from "react-router-dom";

import { EmptyState } from "../../../components/EmptyState";
import { Spinner } from "../../../components/Spinner";
import { useTicketDetail } from "../api/useTicketDetail";
import { AttachmentPreview } from "../components/AttachmentPreview";
import { ContactInfoCard } from "../components/ContactInfoCard";
import { DescriptionPanel } from "../components/DescriptionPanel";
import { StatusUpdateControl } from "../components/StatusUpdateControl";
import { TicketHistoryList } from "../components/TicketHistoryList";
import { TicketStatusBadge } from "../components/TicketStatusBadge";

export function TicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const ticketId = Number(id);
  const { data: ticket, status } = useTicketDetail(ticketId);

  if (status === "pending") return <Spinner label="Loading ticket…" />;
  if (status === "error" || !ticket) return <EmptyState title="Couldn't load this ticket" />;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <Link to="/tickets" className="text-sm text-night/50 hover:text-night">
          ← Back to Tickets
        </Link>
        <div className="mt-2 flex items-center gap-3">
          <h1 className="text-2xl font-semibold text-night">Ticket #{ticket.id}</h1>
          <TicketStatusBadge status={ticket.status} />
        </div>
        <p className="text-sm capitalize text-night/50">
          {ticket.category.replace(/_/g, " ")} · {ticket.sub_category.replace(/_/g, " ")}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="flex flex-col gap-4 lg:col-span-2">
          <DescriptionPanel
            description={ticket.description}
            descriptionEn={ticket.description_en}
            language={ticket.preferred_language}
          />
          <AttachmentPreview url={ticket.attachment_url} />
          <TicketHistoryList history={ticket.history} />
        </div>
        <div className="flex flex-col gap-4">
          <ContactInfoCard astrologer={ticket.astrologer} />
          <StatusUpdateControl ticketId={ticket.id} currentStatus={ticket.status} />
        </div>
      </div>
    </div>
  );
}
