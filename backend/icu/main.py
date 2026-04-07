import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from icu.api.health import router as health_router
from icu.api.v1 import router as v1_router
from icu.api.ws import router as ws_router
from icu.config import settings
from icu.realtime.pubsub import start_pubsub_listener, stop_pubsub_listener
from icu.redis_client import close_redis, init_redis

log = logging.getLogger("icu.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    await start_pubsub_listener()
    log.info("ICU API started")
    yield
    await stop_pubsub_listener()
    await close_redis()


app = FastAPI(
    title="ICU API",
    version="0.1.0",
    lifespan=lifespan,
)

_cors = settings.cors_origin_list
if _cors == ["*"] or (len(_cors) == 1 and _cors[0] == "*"):
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r".*",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health_router)
app.include_router(v1_router, prefix="/v1")
app.include_router(ws_router, prefix="/v1")
