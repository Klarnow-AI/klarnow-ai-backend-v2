import logging
import time
import traceback
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.core.metrics import record_request, snapshot
from app.core.request_context import set_correlation_id
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
from app.modules.feedback.routes import router as feedback_router
from app.modules.ad_factory.routes import router as ad_factory_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.modules.agents.register_tools import register_all_tools
    from app.modules.packs.onboarding_jobs import recover_pending_onboarding_jobs
    log = logging.getLogger("uvicorn.error")
    log.info("CORS allowed origins: %s", settings.cors_allow_origins)
    register_all_tools()
    recover_pending_onboarding_jobs()
    yield


app = FastAPI(
    title="Klarnow AI",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
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
    response = JSONResponse(
        status_code=500,
        content={"detail": detail, "request_id": getattr(request.state, "request_id", None)},
    )
    # Add CORS headers so browser doesn't report CORS instead of 500
    origin = request.headers.get("origin")
    if origin and origin in settings.cors_allow_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
    return response


app.add_exception_handler(Exception, _generic_exception_handler)


@app.middleware("http")
async def request_observability_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    set_correlation_id(request_id)
    start = time.perf_counter()
    response: Response | None = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        status_code = response.status_code if response else 500
        record_request(request.url.path, status_code, duration_ms)
        if response is not None:
            response.headers["X-Request-ID"] = request_id
        set_correlation_id("-")


@app.get("/health")
def health():
    """Health check for load balancers and monitoring."""
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    """Simple JSON metrics for request volume and latency."""
    snap = snapshot()
    return {
        "total_requests": snap.total_requests,
        "error_requests": snap.error_requests,
        "avg_duration_ms": snap.avg_duration_ms,
        "routes": snap.routes,
    }


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
app.include_router(feedback_router, tags=["feedback"])
app.include_router(ad_factory_router, prefix="/api/v1/ad-factory", tags=["ad-factory"])
# Subdomain site serving: GET / and POST /lead when Host is *.sites_domain
app.include_router(builder_subdomain_router, prefix="", tags=["sites-subdomain"])
