"""
services/health_service.py — Application Health Check Service
=============================================================

HealthService provides the operational status of the service. It is called
by the GET /health route handler and returns a HealthResponse object.

Why a class here:
    Encapsulating health logic in a class makes it extensible — future
    checks (database ping, ChromaDB connectivity, LLM reachability) can be
    added as private methods without changing the route handler or the
    HealthResponse schema.
"""

from models.response_models import HealthResponse
from core.logger import get_logger

logger = get_logger(__name__)

# Application version — update this on each release.
APP_VERSION = "1.0.0"


class HealthService:
    """
    Provides the current operational status of the AI Support Agent API.

    The ``check()`` method is the sole public interface. Future versions
    can add connectivity probes (DB, ChromaDB, Groq) here without
    changing the route handler or response schema.
    """

    def check(self) -> HealthResponse:
        """
        Perform a lightweight health check and return the current status.

        Used by load balancers, Kubernetes liveness probes, and monitoring
        dashboards. Intentionally fast — no I/O is performed.

        Returns:
            HealthResponse: A Pydantic model with status, version, and timestamp.
        """
        logger.debug("Health check probe received.")
        return HealthResponse(status="healthy", version=APP_VERSION)
