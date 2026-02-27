import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.core.auth.routes import router as auth_router
from app.modules.packs.routes import router as packs_router
from app.modules.brand_os.routes import router as brand_os_router
from app.modules.campaign.routes import router as campaign_router
from app.modules.conversion_page.routes import router as conversion_page_router
from app.modules.sprint.routes import router as sprint_router
from app.modules.clients.routes import router as clients_router
from app.modules.revenue.routes import router as revenue_router
from app.modules.proof_vault.routes import router as proof_vault_router
from app.modules.chat.routes import router as chat_router
from app.modules.creative.routes import router as creative_router
from app.modules.landing.routes import router as landing_router
from app.modules.agents.routes import router as agents_router
from app.modules.public_site.routes import router as public_site_router
from app.modules.subscription.routes import router as subscription_router
from app.modules.tasks.routes import router as tasks_router
from app.modules.response_rules.routes import router as response_rules_router
from app.modules.builder.routes import router as builder_router, public_router as builder_public_router
from app.modules.builder.subdomain_routes import router as builder_subdomain_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.modules.agents.register_tools import register_all_tools
    register_all_tools()
    yield


app = FastAPI(
    title="Klarnow AI",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
# Allow all origins; credentials=False required when using allow_origins=["*"]
# Auth uses Bearer token in Authorization header (not cookies), so this is fine
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)  # pyright: ignore[reportArgumentType]


def _generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unhandled exceptions and return consistent JSON 500."""
    log = logging.getLogger("uvicorn.error")
    log.exception("Unhandled exception: %s", exc)
    if settings.app_env == "development":
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    else:
        detail = "Internal server error"
    return JSONResponse(status_code=500, content={"detail": detail})


app.add_exception_handler(Exception, _generic_exception_handler)


@app.get("/health")
def health():
    """Health check for load balancers and monitoring."""
    return {"status": "ok"}


app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(packs_router, prefix="/api/v1/packs", tags=["packs"])
app.include_router(brand_os_router, prefix="/api/v1", tags=["brand-os"])
app.include_router(campaign_router, prefix="/api/v1", tags=["campaign"])
app.include_router(conversion_page_router, prefix="/api/v1", tags=["conversion-page"])
app.include_router(sprint_router, prefix="/api/v1", tags=["sprint"])
app.include_router(clients_router, prefix="/api/v1/clients", tags=["clients"])
app.include_router(revenue_router, prefix="/api/v1/revenue", tags=["revenue"])
app.include_router(proof_vault_router, prefix="/api/v1", tags=["proof-vault"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(creative_router, prefix="/api/v1/creative", tags=["creative"])
app.include_router(landing_router, prefix="/api/v1/me", tags=["me"])
app.include_router(agents_router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(public_site_router, prefix="/api/v1/public", tags=["public"])
app.include_router(subscription_router, tags=["subscription"])
app.include_router(tasks_router, tags=["tasks"])
app.include_router(response_rules_router, tags=["response-rules"])
app.include_router(builder_router, prefix="/api/v1/builder", tags=["builder"])
app.include_router(builder_public_router, prefix="/p", tags=["sites"])
# Subdomain site serving: GET / and POST /lead when Host is *.sites_domain
app.include_router(builder_subdomain_router, prefix="", tags=["sites-subdomain"])
