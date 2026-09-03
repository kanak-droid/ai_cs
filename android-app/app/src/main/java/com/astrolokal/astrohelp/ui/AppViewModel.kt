package com.astrolokal.astrohelp.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.astrolokal.astrohelp.data.ApiClient
import com.astrolokal.astrohelp.data.ChatHistoryTurn
import com.astrolokal.astrohelp.data.ChatMessage
import com.astrolokal.astrohelp.data.ChatRequest
import com.astrolokal.astrohelp.data.SessionStore
import com.astrolokal.astrohelp.data.Ticket
import com.astrolokal.astrohelp.data.TicketRatingRequest
import com.astrolokal.astrohelp.data.VerifyResponse
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.UUID

data class AppState(
    val checkingSession: Boolean = true,
    val astrologer: VerifyResponse? = null,
    val loginError: String? = null,
    val loggingIn: Boolean = false,

    // Chat
    val messages: List<ChatMessage> = emptyList(),
    val sending: Boolean = false,
    val chatError: String? = null,

    // Tickets
    val tickets: List<Ticket> = emptyList(),
    val ticketsLoading: Boolean = false,
    val ticketsError: String? = null,
    val selectedTicket: Ticket? = null,

    // Voice call
    val requestingCall: Boolean = false,
    val callStatus: String? = null,
    val callError: String? = null,
) {
    val isAuthenticated: Boolean get() = astrologer != null
}

class AppViewModel(app: Application) : AndroidViewModel(app) {
    private val sessionStore = SessionStore(app)
    private var api: ApiClient? = null

    // One session id per app process — analytics-only, matches the chat-app's
    // "one per webview visit" convention (backend/app/schemas/chat.py).
    private val sessionId: String = UUID.randomUUID().toString()

    private val _state = MutableStateFlow(AppState())
    val state: StateFlow<AppState> = _state.asStateFlow()

    private var started = false

    /**
     * Entry point, called once from [MainActivity].
     *
     * @param handoffUserId when the host AstroLokal app launches this screen
     *   it passes the already-known astrologer user_id here — we authenticate
     *   with it directly and never show the login screen. When null (standalone
     *   / dev launch) we fall back to a previously saved session, else the
     *   login screen.
     * @param baseUrlOverride optional backend URL from the host app; falls back
     *   to BuildConfig.API_BASE_URL when null/blank.
     */
    fun begin(handoffUserId: String?, baseUrlOverride: String?) {
        if (started) return
        started = true
        when {
            !handoffUserId.isNullOrBlank() ->
                authenticate(handoffUserId.trim(), baseUrlOverride, fromLogin = false)
            sessionStore.userId != null ->
                authenticate(sessionStore.userId!!, null, fromLogin = false)
            else ->
                _state.update { it.copy(checkingSession = false) }
        }
    }

    /** Manual login from the standalone/dev login screen. */
    fun login(userId: String) {
        val trimmed = userId.trim()
        if (trimmed.isEmpty()) {
            _state.update { it.copy(loginError = "Enter your user ID") }
            return
        }
        authenticate(trimmed, null, fromLogin = true)
    }

    private fun authenticate(userId: String, baseUrlOverride: String?, fromLogin: Boolean) {
        val client = if (baseUrlOverride.isNullOrBlank()) {
            ApiClient(userId)
        } else {
            ApiClient(userId, baseUrlOverride)
        }
        _state.update {
            if (fromLogin) it.copy(loggingIn = true, loginError = null)
            else it.copy(checkingSession = true, loginError = null)
        }
        viewModelScope.launch {
            runCatching { client.verify() }
                .onSuccess { me ->
                    api = client
                    sessionStore.userId = userId
                    _state.update {
                        it.copy(loggingIn = false, checkingSession = false, astrologer = me)
                    }
                    if (_state.value.messages.isEmpty()) greet(me)
                    loadTickets()
                }
                .onFailure { e ->
                    if (fromLogin) {
                        _state.update {
                            it.copy(loggingIn = false, loginError = e.message ?: "Login failed")
                        }
                    } else {
                        // A stale saved id, or a bad handoff — drop it and show login.
                        sessionStore.clear()
                        _state.update {
                            it.copy(checkingSession = false, loginError = e.message)
                        }
                    }
                }
        }
    }

    fun logout() {
        sessionStore.clear()
        api = null
        _state.value = AppState(checkingSession = false)
    }

    private fun greet(me: VerifyResponse) {
        _state.update {
            it.copy(
                messages = listOf(
                    ChatMessage(
                        role = "assistant",
                        text = "Namaste ${me.name}! I'm your AstroHelp assistant. " +
                            "Ask me about payouts, KYC, salary, or raise a ticket for anything else.",
                    )
                )
            )
        }
    }

    // --- Chat --------------------------------------------------------------

    fun sendMessage(text: String) {
        val client = api ?: return
        val message = text.trim()
        if (message.isEmpty() || _state.value.sending) return

        val history = _state.value.messages.map {
            ChatHistoryTurn(role = it.role, text = it.text)
        }
        _state.update {
            it.copy(
                messages = it.messages + ChatMessage(role = "astrologer", text = message),
                sending = true,
                chatError = null,
            )
        }

        viewModelScope.launch {
            runCatching {
                client.sendChat(
                    ChatRequest(message = message, history = history, session_id = sessionId)
                )
            }.onSuccess { resp ->
                _state.update {
                    it.copy(
                        messages = it.messages + ChatMessage(
                            role = "assistant",
                            text = resp.reply,
                            trace = resp.trace,
                        ),
                        sending = false,
                    )
                }
                // A ticket may have just been created by the bot — refresh the list.
                if (resp.created_ticket_id != null) loadTickets()
            }.onFailure { e ->
                _state.update {
                    it.copy(sending = false, chatError = e.message ?: "Couldn't send message")
                }
            }
        }
    }

    fun clearChatError() = _state.update { it.copy(chatError = null) }

    // --- Voice call --------------------------------------------------------

    /**
     * Ask the backend to place an outbound AI call. The call rings the
     * astrologer's registered phone over PSTN (via Vapi) — nothing happens
     * inside the app itself; we only surface the queued/failed status.
     * session_id is passed so the call can pick up this visit's chat context.
     */
    fun requestCall() {
        val client = api ?: return
        if (_state.value.requestingCall) return
        _state.update { it.copy(requestingCall = true, callError = null, callStatus = null) }
        viewModelScope.launch {
            runCatching { client.requestCall(sessionId) }
                .onSuccess { resp ->
                    _state.update { it.copy(requestingCall = false, callStatus = resp.status) }
                }
                .onFailure { e ->
                    _state.update {
                        it.copy(
                            requestingCall = false,
                            callError = e.message ?: "Couldn't start the call",
                        )
                    }
                }
        }
    }

    fun clearCallState() = _state.update { it.copy(callStatus = null, callError = null) }

    // --- Tickets -----------------------------------------------------------

    fun loadTickets() {
        val client = api ?: return
        _state.update { it.copy(ticketsLoading = true, ticketsError = null) }
        viewModelScope.launch {
            runCatching { client.listTickets() }
                .onSuccess { list ->
                    _state.update { it.copy(ticketsLoading = false, tickets = list) }
                }
                .onFailure { e ->
                    _state.update {
                        it.copy(
                            ticketsLoading = false,
                            ticketsError = e.message ?: "Couldn't load tickets",
                        )
                    }
                }
        }
    }

    fun openTicket(ticket: Ticket) {
        _state.update { it.copy(selectedTicket = ticket) }
        // Fetch the full record (with status history) in the background.
        val client = api ?: return
        viewModelScope.launch {
            runCatching { client.getTicket(ticket.id) }
                .onSuccess { full ->
                    _state.update {
                        if (it.selectedTicket?.id == full.id) it.copy(selectedTicket = full) else it
                    }
                }
        }
    }

    fun closeTicket() = _state.update { it.copy(selectedTicket = null) }

    fun rateTicket(ticketId: Int, rating: Int, comment: String?) {
        val client = api ?: return
        viewModelScope.launch {
            runCatching {
                client.rateTicket(
                    ticketId,
                    TicketRatingRequest(rating = rating, comment = comment?.ifBlank { null }),
                )
            }.onSuccess { updated ->
                _state.update { s ->
                    s.copy(
                        selectedTicket = if (s.selectedTicket?.id == updated.id) updated else s.selectedTicket,
                        tickets = s.tickets.map { if (it.id == updated.id) updated else it },
                    )
                }
            }
        }
    }
}
