"""Pure-data tool definitions passed to the Anthropic `tools=[...]` parameter.

Deliberately no `astrologer_id` property on any of these — Claude is told the
astrologer's identity narratively in the system prompt for reasoning, but has
no schema slot to place an id in. The real enforcement lives in
agent/executor.py, which never trusts a tool_use input for identity anyway;
this is defense in depth, not the enforcement itself.
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

CREATE_SUPPORT_TICKET = {
    "name": "create_support_ticket",
    "description": (
        "Create a support ticket for an issue you cannot resolve directly, or when the "
        "astrologer says they are not satisfied with your answer. Always provide a clear "
        "category/sub_category and an English summary so admins who may not read the "
        "astrologer's language can triage it."
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
                "description": "More specific sub-category, e.g. 'payout_delay', 'photo_change'.",
            },
            "description": {
                "type": "string",
                "description": "The issue described in the astrologer's own words/language.",
            },
            "description_en": {
                "type": "string",
                "description": "A clear English summary of the issue, for admins.",
            },
            "attachment_url": {
                "type": "string",
                "description": "URL of a relevant photo/attachment, if any (e.g. a beautified photo).",
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

ALL_TOOLS = [
    GET_PAYOUT_STATUS,
    GET_KYC_STATUS,
    GET_SALARY_DETAILS,
    GET_ASSIGNED_ADMIN,
    TRIGGER_PHOTO_BEAUTIFY,
    CREATE_SUPPORT_TICKET,
    GET_TICKETS,
]
