from contextlib import asynccontextmanager
import asyncio
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.config import settings
from app.database import SessionLocal, init_db
from app.routers import auth, alerts, asset_markets, category_paper, chat, congress, event_markets, flow, intelligence, paper, portfolio, predictions, stocks, subscription
from app.services.asset_market_predictions import AssetMarketPredictionService
from app.services.predictions import TrackerService

_tracker = TrackerService()
_asset_predictions = AssetMarketPredictionService()


async def _resolution_loop():
    """Check due predictions every 15 minutes (supports 15m/30m/1h horizons)."""
    while True:
        await asyncio.sleep(900)
        db = SessionLocal()
        try:
            count = await _tracker.resolve_due_predictions(db)
            asset_count = await _asset_predictions.resolve_due(db)
            if count or asset_count:
                print(f"[resolve] stocks={count} assets={asset_count}")
        except Exception as exc:
            print(f"[resolve] error: {exc}")
        finally:
            db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    task = asyncio.create_task(_resolution_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Bullseye AI API",
    description="Token-based AI stock predictions with immutable Railway prediction ledger",
    version="1.1.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(stocks.router, prefix="/api/v1")
app.include_router(congress.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(asset_markets.router, prefix="/api/v1")
app.include_router(event_markets.router, prefix="/api/v1")
app.include_router(flow.router, prefix="/api/v1")
app.include_router(intelligence.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(paper.router, prefix="/api/v1")
app.include_router(category_paper.router, prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(subscription.router, prefix="/api/v1")


API_INDEX = {
    "service": "bullseye-api",
    "version": "1.1.0",
    "status": "online",
    "mock_mode": settings.mock_mode,
    "docs": "/docs",
    "health": "/health",
    "endpoints": {
        "auth": "/api/v1/auth/register",
        "tokens": "/api/v1/auth/tokens",
        "predictions": "/api/v1/predictions/analyze",
        "tracker": "/api/v1/predictions/tracker",
        "accuracy_dashboard": "/api/v1/predictions/accuracy-dashboard",
        "chat": "/api/v1/chat/send",
        "stocks": "/api/v1/stocks/search",
        "congress_trades": "/api/v1/congress/trades",
        "flow": "/api/v1/flow/{ticker}",
        "intelligence": "/api/v1/intelligence/macro",
        "insider_trades": "/api/v1/insider/trades",
        "watchlist": "/api/v1/watchlist",
        "paper_portfolio": "/api/v1/paper/portfolio",
        "event_markets": "/api/v1/event-markets/trending",
    },
    "note": "This is the Bullseye AI backend API. Use the iOS app — there is no website here.",
}


@app.get("/")
def root(request: Request):
    if "application/json" in request.headers.get("accept", ""):
        return API_INDEX
    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Bullseye AI API</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0a120a; color: #e8f5e9; margin: 0; padding: 40px 20px; }
    .wrap { max-width: 640px; margin: 0 auto; }
    h1 { color: #39ff14; margin-bottom: 8px; }
    p { color: #a5d6a7; line-height: 1.6; }
    .badge { display: inline-block; background: #1b5e20; color: #39ff14; padding: 4px 10px; border-radius: 999px; font-size: 13px; margin-bottom: 24px; }
    a { color: #69f0ae; }
    ul { padding-left: 20px; }
    li { margin: 8px 0; }
    code { background: #1a2e1a; padding: 2px 6px; border-radius: 4px; font-size: 14px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="badge">API online</div>
    <h1>Bullseye AI API</h1>
    <p>This URL is the <strong>backend server</strong> for the Bullseye AI iOS app — not a website.
       Open the Bullseye app on your iPhone to use predictions, chat, and tracking.</p>
    <p>Useful links:</p>
    <ul>
      <li><a href="/health">/health</a> — server status</li>
      <li><a href="/docs">/docs</a> — interactive API documentation</li>
      <li><a href="/api/v1">/api/v1</a> — API index (JSON)</li>
    </ul>
    <p style="margin-top:32px;font-size:14px;color:#81c784">
      Mock mode: <code>""" + str(settings.mock_mode).lower() + """</code>
    </p>
  </div>
</body>
</html>"""
    return HTMLResponse(html)


@app.get("/api/v1")
def api_v1_index():
    return API_INDEX


@app.get("/health")
def health():
    return {"status": "ok", "mock_mode": settings.mock_mode}


@app.get("/api/v1/ping")
def ping():
    return {"ok": True, "service": "bullseye-api"}
