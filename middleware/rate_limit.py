from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timezone
from collections import defaultdict


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients: dict[str, list[datetime]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        if "/ws" in request.url.path or request.url.path.startswith("/api/v1/uploads"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = datetime.now(timezone.utc)
        window = self.window_seconds

        # Clean old entries
        self.clients[client_ip] = [
            t for t in self.clients[client_ip]
            if (now - t).total_seconds() < window
        ]

        if len(self.clients[client_ip]) >= self.max_requests:
            oldest = min(self.clients[client_ip])
            retry_after = int(window - (now - oldest).total_seconds())
            raise HTTPException(
                status_code=429,
                detail="Too many requests",
                headers={"Retry-After": str(max(retry_after, 1))},
            )

        self.clients[client_ip].append(now)
        return await call_next(request)
