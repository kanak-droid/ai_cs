from pydantic import BaseModel, field_validator


class ZohoWebhookRequest(BaseModel):
    # This is OUR OWN contract, not Zoho's raw webhook payload — configured
    # as the JSON body template on the Zoho Desk workflow rule's webhook
    # action (see app/api/routes/zoho_webhook.py), so we control it exactly
    # rather than depending on Zoho's undocumented default shape.
    ticket_id: str
    status: str
    note: str | None = None

    @field_validator("ticket_id", mode="before")
    @classmethod
    def _coerce_ticket_id_to_str(cls, value: object) -> object:
        # Zoho's "Ticket Id" field is a Deluge number, not a string — a
        # workflow's custom function serializing it into the webhook body
        # (via a Map's toString()) sends it as a raw JSON number, not a
        # quoted string. Accept either rather than depending on the Deluge
        # script always remembering to stringify it first.
        if isinstance(value, int):
            return str(value)
        return value
