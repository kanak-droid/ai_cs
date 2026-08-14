"""Pure-data tool definitions. agent/orchestrator.py translates each of these
into a Gemini `types.FunctionDeclaration` (name/description/input_schema map
onto name/description/parameters_json_schema) — this file itself stays
provider-neutral.

Deliberately no `astrologer_id` property on any of these — the model is told
the astrologer's identity narratively in the system prompt for reasoning, but
has no schema slot to place an id in. The real enforcement lives in
agent/executor.py, which never trusts a tool call's input for identity
anyway; this is defense in depth, not the enforcement itself.
"""

GET_PAYOUT_STATUS = {
    "name": "get_payout_status",
    "description": "Get the current astrologer's payout status, amount, and scheduled date.",
    "input_schema": {"type": "object", "properties": {}},
}

GET_KYC_STATUS = {
    "name": "get_kyc_status",
    "description": "Get the current astrologer's KYC verification status and, if rejected, why.",
    "input_schema": {"type": "object", "properties": {}},
}

GET_PRIORITY_RANKING = {
    "name": "get_priority_ranking",
    "description": (
        "Get the current astrologer's queue priority ranking and recent call/talktime "
        "stats — use this for questions like 'why is my priority low' or 'how many calls "
        "have I been getting'."
    ),
    "input_schema": {"type": "object", "properties": {}},
}

GET_SALARY_DETAILS = {
    "name": "get_salary_details",
    "description": "Get the current astrologer's monthly salary and revision dates.",
    "input_schema": {"type": "object", "properties": {}},
}

GET_ASSIGNED_ADMIN = {
    "name": "get_assigned_admin",
    "description": "Get the KAM/admin currently assigned to the astrologer.",
    "input_schema": {"type": "object", "properties": {}},
}

TRIGGER_PHOTO_BEAUTIFY = {
    "name": "trigger_photo_beautify",
    "description": (
        "Send an uploaded profile photo through the beautify/retouch pipeline. "
        "Call this only after the astrologer has uploaded a photo and its URL is known. "
        "This never updates the astrologer's live profile photo by itself — always "
        "follow it with create_support_ticket so an admin can review and approve it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "image_url": {
                "type": "string",
                "description": "URL of the astrologer's freshly uploaded photo.",
            }
        },
        "required": ["image_url"],
    },
}

ANALYZE_SCREENSHOT = {
    "name": "analyze_screenshot",
    "description": (
        "Look at a screenshot or photo the astrologer shared, to help diagnose a technical "
        "problem (an error message, a stuck/broken screen) or a business one (a payout/KYC "
        "screen that seems to contradict get_payout_status/get_kyc_status). Call this only "
        "after the astrologer has actually shared an image and you know its URL — use it as "
        "a debugging step before deciding whether to raise a ticket, not instead of one."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "image_url": {
                "type": "string",
                "description": "URL of the screenshot/photo to analyze.",
            },
            "question": {
                "type": "string",
                "description": (
                    "What to look for, e.g. 'What error message is shown on this screen?' "
                    "or 'Does this payout screen show a different amount than expected?'"
                ),
            },
        },
        "required": ["image_url", "question"],
    },
}

CREATE_SUPPORT_TICKET = {
    "name": "create_support_ticket",
    "description": (
        "Create a support ticket for an issue you cannot resolve directly, or when the "
        "astrologer says they are not satisfied with your answer. Always provide a clear "
        "category/sub_category and a real summary of the underlying issue (not just the "
        "astrologer's most recent message) so admins who may not read the astrologer's "
        "language can triage it. For category 'technical', 'other', 'payout', or 'kyc', "
        "EVERY astrologer's ticket (any priority) needs a photo/video attached first — this "
        "call will error and tell you to get one if it's missing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": (
                    "Broad issue category: 'payout', 'kyc', 'profile' (photo change), "
                    "'technical', 'phone_change' (astrologer wants their registered phone "
                    "number changed), 'no_visibility' (astrologer says they aren't showing "
                    "up / getting bookings/visibility they expect), or 'other'."
                ),
            },
            "sub_category": {
                "type": "string",
                "description": "More specific sub-category, e.g. 'payout_delay', 'photo_change'.",
            },
            "description": {
                "type": "string",
                "description": (
                    "A summary, in the astrologer's own language, of the actual underlying "
                    "issue across the WHOLE conversation so far — what they originally asked, "
                    "what you found or told them, and why they remain unsatisfied or need a "
                    "human. Never just the astrologer's single most recent message on its own "
                    "(e.g. 'connect me to a person' or 'I'm not satisfied' tells an admin "
                    "nothing) — always name the actual topic."
                ),
            },
            "description_en": {
                "type": "string",
                "description": (
                    "The same summary as `description`, written in clear English for admins "
                    "who may not read the astrologer's language."
                ),
            },
            "attachment_url": {
                "type": "string",
                "description": (
                    "URL of a relevant photo/video, if any (e.g. a profile photo for a "
                    "photo-change request, or a screenshot of the issue). You can leave "
                    "this out if the astrologer already shared one earlier in this "
                    "conversation — it's attached automatically, no need to look up or "
                    "repeat the exact URL."
                ),
            },
        },
        "required": ["category", "sub_category", "description", "description_en"],
    },
}

GET_TICKETS = {
    "name": "get_tickets",
    "description": "List the current astrologer's support tickets and their statuses.",
    "input_schema": {"type": "object", "properties": {}},
}

MARK_ISSUE_RESOLVED = {
    "name": "mark_issue_resolved",
    "description": (
        "Call this ONLY after you asked the astrologer something like 'did that solve it?' "
        "and they clearly confirmed yes — for a genuine problem you helped troubleshoot, not "
        "a simple factual lookup (e.g. don't call this just because you answered a payout "
        "status question). This shows them a quick feedback prompt and never raises a ticket."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Broad issue category, e.g. 'payout', 'kyc', 'profile', 'technical', 'other'.",
            },
            "sub_category": {
                "type": "string",
                "description": "More specific sub-category, e.g. 'app_crash', 'photo_change'.",
            },
        },
        "required": ["category", "sub_category"],
    },
}

ALL_TOOLS = [
    GET_PAYOUT_STATUS,
    GET_KYC_STATUS,
    GET_PRIORITY_RANKING,
    GET_SALARY_DETAILS,
    GET_ASSIGNED_ADMIN,
    # TRIGGER_PHOTO_BEAUTIFY intentionally left out of the model's toolset —
    # the n8n beautify workflow is on hold (2026-08-14); Photo Change tickets
    # currently carry the astrologer's original, unedited photo instead. See
    # app/agent/prompt.py's "Profile photo changes" section and
    # docs/chatbot-approach.md §8d.
    ANALYZE_SCREENSHOT,
    CREATE_SUPPORT_TICKET,
    GET_TICKETS,
    MARK_ISSUE_RESOLVED,
]
