package com.astrolokal.astrohelp.data

import com.astrolokal.astrohelp.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import java.io.BufferedReader
import java.net.HttpURLConnection
import java.net.URL

/**
 * Thin client over the AstroHelp FastAPI backend's astrologer-facing routes.
 *
 * Auth: the astrologer side has no signed token — the main AstroLokal app
 * hands off a plain `user_id`, which the backend resolves against
 * Astrologer.user_id (see backend/app/services/auth_service.py). So every
 * request just sends `Authorization: Bearer <user_id>`.
 */
class ApiClient(
    private val userId: String,
    private val baseUrl: String = BuildConfig.API_BASE_URL,
) {
    class ApiException(val code: Int, message: String) : Exception(message)

    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    suspend fun verify(): VerifyResponse =
        decode(request("GET", "/api/auth/verify", null))

    suspend fun listTickets(): List<Ticket> =
        decode(request("GET", "/api/tickets", null))

    suspend fun getTicket(id: Int): Ticket =
        decode(request("GET", "/api/tickets/$id", null))

    suspend fun sendChat(body: ChatRequest): ChatResponse =
        decode(request("POST", "/api/chat", json.encodeToString(ChatRequest.serializer(), body)))

    suspend fun rateTicket(id: Int, body: TicketRatingRequest): Ticket =
        decode(
            request(
                "POST",
                "/api/tickets/$id/rating",
                json.encodeToString(TicketRatingRequest.serializer(), body),
            )
        )

    suspend fun requestCall(sessionId: String?): RequestCallResponse =
        decode(
            request(
                "POST",
                "/api/voice/request-call",
                json.encodeToString(RequestCallBody.serializer(), RequestCallBody(sessionId)),
            )
        )

    suspend fun submitSessionFeedback(sessionId: String, body: SessionFeedbackRequest) {
        request(
            "POST",
            "/api/chat/sessions/$sessionId/feedback",
            json.encodeToString(SessionFeedbackRequest.serializer(), body),
        )
    }

    // --- HTTP plumbing -----------------------------------------------------

    private inline fun <reified T> decode(text: String): T =
        json.decodeFromString(text)

    private suspend fun request(method: String, path: String, body: String?): String =
        withContext(Dispatchers.IO) {
            val conn = (URL(baseUrl + path).openConnection() as HttpURLConnection).apply {
                requestMethod = method
                connectTimeout = 15_000
                readTimeout = 30_000
                setRequestProperty("Authorization", "Bearer $userId")
                setRequestProperty("Accept", "application/json")
                if (body != null) {
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json")
                }
            }
            try {
                if (body != null) {
                    conn.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
                }
                val code = conn.responseCode
                val stream = if (code in 200..299) conn.inputStream else conn.errorStream
                val text = stream?.bufferedReader()?.use(BufferedReader::readText).orEmpty()
                if (code !in 200..299) {
                    throw ApiException(code, extractDetail(text) ?: "HTTP $code")
                }
                text
            } finally {
                conn.disconnect()
            }
        }

    /** Pull FastAPI's `{"detail": "..."}` message out of an error body, if present. */
    private fun extractDetail(body: String): String? =
        runCatching {
            (json.parseToJsonElement(body) as? JsonObject)
                ?.get("detail")
                ?.let { (it as? JsonPrimitive)?.contentOrNull }
        }.getOrNull()
}
