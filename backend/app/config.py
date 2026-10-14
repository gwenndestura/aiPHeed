from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # extra="ignore": the .env carries fetcher API keys that individual scripts
    # read directly. Forbidding them made `alembic` and anything importing
    # settings fail on a file that was otherwise valid.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite+aiosqlite:///./aipheed.db"
    DB_ECHO: bool = False
    SECRET_KEY: str = "changeme"
    MODEL_PATH: str = "models"
    PSA_MAIN_URL: str = "https://psa.gov.ph"
    PSA_RSSO_URL: str = "https://rsso04a.psa.gov.ph"
    DATA_RAW_PATH: str = "data/raw"

    # ── Auth ──────────────────────────────────────────────────────────────
    # Only addresses in this domain may hold an account. The frontend checked
    # this client-side, where anyone could edit it; it is enforced here now.
    ADMIN_EMAIL_DOMAIN: str = "calabarzon.da.gov.ph"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_SECONDS: int = 3600

    # ── Sessions (refresh tokens) ─────────────────────────────────────────
    # The access token above lives in browser memory only, so a reload loses
    # it. A refresh token in an httpOnly cookie brings the session back. See
    # app/services/sessions.py.
    #   idle: signed out after this long without a refresh (page load, or
    #         access-token renewal while working)
    #   max:  signed out this long after signing in, however active
    REFRESH_TOKEN_IDLE_TTL_SECONDS: int = 8 * 3600
    REFRESH_TOKEN_MAX_TTL_SECONDS: int = 7 * 24 * 3600
    # strict | lax | none. Strict works when the frontend and the API are on
    # the same site (e.g. localhost:8080 + localhost:8000, or app.example.ph +
    # api.example.ph). A cross-site deployment (a *.vercel.app frontend calling
    # an API on another domain) needs "none" -- but only after the CORS preview
    # regex (CORS_PREVIEW_REGEX) is pinned to this project's own deployments
    # (QA_REPORT SEC-08): with SameSite=None the browser sends the cookie on
    # cross-site requests, and CORS is then what stops other sites using it.
    REFRESH_COOKIE_SAMESITE: str = "strict"
    # Leave true. It is relaxed automatically only for plain-http requests to
    # localhost / 127.0.0.1, where browsers would otherwise drop the cookie.
    REFRESH_COOKIE_SECURE: bool = True

    @field_validator("REFRESH_COOKIE_SAMESITE")
    @classmethod
    def _samesite(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("strict", "lax", "none"):
            raise ValueError("REFRESH_COOKIE_SAMESITE must be strict, lax or none")
        return v

    # ── API docs ──────────────────────────────────────────────────────────
    # /docs, /redoc and /openapi.json list every route, admin ones included.
    # Off unless asked for, so a deployment does not publish its own map.
    ENABLE_API_DOCS: bool = False

    # ── Rate limiting ─────────────────────────────────────────────────────
    # Counters are per-process; behind multiple workers the effective limit
    # multiplies by the worker count. See app/services/ratelimit.py.
    RATE_LIMIT_ENABLED: bool = True
    # Only set this when a reverse proxy is definitely in front. If the app is
    # directly reachable, trusting X-Forwarded-For lets a caller forge a fresh
    # identity per request and the limits become decorative.
    RATE_LIMIT_TRUST_FORWARDED: bool = False
    RATE_LIMIT_LOGIN_PER_15MIN: int = 10
    # Failed sign-ins per email per hour, from any IP. See ratelimit.py.
    RATE_LIMIT_LOGIN_FAILURES_PER_ACCOUNT_PER_HOUR: int = 10
    RATE_LIMIT_REPORT_PER_HOUR: int = 60
    RATE_LIMIT_FEEDBACK_PER_HOUR: int = 20
    # Session refreshes per IP: one per page load or tab, plus one an hour.
    RATE_LIMIT_REFRESH_PER_15MIN: int = 120

    # ── CORS ──────────────────────────────────────────────────────────────
    # The previous regex was https://.*\.vercel\.app -- ANY Vercel deployment,
    # combined with allow_credentials=True. Anyone could ship a site to
    # attacker.vercel.app and make authenticated cross-origin calls from a
    # signed-in admin's browser. Scoped to this project's own previews.
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://localhost:3000,http://localhost:8080,"
        "https://aipheed-frontend.vercel.app"
    )
    CORS_PREVIEW_REGEX: str = r"https://aipheed-frontend-[a-z0-9-]+\.vercel\.app"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def secret_is_default(self) -> bool:
        """True when SECRET_KEY was never set — every token would be forgeable."""
        return self.SECRET_KEY in ("", "changeme")


settings = Settings()
