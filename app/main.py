"""FastAPI app: JSON API under /api and the web interface at /."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .db import HistoryStore
from .prompts import TONES
from .providers import ProviderError, build_provider
from .refiner import Refiner
from .schemas import RefineRequest, RefineResponse, StatsResponse

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    provider = build_provider(settings)
    refiner = Refiner(provider, native_language=settings.native_language)
    store = HistoryStore(settings.db_path)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        store.init()
        yield

    app = FastAPI(title="SecondLang", version="1.0.0", lifespan=lifespan,
                  description="Refine English phrases for formal or family conversations.")

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "provider": provider.name, "model": provider.model}

    @app.get("/api/tones")
    async def tones():
        return [{"id": k, "label": v["label"], "audience": v["audience"]} for k, v in TONES.items()]

    @app.post("/api/refine", response_model=RefineResponse)
    async def refine(req: RefineRequest):
        try:
            result = await refiner.refine(req.text, req.tone, req.context)
        except ProviderError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return store.save(result) if req.save else result

    @app.get("/api/history", response_model=list[RefineResponse])
    async def history(limit: int = Query(50, ge=1, le=500)):
        return store.list(limit)

    @app.delete("/api/history/{item_id}")
    async def delete_item(item_id: int):
        if not store.delete(item_id):
            raise HTTPException(status_code=404, detail="Not found")
        return {"deleted": item_id}

    @app.delete("/api/history")
    async def clear_history():
        return {"deleted": store.clear()}

    @app.get("/api/stats", response_model=StatsResponse)
    async def stats():
        return store.stats()

    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


app = create_app()
