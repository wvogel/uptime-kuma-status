import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import engine
from app.models import Base
from app.cache import monitor_fetcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Running migrations...")
    from app.migrate import run_migrations
    run_migrations()
    log.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    Path("data/logos").mkdir(parents=True, exist_ok=True)

    log.info("Starting monitor fetcher...")
    monitor_fetcher.start()
    yield
    log.info("Stopping monitor fetcher...")
    await monitor_fetcher.stop()


app = FastAPI(title="Uptime Status Admin", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")

from app.routers import admin  # noqa: E402

app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
