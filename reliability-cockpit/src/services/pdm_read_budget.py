"""Inspection LIST wire budget; mirrors the unchanged two-MiB QA proxy ceiling.

No projection, truncation or input/storage limit change. Use the same encoder and
JSON response implementation as the owning FastAPI router, including model-level
legacy serializers, UTF-8, null/boolean values and timestamp precision.
"""
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse
from src.domain.engineering import EngineeringError

PDM_PAGE_BYTES = 2 * 1024 * 1024


def wire_size(value):
    return len(JSONResponse(jsonable_encoder(value)).body)


def require_page_budget(size):
    if size > PDM_PAGE_BYTES:
        raise EngineeringError("PDM_PAGE_BODY_LIMIT", 413)


def bounded_inspection_page(page):
    require_page_budget(wire_size(page))
    return page
