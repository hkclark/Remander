# Authentication

Remander uses server-side session authentication built on Starlette's `SessionMiddleware`. Email
address is the username. Both dashboard pages remain public; all other routes require a valid
session.

---

## Data Model

### `User` — `src/remander/models/user.py`

| Field | Type | Notes |
|---|---|---|
| `id` | IntField PK | |
| `email` | CharField(255) UNIQUE | the username |
| `display_name` | CharField(255) nullable | shown in nav and notification emails |
| `password_hash` | CharField(255) nullable | null until invite is accepted |
| `token` | CharField(255) nullable UNIQUE | personal `?token=` auth; null = disabled |
| `is_active` | BooleanField default=True | disable without deleting |
| `is_admin` | BooleanField default=False | gates user management UI |
| `created_at` / `updated_at` | DatetimeField | |

### `UserAccessLog` — `src/remander/models/user_access_log.py`

| Field | Type | Notes |
|---|---|---|
| `id` | IntField PK | |
| `user` | ForeignKeyField → User | ON DELETE CASCADE |
| `timestamp` | DatetimeField auto_now_add | |
| `ip_address` | CharField(45) nullable | IPv4 + IPv6 |
| `method` | CharField(20) | `"password"` \| `"token"` \| `"password_reset"` \| `"invitation"` |
| `path` | CharField(500) nullable | the route accessed |

---

## Session Mechanism

`SessionMiddleware` (Starlette built-in) stores an HMAC-signed cookie containing `{"user_id": 42}`.
No external store — the signed cookie is self-contained. Session data is validated on every request,
so revoking a user (`is_active=False`) takes effect immediately on the next request.

```python
# main.py
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)
```

New setting in `config.py` (`.env` only — not editable in the admin UI, as changing it invalidates
all active sessions):

```python
session_secret_key: str = ""   # must be set in .env
```

The lifespan asserts this is non-empty at startup.

---

## Route Protection Strategy

**Router-level `dependencies=`** in `main.py` — zero changes to individual handler signatures:

```python
from remander.auth import get_current_user, require_admin

# Public:
app.include_router(dashboard_router)            # GET /
app.include_router(guest_dashboard_router)      # GET /d, POST /d/...

# Protected (session required):
app.include_router(devices_router,            dependencies=[Depends(get_current_user)])
app.include_router(bitmasks_router,           dependencies=[Depends(get_current_user)])
app.include_router(tags_router,               dependencies=[Depends(get_current_user)])
app.include_router(commands_router,           dependencies=[Depends(get_current_user)])
app.include_router(dashboard_buttons_router,  dependencies=[Depends(get_current_user)])
app.include_router(activity_router,           dependencies=[Depends(get_current_user)])
app.include_router(admin_router,              dependencies=[Depends(get_current_user)])

# Auth routes (no protection):
app.include_router(auth_router)               # /login, /logout, /forgot-password, etc.

# Admin user management (admin flag required):
app.include_router(users_router,              dependencies=[Depends(require_admin)])
```

---

## Auth Dependencies — `src/remander/auth.py`

```python
class RequiresLoginException(Exception): ...

# Registered on app:
@app.exception_handler(RequiresLoginException)
async def redirect_to_login(request, exc):
    # Full-page request: RedirectResponse to /login?next=<path>
    # HTMX partial (HX-Request header): respond with HX-Redirect header

async def get_current_user(request: Request) -> User:
    """Fetch the authenticated user from the session. Raises RequiresLoginException if not logged in."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise RequiresLoginException()
    user = await User.get_or_none(id=user_id, is_active=True)
    if user is None:
        request.session.clear()
        raise RequiresLoginException()
    return user

async def get_current_user_optional(request: Request) -> User | None:
    """Returns the authenticated user or None. Used on public routes."""

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Extends get_current_user to also require is_admin=True."""
    if not current_user.is_admin:
        raise HTTPException(403)
    return current_user
```

`RequiresLoginException` is a custom exception (rather than `HTTPException`) so the handler can
distinguish auth redirects from real errors and can emit `HX-Redirect` for HTMX partial requests.

---

## Token Auth on Dashboards

Users can set a personal `token` on their account. Passing `?token=<value>` on either dashboard
page looks up the user by token and attributes the request to them — **without creating a session**.
Token auth is stateless by design: the token in the URL authenticates the device, not the browser.

```python
@router.get("/")
async def dashboard(request: Request, token: str | None = None):
    user = await get_current_user_optional(request)
    if user is None and token:
        user = await User.get_or_none(token=token, is_active=True)
        if user:
            await log_access(user, request.client.host, method="token", path="/")
    ...
```

If a user has no token set (`token=NULL`), they can only authenticate via username and password.

---

## Auth Routes — `src/remander/routes/auth.py`

| Route | Purpose |
|---|---|
| `GET /login` | Render login form; redirect to `/` if already logged in |
| `POST /login` | Verify email + bcrypt password; set `session["user_id"]`; log access; redirect |
| `GET /logout` | Clear session; redirect to `/login` |
| `GET /forgot-password` | Render email input form |
| `POST /forgot-password` | Look up user; send reset email; always show generic "if registered, you'll receive a link" |
| `GET /reset-password?token=` | Validate signed token; render new-password form |
| `POST /reset-password` | Validate token; hash and save new password; log `method="password_reset"`; redirect to `/login` |
| `GET /set-password?token=` | Validate invite token; render initial set-password form |
| `POST /set-password` | Validate token; set password (only if `password_hash` is still null); log `method="invitation"` |

---

## Password Reset & Invitation Tokens

Both flows use `itsdangerous.URLSafeTimedSerializer` — a standard Python library for HMAC-signed,
time-limited tokens. The same `session_secret_key` is reused with different salts so the keys are
effectively independent.

```python
def make_token(payload: str, salt: str, secret: str) -> str:
    return URLSafeTimedSerializer(secret, salt=salt).dumps(payload)

def verify_token(token: str, salt: str, secret: str, max_age: int) -> str | None:
    try:
        return URLSafeTimedSerializer(secret, salt=salt).loads(token, max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None
```

| Flow | Salt | Expiry | Payload |
|---|---|---|---|
| Password reset | `"password-reset"` | 1 hour | user's email |
| Invitation | `"invitation"` | 7 days | user's email |

**POST /forgot-password always returns the same response** regardless of whether the email is
registered — this prevents email enumeration attacks.

**POST /set-password checks `password_hash is None`** before accepting a new password — this
ensures an invite link can only be used once.

---

## Admin Users CRUD — `src/remander/routes/users.py`

Prefix `/admin/users`, protected by `require_admin`:

| Route | Purpose |
|---|---|
| `GET /admin/users` | List all users: email, display name, active, admin, last access |
| `POST /admin/users/create` | Create user (email, display_name, is_admin); send invitation email |
| `POST /admin/users/{id}/toggle-active` | Enable/disable user |
| `POST /admin/users/{id}/toggle-admin` | Grant/revoke admin flag |
| `POST /admin/users/{id}/resend-invite` | Regenerate + resend invite if password not yet set |
| `GET /admin/users/{id}/history` | Paginated `UserAccessLog` for that user |

---

## Command Attribution

`Command.initiated_by_user` and `Command.initiated_by_ip` already exist on the model and are
already rendered in completion notification emails by `notification_templates.py`. The only change
needed is in `routes/commands.py`: replace the current insecure `?user=` query-param approach with
`Depends(get_current_user)`.

```python
@router.post("/execute/set-away-now")
async def execute_set_away_now(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> Response:
    cmd = await create_command(
        CommandType.SET_AWAY_NOW,
        initiated_by_ip=request.client.host if request.client else None,
        initiated_by_user=current_user.display_name or current_user.email,
    )
```

No changes to `WorkflowState`, `WorkflowDeps`, `NotifyNode`, or `render_notification()` —
they already consume `Command.initiated_by_user` correctly.

Guest dashboard commands (`/d/execute/...`) remain anonymous. No user attribution for guest actions.

---

## Email Helper — `src/remander/services/email.py`

The existing `EmailNotificationSender` sends to the configured `smtp_to` (admin address). Auth
flows send to the user's own email address. A new helper wraps the same SMTP logic with a dynamic
`to` recipient:

```python
async def send_auth_email(to: str, subject: str, body: str) -> None:
    """Send to a user's email address using the configured SMTP settings."""
```

---

## New Dependencies

```bash
uv add "passlib[bcrypt]" itsdangerous
```

`python-multipart` and `aiosmtplib` are already present.

---

## Configuration

New settings (all `.env`-only — listed in `READ_ONLY_SETTINGS`, not editable in the admin UI):

| Key | Default | Purpose |
|---|---|---|
| `session_secret_key` | `""` | HMAC key for session cookies and signed tokens |
| `password_reset_expiry_seconds` | `3600` | Reset link validity (1 hour) |
| `invitation_expiry_seconds` | `604800` | Invite link validity (7 days) |

---

## Migration

Migration 8: two new tables (`user`, `user_access_log`) plus indexes on `user.token` and
`user_access_log.user_id`. Follow the standard `--empty` workflow from `CLAUDE.md`.

```sql
-- upgrade()
CREATE TABLE "user" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "display_name" VARCHAR(255),
    "password_hash" VARCHAR(255),
    "token" VARCHAR(255) UNIQUE,
    "is_active" INT NOT NULL DEFAULT 1,
    "is_admin" INT NOT NULL DEFAULT 0,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE "user_access_log" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    "timestamp" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "ip_address" VARCHAR(45),
    "method" VARCHAR(20) NOT NULL,
    "path" VARCHAR(500)
);

CREATE INDEX "idx_user_access_log_user_id" ON "user_access_log" ("user_id");
CREATE INDEX "idx_user_token" ON "user" ("token");

-- downgrade()
DROP TABLE IF EXISTS "user_access_log";
DROP TABLE IF EXISTS "user";
```

---

## Templates

| Path | Purpose |
|---|---|
| `templates/auth/login.html` | Email + password fields; "Forgot password" link; optional `?message=` banner |
| `templates/auth/forgot_password.html` | Single email field |
| `templates/auth/reset_password.html` | New password + confirm; expired-token error state |
| `templates/auth/set_password.html` | Invitation: initial password form |
| `templates/admin/users.html` | User table with status, admin flag, last access, View History link |
| `templates/admin/user_history.html` | Paginated access log for a single user |

`base.html` gains a user info section in the nav (display name or email, Sign Out link), shown only
when `current_user` is in the template context.

---

## Files to Create

| File | Purpose |
|---|---|
| `src/remander/models/user.py` | `User` Tortoise model |
| `src/remander/models/user_access_log.py` | `UserAccessLog` Tortoise model |
| `src/remander/auth.py` | Dependencies, token utilities, `RequiresLoginException` handler |
| `src/remander/routes/auth.py` | Login, logout, forgot/reset password, set-password routes |
| `src/remander/routes/users.py` | Admin user CRUD routes |
| `src/remander/services/user.py` | `create_user`, `get_user_by_email`, `get_user_by_token`, `set_password`, `list_users`, `log_access` |
| `src/remander/services/email.py` | `send_auth_email` helper |
| `src/remander/templates/auth/login.html` | |
| `src/remander/templates/auth/forgot_password.html` | |
| `src/remander/templates/auth/reset_password.html` | |
| `src/remander/templates/auth/set_password.html` | |
| `src/remander/templates/admin/users.html` | |
| `src/remander/templates/admin/user_history.html` | |
| `migrations/models/8_<timestamp>_add_auth_tables.py` | DB migration |
| `tests/test_auth.py` | Auth service unit tests |
| `tests/test_routes_auth.py` | Login/logout/reset/invite route tests |
| `tests/test_routes_users.py` | Admin user management route tests |
| `tests/factories/user.py` | `create_user` test factory |

---

## Files to Modify

| File | Change |
|---|---|
| `src/remander/models/__init__.py` | Add `User`, `UserAccessLog` |
| `src/remander/models/enums.py` | Add `AuthMethod` StrEnum |
| `src/remander/config.py` | Add `session_secret_key`, `password_reset_expiry_seconds`, `invitation_expiry_seconds` |
| `src/remander/main.py` | Add `SessionMiddleware`, `RequiresLoginException` handler, router-level deps, new routers |
| `src/remander/routes/commands.py` | Replace `?user=` query-param with `Depends(get_current_user)` in execute handlers |
| `src/remander/templates/base.html` | Add nav user info and Sign Out link |
| `src/remander/templates/admin/index.html` | Add Users card |
| `pyproject.toml` | Add `passlib[bcrypt]`, `itsdangerous` |
| `tests/conftest.py` | Add `logged_in_client` fixture using `dependency_overrides` |

---

## Test Strategy

Router-level auth will cause all existing protected route tests to return 302. Fix with FastAPI's
`dependency_overrides` — add a `logged_in_client` fixture to `conftest.py`:

```python
@pytest.fixture
async def logged_in_client(db) -> AsyncIterator[AsyncClient]:
    from remander.auth import get_current_user
    from remander.main import app

    fake_user = User(id=1, email="test@example.com", is_active=True, is_admin=True)
    app.dependency_overrides[get_current_user] = lambda: fake_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

Existing protected route tests are updated to use `logged_in_client` instead of `client`.

---

## Implementation Order (TDD)

1. `uv add "passlib[bcrypt]" itsdangerous`
2. `session_secret_key` in `config.py` + startup assertion in `main.py`
3. `User` + `UserAccessLog` models + `AuthMethod` enum — **tests first**
4. Migration 8
5. `services/user.py` — **tests first**
6. `services/email.py`
7. `auth.py` (dependencies, token utils, exception handler) — **unit tests**
8. `SessionMiddleware` in `main.py`
9. `routes/auth.py` + auth templates — **route tests**
10. Router-level protection in `main.py` + update existing test fixtures to use `logged_in_client`
11. `routes/commands.py` — replace `?user=` with `Depends(get_current_user)`
12. `routes/users.py` + admin user templates — **route tests**
13. `base.html` + `admin/index.html` updates
