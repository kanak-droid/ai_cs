import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, chat, tickets
from app.api.routes.admin import admins as admin_admins
from app.api.routes.admin import astrologers as admin_astrologers
from app.api.routes.admin import login as admin_login
from app.api.routes.admin import slack_log as admin_slack_log
from app.api.routes.admin import tickets as admin_tickets
from app.core.config import settings
from app.core.errors import AppError

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


app.include_router(chat.router)
app.include_router(tickets.router)
app.include_router(auth.router)
app.include_router(admin_login.router)
app.include_router(admin_tickets.router)
app.include_router(admin_astrologers.router)
app.include_router(admin_slack_log.router)
app.include_router(admin_admins.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
