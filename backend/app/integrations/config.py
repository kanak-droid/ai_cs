from app.core.config import settings

# Every mocked client below checks this flag before doing anything network-shaped.
# Flip to False (and fill in the corresponding real URL/credential env vars) to
# switch a client over to a real backend with no other code changes required.
MOCK_MODE = settings.MOCK_MODE
