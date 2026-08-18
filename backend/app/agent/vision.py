"""One-shot Gemini multimodal call to interpret an astrologer's screenshot.

Separate from the tool-calling `contents` loop in orchestrator.py — this is a
single image-in/text-out request the executor makes on the model's behalf,
not a turn in the ongoing conversation.
"""

import httpx
from google.genai import types

from app.agent import vertex_client
from app.core.config import settings

# The orchestrator model writes `question` itself, and how leading it is
# varies by conversation — verified live that a leading question ("Does this
# payout screen show a different amount than expected?") makes Gemini
# fabricate a fully fictional screenshot (invented amount, status, date) for
# a plain black image, while a neutral question on the same image correctly
# reports it's blank. This grounding is appended to every call regardless of
# how the question is phrased, rather than trusting the question to be safe.
_GROUNDING_SUFFIX = (
    "\n\nOnly describe what is actually visible in the image. If it's blank, "
    "solid-color, unreadable, cropped, or otherwise doesn't show what the "
    "question assumes, say that plainly — never guess or invent a specific "
    "number, date, name, status, or other text that isn't clearly legible."
)


def analyze_image(image_url: str, question: str) -> str:
    image_response = httpx.get(image_url, timeout=10.0)
    image_response.raise_for_status()
    mime_type = image_response.headers.get("content-type", "image/jpeg").split(";")[0]

    client = vertex_client.build_vertex_client()
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=image_response.content, mime_type=mime_type),
            question + _GROUNDING_SUFFIX,
        ],
        config=types.GenerateContentConfig(labels=vertex_client.billing_labels()),
    )
    return response.text or "Couldn't make out anything specific in that screenshot."
