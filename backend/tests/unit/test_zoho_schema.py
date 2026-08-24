from app.schemas.zoho import ZohoWebhookRequest


def test_ticket_id_accepts_a_raw_json_number():
    # Zoho's "Ticket Id" field is a Deluge number — a workflow's custom
    # function serializing it via a Map's toString() sends it as an
    # unquoted JSON number, not a string (confirmed live 2026-08-22).
    body = ZohoWebhookRequest.model_validate({"ticket_id": 271863000003664934, "status": "Closed"})
    assert body.ticket_id == "271863000003664934"


def test_ticket_id_still_accepts_a_plain_string():
    body = ZohoWebhookRequest.model_validate({"ticket_id": "271863000003664934", "status": "Closed"})
    assert body.ticket_id == "271863000003664934"
