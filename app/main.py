from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from app.modules.launch_pack.routes import router as launch_pack_router
from app.modules.chat.routes import router as chat_router
from app.modules.creative.routes import router as creative_router
from app.modules.landing.routes import router as landing_router
from app.modules.agents.routes import router as agents_router
from app.modules.public_site.routes import router as public_site_router
from app.modules.subscription.routes import router as subscription_router
from app.modules.tasks.routes import router as tasks_router
from app.modules.response_rules.routes import router as response_rules_router
from app.modules.builder.routes import router as builder_router, public_router as builder_public_router


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
# In development, always allow localhost frontend; avoid empty allow_origins
_dev_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
_cors_origins = [settings.frontend_url] if settings.frontend_url else []
if settings.app_env == "development":
    _cors_origins = list(dict.fromkeys([*_cors_origins, *_dev_origins]))
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins if _cors_origins else _dev_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)  # pyright: ignore[reportArgumentType]


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
app.include_router(launch_pack_router, prefix="/api/v1", tags=["launch-pack"])
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
