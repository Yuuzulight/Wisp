"""HTTP API — single /query endpoint. Localhost-only, no auth (see design doc)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from wisp.config import settings
from wisp.pipeline import run_query

app = FastAPI(title="Wisp")


class QueryRequest(BaseModel):
    query: str
    backend: Literal["local", "claude"] = "local"


@app.post("/query")
async def query(request: QueryRequest) -> dict:
    result = await run_query(request.query, request.backend, settings)
    return asdict(result)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
