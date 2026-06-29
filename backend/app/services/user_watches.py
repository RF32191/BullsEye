"""Persist politician / whale / flow alert watches on user preferences."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import User


class UserWatchesService:
    def get(self, user: User) -> dict:
        prefs = user.preferences or {}
        return {
            "politician_slugs": prefs.get("politician_slugs", []),
            "whale_wallets": prefs.get("whale_wallets", []),
            "flow_tickers": prefs.get("flow_tickers", []),
            "flow_score_push_threshold": prefs.get("flow_score_push_threshold", 62),
            "flow_score_pull_threshold": prefs.get("flow_score_pull_threshold", 38),
            "congress_net_min_usd": prefs.get("congress_net_min_usd", 50_000),
        }

    def update(self, db: Session, user: User, payload: dict) -> dict:
        prefs = dict(user.preferences or {})
        for key in (
            "politician_slugs",
            "whale_wallets",
            "flow_tickers",
            "flow_score_push_threshold",
            "flow_score_pull_threshold",
            "congress_net_min_usd",
        ):
            if key in payload and payload[key] is not None:
                prefs[key] = payload[key]
        user.preferences = prefs
        db.commit()
        db.refresh(user)
        return self.get(user)
