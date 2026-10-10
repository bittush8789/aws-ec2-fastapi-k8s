"""
FastAPI Application for Kubernetes Lab
Demonstrates health probes, Pod identity, and Kubernetes concepts
"""

import os
import socket
import time
from datetime import datetime, timezone

from fastapi import FastAPI, Response, status
from pydantic import BaseModel

# ── Application metadata ────────────────────────────────────────────────────
APP_VERSION = "1.0.0"
APP_NAME = "fastapi-kind-lab"
START_TIME = time.time()

app = FastAPI(
    title="FastAPI Kind Lab",
    description="Kubernetes hands-on lab — FastAPI on kind (Kubernetes in Docker)",
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Pydantic response models ─────────────────────────────────────────────────

class RootResponse(BaseModel):
    message: str
    hostname: str
    pod_ip: str
    node_name: str
    namespace: str
    version: str
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    hostname: str
    uptime_seconds: float
    timestamp: str


class InfoResponse(BaseModel):
    app_name: str
    version: str
    hostname: str
    pod_ip: str
    node_name: str
    namespace: str
    python_env: dict
    start_time: str
    uptime_seconds: float


# ── Helper ───────────────────────────────────────────────────────────────────

def get_pod_metadata() -> dict:
    """Read Kubernetes downward API env vars injected by the Deployment."""
    return {
        "hostname": socket.gethostname(),
        "pod_ip": os.environ.get("POD_IP", "unknown"),
        "node_name": os.environ.get("NODE_NAME", "unknown"),
        "namespace": os.environ.get("POD_NAMESPACE", "unknown"),
    }


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_model=RootResponse, tags=["Root"])
async def root():
    """
    Root endpoint — returns identity of the Pod serving the request.
    Useful for observing load balancing across replicas.
    """
    meta = get_pod_metadata()
    return RootResponse(
        message="Hello from FastAPI on Kubernetes (kind)! 🚀",
        hostname=meta["hostname"],
        pod_ip=meta["pod_ip"],
        node_name=meta["node_name"],
        namespace=meta["namespace"],
        version=APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/health/live", response_model=HealthResponse, tags=["Health"])
async def liveness(response: Response):
    """
    Liveness probe endpoint.
    Kubernetes restarts the container if this returns non-2xx.
    Should only fail if the app is in an unrecoverable broken state.
    """
    uptime = time.time() - START_TIME
    response.status_code = status.HTTP_200_OK
    return HealthResponse(
        status="alive",
        hostname=socket.gethostname(),
        uptime_seconds=round(uptime, 2),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/health/ready", response_model=HealthResponse, tags=["Health"])
async def readiness(response: Response):
    """
    Readiness probe endpoint.
    Kubernetes stops routing traffic if this returns non-2xx.
    Should fail if the app cannot serve traffic (e.g. DB not connected).
    """
    uptime = time.time() - START_TIME

    # Simulate a startup warm-up period (app is not ready for first 2 seconds)
    if uptime < 2.0:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            status="not_ready",
            hostname=socket.gethostname(),
            uptime_seconds=round(uptime, 2),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    response.status_code = status.HTTP_200_OK
    return HealthResponse(
        status="ready",
        hostname=socket.gethostname(),
        uptime_seconds=round(uptime, 2),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/info", response_model=InfoResponse, tags=["Info"])
async def info():
    """
    Detailed application and environment information.
    Useful for debugging Kubernetes Downward API injection.
    """
    import sys
    meta = get_pod_metadata()
    uptime = time.time() - START_TIME
    return InfoResponse(
        app_name=APP_NAME,
        version=APP_VERSION,
        hostname=meta["hostname"],
        pod_ip=meta["pod_ip"],
        node_name=meta["node_name"],
        namespace=meta["namespace"],
        python_env={
            "python_version": sys.version,
            "platform": sys.platform,
        },
        start_time=datetime.fromtimestamp(START_TIME, tz=timezone.utc).isoformat(),
        uptime_seconds=round(uptime, 2),
    )
