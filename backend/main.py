"""FastAPI entry point.

Run from the repository root (so the shared ``config`` and
``technical_indicators`` modules are importable):

    uvicorn backend.main:app --reload --port 8000
"""

from dotenv import load_dotenv

load_dotenv()

import os  # noqa: E402

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from .routes import admin, analysis, auth, portfolio  # noqa: E402

# Interactive API docs only in development (or with API_DOCS=1).
_docs = os.getenv("API_DOCS", "0" if os.getenv("VERCEL") else "1") == "1"
app = FastAPI(
    title="Portfolio Dashboard API", version="2.0.0",
    docs_url="/docs" if _docs else None, redoc_url=None, openapi_url="/openapi.json" if _docs else None,
)

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def security(request: Request, call_next):
    # CSRF: the web app sends X-Requested-With on every call. Browsers won't let another
    # site add that header to a cross-origin request without a CORS preflight, which this
    # API never approves, so a forged form post or fetch is rejected here.
    if request.method in _UNSAFE_METHODS and "x-requested-with" not in request.headers:
        return JSONResponse({"detail": "Missing X-Requested-With header"}, status_code=403)
    response = await call_next(request)
    response.headers.setdefault("Cache-Control", "no-store")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    return response


for module in (auth, portfolio, analysis, admin):
    app.include_router(module.router)


@app.get("/api/health")
def health():
    return {"ok": True}
