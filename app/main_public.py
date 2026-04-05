import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Public app ready (reads from Valkey + SQLite, no writes)")
    yield


from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest


ALLOWED_ORIGINS = {
    "https://docs.smileeyes.de",
    "https://docs2.smileeyes.de",
    "https://docs3.smileeyes.de",
}


class EmbedMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        origin = request.headers.get("origin", "")

        # Handle CORS preflight (OPTIONS) for Private Network Access
        if request.method == "OPTIONS":
            from starlette.responses import Response
            resp = Response(status_code=204)
            if origin in ALLOWED_ORIGINS:
                resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
            resp.headers["Access-Control-Allow-Private-Network"] = "true"
            resp.headers["Access-Control-Max-Age"] = "86400"
            return resp

        response = await call_next(request)
        response.headers["Content-Security-Policy"] = "frame-ancestors 'self' https://docs.smileeyes.de https://docs2.smileeyes.de https://docs3.smileeyes.de"
        if "X-Frame-Options" in response.headers:
            del response.headers["X-Frame-Options"]
        if origin in ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response


app = FastAPI(title="Uptime Status", lifespan=lifespan)
app.add_middleware(EmbedMiddleware)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")

from app.routers import public, ws as ws_router  # noqa: E402

app.include_router(public.router)
app.include_router(ws_router.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
