"""Health endpoints used by Kubernetes probes."""

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    # Keep liveness independent of databases and other external services.
    return {"status": "ok"}


@router.get("/ready")
async def readiness(request: Request) -> dict[str, str]:
    if not request.app.state.ready:
        raise HTTPException(status_code=503, detail="Service is not ready")
    # Add bounded checks for dependencies required to serve traffic here.
    return {"status": "ready"}
