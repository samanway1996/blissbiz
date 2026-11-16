from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.services.images import MAX_IMAGE_BYTES


class UploadLimitMiddleware:
    """Bound upload bodies before multipart parsing, including chunked requests."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if not (
            scope["type"] == "http"
            and scope["method"] == "PUT"
            and path.startswith("/api/v1/admin/businesses/")
            and path.endswith(("/logo", "/image"))
        ):
            await self.app(scope, receive, send)
            return
        # Permit multipart headers/boundaries in addition to the 5 MiB file.
        limit = MAX_IMAGE_BYTES + 64 * 1024
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > limit:
                response = JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "image_too_large",
                            "message": "Upload request exceeds the size limit.",
                        }
                    },
                    headers={"Cache-Control": "no-store"},
                )
                await response(scope, receive, send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)
