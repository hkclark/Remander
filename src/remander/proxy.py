"""Reverse proxy support — path-prefix stripping middleware."""

from starlette.types import ASGIApp, Receive, Scope, Send


class ProxyPrefixMiddleware:
    """Strip a path prefix from incoming requests forwarded by a trusted reverse proxy.

    When a proxy forwards ``https://public.example.com/PREFIX/login`` to this app as
    ``http://internal/PREFIX/login`` (keeping the prefix intact), this middleware:

    1. Validates the ``X-Forwarded-Token`` header to confirm the request came from
       the configured trusted proxy (when ``token`` is non-empty).
    2. Strips ``prefix`` from ``scope["path"]`` so route handlers see ``/login``.
    3. Sets ``scope["root_path"]`` to ``prefix`` so ``request.root_path`` and Jinja2's
       ``{{ root_path }}`` global produce correct prefix-aware URLs.
    4. Optionally overwrites ``scope["scheme"]`` with ``scheme`` (e.g. ``"https"``) so
       ``request.url`` reflects the public-facing URL.

    If ``prefix`` is empty the middleware is a transparent no-op.
    If ``token`` is empty, prefix stripping applies to *all* requests whose path starts
    with the prefix (useful for testing; less secure in production).
    """

    def __init__(self, app: ASGIApp, prefix: str, token: str, scheme: str = "") -> None:
        self.app = app
        self.prefix = prefix.rstrip("/")
        self.token = token
        self.scheme = scheme

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket") and self.prefix:
            path: str = scope.get("path", "")
            if path.startswith(self.prefix):
                # Check token if one is configured
                if self.token:
                    headers = dict(scope.get("headers", []))
                    request_token = headers.get(b"x-forwarded-token", b"").decode()
                    if request_token != self.token:
                        await self.app(scope, receive, send)
                        return

                new_path = path[len(self.prefix) :] or "/"
                scope = dict(scope)
                scope["path"] = new_path
                scope["raw_path"] = new_path.encode()
                scope["root_path"] = self.prefix

                if self.scheme:
                    scope["scheme"] = self.scheme

        await self.app(scope, receive, send)
