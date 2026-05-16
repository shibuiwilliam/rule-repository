"""REST API router for serving seed/sample data.

Serves static JSON files from sample_rules/seed/ so frontend pages
can fetch sample data instead of hardcoding it.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/seed", tags=["seed"])

# Resolve seed data directory (sample_rules/seed/ at repo root)
_SEED_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "sample_rules" / "seed"

# Cache loaded files
_cache: dict[str, dict] = {}


def _load_seed(name: str) -> dict:
    """Load a seed JSON file by name (without extension)."""
    if name in _cache:
        return _cache[name]

    path = _SEED_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Seed data '{name}' not found")

    data = json.loads(path.read_text(encoding="utf-8"))
    _cache[name] = data
    return data


@router.get("/{domain}")
async def get_seed_data(domain: str) -> JSONResponse:
    """Get seed data for a domain (hr, legal, compliance, security, sales, marketing, admin)."""
    data = _load_seed(domain)
    return JSONResponse(content=data)


@router.get("/{domain}/{section}")
async def get_seed_section(domain: str, section: str) -> JSONResponse:
    """Get a specific section of seed data."""
    data = _load_seed(domain)
    if section not in data:
        raise HTTPException(status_code=404, detail=f"Section '{section}' not found in '{domain}'")
    return JSONResponse(content=data[section])
