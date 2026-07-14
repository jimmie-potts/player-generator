from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from formula_preview_api.config import PreviewSettings
from formula_preview_api.errors import FieldError, PreviewAPIError
from formula_preview_api.models import (
    BaselineResponse,
    ErrorResponse,
    FormulaResponse,
    MetricsResponse,
    PlayerDetailResponse,
    PreviewRequest,
    PreviewResponse,
    SearchResponse,
)
from formula_preview_api.service import PreviewService


def _validation_path(location: tuple[Any, ...]) -> str:
    parts = [str(value) for value in location if value not in {"body", "query", "path"}]
    return ".".join(parts) or "request"


def create_app(
    settings: PreviewSettings,
    *,
    service: PreviewService | None = None,
) -> FastAPI:
    preview = service or PreviewService(settings)
    preview_executor = ThreadPoolExecutor(
        max_workers=2,
        thread_name_prefix="formula-preview",
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            preview_executor.shutdown(wait=True, cancel_futures=True)

    app = FastAPI(
        title="Player Generator Formula Preview API",
        version="1.0.0",
        description=(
            "Versioned, read-only formula inspection and temporary recalculation over one "
            "integrity-checked reference cohort."
        ),
        lifespan=lifespan,
    )
    app.state.preview_service = preview
    app.state.preview_executor = preview_executor

    @app.exception_handler(PreviewAPIError)
    async def preview_error_handler(_request: Request, error: PreviewAPIError) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content=error.payload())

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        _request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        fields = [
            FieldError(
                path=_validation_path(tuple(item.get("loc", ()))),
                code=str(item.get("type", "invalid")),
                message=str(item.get("msg", "Invalid value.")),
            )
            for item in error.errors()
        ]
        api_error = PreviewAPIError(
            status_code=422,
            code="invalid_request",
            message="Request validation failed.",
            fields=fields,
        )
        return JSONResponse(status_code=422, content=api_error.payload())

    @app.exception_handler(HTTPException)
    async def http_error_handler(_request: Request, error: HTTPException) -> JSONResponse:
        code = "method_not_allowed" if error.status_code == 405 else "http_error"
        api_error = PreviewAPIError(
            status_code=error.status_code,
            code=code,
            message=str(error.detail),
        )
        return JSONResponse(status_code=error.status_code, content=api_error.payload())

    @app.get(
        "/api/v1/formula",
        response_model=FormulaResponse,
        responses={422: {"model": ErrorResponse}},
    )
    async def formula() -> FormulaResponse:
        return preview.formula()

    @app.get(
        "/api/v1/metrics",
        response_model=MetricsResponse,
        responses={422: {"model": ErrorResponse}},
    )
    async def metrics() -> MetricsResponse:
        return preview.metrics()

    @app.get(
        "/api/v1/players",
        response_model=BaselineResponse,
        responses={422: {"model": ErrorResponse}},
    )
    async def baseline(
        limit: int | None = None,
        pinned_player_id: Annotated[
            list[str] | None,
            Query(alias="pinnedPlayerId"),
        ] = None,
    ) -> BaselineResponse:
        return preview.baseline(
            limit=limit,
            pinned_player_ids=pinned_player_id or (),
        )

    @app.get(
        "/api/v1/players/search",
        response_model=SearchResponse,
        responses={422: {"model": ErrorResponse}},
    )
    async def search(
        q: Annotated[str, Query(min_length=1)],
        limit: int | None = None,
    ) -> SearchResponse:
        return preview.search(q, limit=limit)

    @app.get(
        "/api/v1/players/{player_id}",
        response_model=PlayerDetailResponse,
        responses={404: {"model": ErrorResponse}},
    )
    async def detail(player_id: str) -> PlayerDetailResponse:
        return preview.detail(player_id)

    @app.post(
        "/api/v1/previews",
        response_model=PreviewResponse,
        responses={
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
        },
    )
    async def previews(request: PreviewRequest) -> PreviewResponse:
        calculation = preview_executor.submit(preview.preview, request)
        try:
            while not calculation.done():
                await asyncio.sleep(0.005)
            return calculation.result()
        except asyncio.CancelledError:
            calculation.cancel()
            raise

    return app
