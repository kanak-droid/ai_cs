package com.astrolokal.astrohelp.data

import kotlinx.serialization.Serializable

// These mirror the astrologer-facing Pydantic schemas in the FastAPI backend
// (backend/app/schemas/{auth,chat,ticket}.py). Field names are snake_case to
// match the JSON on the wire — the Json instance in ApiClient does NOT remap
// names, so keep these identical to the backend.

@Serializable
data class VerifyResponse(
    val astrologer_id: Int,
    val name: String,
    val language: String,
)

@Serializable
data class ChatHistoryTurn(
    val role: String, // "astrologer" | "assistant"
    val text: String,
)

@Serializable
data class ChatRequest(
    val message: String,
    val history: List<ChatHistoryTurn> = emptyList(),
    val session_id: String? = null,
)

@Serializable
data class ChatTraceStep(
    val tool: String,
    val ok: Boolean,
    val summary: String,
)

@Serializable
data class ChatResponse(
    val reply: String,
    val trace: List<ChatTraceStep> = emptyList(),
    val created_ticket_id: Int? = null,
    val show_feedback: Boolean = false,
)

@Serializable
data class TicketStatusHistoryRead(
    val status: String,
    val changed_at: String,
    val changed_by: String,
    val note: String? = null,
    val is_status_change: Boolean = true,
)

@Serializable
data class Ticket(
    val id: Int,
    val astrologer_id: Int,
    val category: String,
    val sub_category: String,
    val description: String,
    val description_en: String,
    val preferred_language: String,
    val attachment_url: String? = null,
    val assigned_admin_id: Int? = null,
    val assigned_cs_id: Int? = null,
    val kam_notified: Boolean = false,
    val cs_notified: Boolean = false,
    val status: String,
    val resolved_at: String? = null,
    val satisfaction: String? = null,
    val rating: Int? = null,
    val rating_reasons: List<String>? = null,
    val rating_comment: String? = null,
    val rated_at: String? = null,
    val escalated_to_kam: Boolean = false,
    val escalated_at: String? = null,
    val created_at: String,
    val updated_at: String,
    val history: List<TicketStatusHistoryRead> = emptyList(),
)

@Serializable
data class TicketRatingRequest(
    val rating: Int,
    val reasons: List<String> = emptyList(),
    val comment: String? = null,
)

@Serializable
data class SessionFeedbackRequest(
    val rating: Int,
    val reasons: List<String> = emptyList(),
    val comment: String? = null,
)

// Voice call — mirrors backend/app/schemas/voice.py on the ai-voice-call
// branch. The AI places an outbound (PSTN) call via Vapi to the astrologer's
// registered phone; session_id links the call to this visit's chat context.
@Serializable
data class RequestCallBody(
    val session_id: String? = null,
)

@Serializable
data class RequestCallResponse(
    val call_id: Int,
    val status: String,
)

/** A single rendered chat bubble in the UI. */
data class ChatMessage(
    val role: String, // "astrologer" | "assistant"
    val text: String,
    val trace: List<ChatTraceStep> = emptyList(),
    val timestampMillis: Long = System.currentTimeMillis(),
)
