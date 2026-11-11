from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send, Message


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, *, hsts: bool = False):
        self.app = app
        self.headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Cross-Origin-Opener-Policy": "same-origin",
        }
        if hsts:
            self.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in self.headers.items():
                    headers.setdefault(name, value)
            await send(message)

        await self.app(scope, receive, send_wrapper)