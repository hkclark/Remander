"""Reverse proxy support — root_path injection middleware."""

from starlette.types import ASGIApp, Receive, Scope, Send


class ProxyPrefixMiddleware:
    """Inject ``root_path`` for requests forwarded by a trusted reverse proxy.

    The expected proxy setup is the standard one: the proxy strips the path prefix
    before forwarding, so the app sees ``/login`` rather than ``/PREFIX/login``.
    This middleware's job is purely URL generation — it sets ``scope["root_path"]``
    so that ``request.root_path`` in redirect handlers and ``{{ root_path }}`` in
    Jinja2 templates produce correct public-facing URLs (e.g. ``/PREFIX/login``
    instead of ``/login``), which the browser then routes back through the proxy.

    Behaviour:
    1. Both ``prefix`` and ``token`` must be non-empty, otherwise the middleware is a
       transparent no-op (local access without proxy config is unaffected).
    2. Validates the ``X-Forwarded-Token`` header — only injects ``root_path`` when the
       header value exactly matches ``token``.
    3. Sets ``scope["root_path"]`` to ``prefix`` on authenticated proxy requests.
    4. Optionally overwrites ``scope["scheme"]`` with ``scheme`` (e.g. ``"https"``) so
       ``request.url`` and email link generation reflect the public-facing scheme.

    The path in ``scope["path"]`` is **not modified** — the proxy already stripped it.
    """

    def __init__(self, app: ASGIApp, prefix: str, token: str, scheme: str = "") -> None:
        self.app = app
        self.prefix = prefix.rstrip("/")
        self.token = token
        self.scheme = scheme
        # Force to be absolute path
        if self.prefix and not self.prefix.startswith("/"):
            self.prefix = "/" + self.prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket") and self.prefix and self.token:
            headers = dict(scope.get("headers", []))
            request_token = headers.get(b"x-forwarded-token", b"").decode()
            if request_token == self.token:
                scope = dict(scope)
                scope["root_path"] = self.prefix
                if self.scheme:
                    scope["scheme"] = self.scheme

        await self.app(scope, receive, send)
