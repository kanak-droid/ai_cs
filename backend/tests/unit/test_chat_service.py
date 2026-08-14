from app.schemas.chat import ChatHistoryTurn
from app.services.chat_service import _find_last_attachment_url


def test_finds_attachment_url_in_current_message():
    url = _find_last_attachment_url(
        "Here's my photo.\n\n[Uploaded attachment URL: http://x/a.png]", history=[]
    )
    assert url == "http://x/a.png"


def test_falls_back_to_most_recent_attachment_in_history():
    history = [
        ChatHistoryTurn(role="astrologer", text="[Uploaded attachment URL: http://x/old.png]"),
        ChatHistoryTurn(role="assistant", text="Got it, thanks!"),
        ChatHistoryTurn(role="astrologer", text="[Uploaded attachment URL: http://x/new.png]"),
        ChatHistoryTurn(role="assistant", text="Looking into it."),
    ]
    url = _find_last_attachment_url("I'm still not satisfied", history=history)
    assert url == "http://x/new.png"


def test_returns_none_when_nothing_was_ever_shared():
    history = [ChatHistoryTurn(role="astrologer", text="What's my payout status?")]
    assert _find_last_attachment_url("connect me to a person", history=history) is None
