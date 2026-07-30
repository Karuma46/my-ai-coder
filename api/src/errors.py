from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    error: dict[str, object] = {
        "code": code,
        "message": message,
        "requestId": request.headers.get("x-request-id") or f"req_{uuid4().hex[:12]}",
    }
    if details:
        error["details"] = details
    return JSONResponse(status_code=status_code, content={"error": error})
