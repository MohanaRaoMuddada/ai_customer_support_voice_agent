"""
api/routes/health.py — GET /health Route
==========================================

Responsibility: receive the request, delegate to HealthService, return the response.
Zero business logic lives here.
"""

from fastapi import APIRouter, status

from models.response_models import HealthResponse
from services.health_service import HealthService

health_router = APIRouter()

# Module-level service instance. In a larger application this would be
# injected via FastAPI's Depends() mechanism.
_health_service = HealthService()


@health_router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="API Health Check",
    description=(
        "Reports the service operational status, current version, and UTC timestamp. "
        "Consumed by load balancers, Kubernetes liveness probes, and monitoring dashboards."
    ),
)
def health_check() -> HealthResponse:
    """
    Lightweight liveness probe endpoint.

    Intentionally synchronous (``def``, not ``async def``) — no I/O is
    performed, so there is no benefit to async here.
    """
    return _health_service.check()
