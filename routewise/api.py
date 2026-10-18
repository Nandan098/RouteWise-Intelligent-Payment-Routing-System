"""FastAPI application and HTTP endpoints."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from .config import Settings
from .database import Database
from .schemas import (
    FeedbackRequest, FeedbackResponse, GatewayResponse, HealthResponse,
    RouteRequest, RouteResponse, StatsResponse,
)
from .service import (
    FeedbackConflict, IdempotencyConflict, NoHealthyGateway, RouteNotFound,
    RoutingService,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def create_app(
    database_path: str | Path | None = None,
    gateway_config_path: str | Path | None = None,
) -> FastAPI:
    settings = Settings.from_env(database_path, gateway_config_path)
    settings.validate()
    database = Database(settings.database_path)
    service = RoutingService(database, settings)
    app = FastAPI(
        title="RouteWise API",
        version="1.0.0",
        description=(
            "Educational payment-gateway routing simulator. It selects among simulated gateways; "
            "it does not process or move real money."
        ),
    )
    app.state.settings = settings
    app.state.database = database
    app.state.service = service

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    def health() -> dict:
        return {
            "status": "ok",
            "native_cpp_available": service.native_cpp_available(),
            "database": "sqlite",
        }

    @app.get("/gateways", response_model=list[GatewayResponse], tags=["Routing"])
    def gateways() -> list[dict]:
        return service.get_gateways()

    @app.post("/route", response_model=RouteResponse, tags=["Routing"])
    def route_transaction(request: RouteRequest) -> dict:
        try:
            return service.route(request)
        except IdempotencyConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except NoHealthyGateway as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Routing request failed")
            raise HTTPException(status_code=500, detail="Routing request could not be completed") from exc

    @app.post("/feedback", response_model=FeedbackResponse, tags=["Routing"])
    def feedback(request: FeedbackRequest) -> dict:
        try:
            return service.record_feedback(request)
        except RouteNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except FeedbackConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Feedback recording failed")
            raise HTTPException(status_code=500, detail="Feedback could not be recorded") from exc

    @app.get("/transactions/{transaction_id}", response_model=RouteResponse, tags=["Routing"])
    def get_transaction(transaction_id: str) -> dict:
        result = service.get_route(transaction_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Transaction route not found")
        return result

    @app.get("/routes", response_model=list[RouteResponse], tags=["Routing"])
    def recent_routes(limit: int = Query(default=20, ge=1, le=100)) -> list[dict]:
        return service.list_routes(limit)

    @app.get("/stats", response_model=StatsResponse, tags=["Analytics"])
    def stats() -> dict:
        return service.get_stats()

    @app.exception_handler(ValueError)
    async def value_error_handler(_request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return app
