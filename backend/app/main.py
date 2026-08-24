import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, chat, feedback, tickets, uploads, zoho_webhook
from app.api.routes.admin import admins as admin_admins
from app.api.routes.admin import analytics as admin_analytics
from app.api.routes.admin import astrologers as admin_astrologers
from app.api.routes.admin import chat_logs as admin_chat_logs
from app.api.routes.admin import email_log as admin_email_log
from app.api.routes.admin import login as admin_login
from app.api.routes.admin import sheets_sync as admin_sheets_sync
from app.api.routes.admin import slack_log as admin_slack_log
from app.api.routes.admin import tickets as admin_tickets
from app.core.config import settings
from app.core.errors import AppError
from app.core.uploads import UPLOAD_DIR

STATIC_DIR = Path(__file__).resolve().parent / "static"
# The built chat-app SPA, copied in by backend/Dockerfile's frontend-builder
# stage — absent in local dev (chat-app runs via its own `npm run dev`
# instead), which is why every route below is registered behind an
# existence check rather than assuming it's always there.
CHAT_DIST_DIR = Path(__file__).resolve().parent / "chat_static"

logger = logging.getLogger(__name__)

app = FastAPI(title="AstroHelp API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(Exception)
def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Without this, an unhandled exception propagates past CORSMiddleware
    # entirely (Starlette's ServerErrorMiddleware sits outside it), so the
    # browser reports a confusing "CORS blocked" error instead of the real
    # failure. Catching it here keeps the response inside the CORS-wrapped
    # layer and gives the frontend a real (if generic) error body to show.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})


app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(chat.router)
app.include_router(tickets.router)
app.include_router(auth.router)
app.include_router(uploads.router)
app.include_router(feedback.router)
app.include_router(admin_login.router)
app.include_router(admin_tickets.router)
app.include_router(admin_astrologers.router)
app.include_router(admin_slack_log.router)
app.include_router(admin_admins.router)
app.include_router(admin_analytics.router)
app.include_router(admin_chat_logs.router)
app.include_router(admin_email_log.router)
app.include_router(admin_sheets_sync.router)
app.include_router(zoho_webhook.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _is_reserved_path(full_path: str) -> bool:
    return full_path == "health" or full_path.startswith(("api/", "uploads/", "static/"))


if CHAT_DIST_DIR.exists():
    app.mount(
        "/assets", StaticFiles(directory=str(CHAT_DIST_DIR / "assets")), name="chat-assets"
    )

    # Registered last, so every route/mount above gets first chance to match.
    # Anything left over is either a real chat-app asset (favicon, etc.) or a
    # client-side route (e.g. /tickets/5) that only React Router understands
    # — index.html is served either way, mirroring nginx's old
    # `try_files $uri $uri/ /index.html` for the same SPA.
    @app.get("/{full_path:path}")
    def serve_chat_app(full_path: str) -> FileResponse:
        if _is_reserved_path(full_path):
            raise HTTPException(status_code=404)
        candidate = CHAT_DIST_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        # index.html references each build's content-hashed JS/CSS
        # filenames — without this, a browser can serve a stale cached copy
        # on a normal refresh, keeping a WebView on old asset references
        # (some possibly deleted by the next deploy) until a hard refresh
        # forces a real re-fetch (observed live 2026-08-18, admin-app's
        # equivalent). "no-cache" still allows caching, just forces
        # revalidation with the server every time.
        return FileResponse(CHAT_DIST_DIR / "index.html", headers={"Cache-Control": "no-cache"})
