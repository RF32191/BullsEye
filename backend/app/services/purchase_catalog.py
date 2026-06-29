"""In-app purchase catalog — token packs and subscription tiers."""

TOKEN_PACKS: dict[str, dict] = {
    "pack_2500": {
        "id": "pack_2500",
        "product_id": "Fermoselle.Bullseye.tokens.2500",
        "label": "Starter",
        "tokens": 2500,
        "price_usd": 4.99,
        "subtitle": "~10 AI predictions",
    },
    "pack_10000": {
        "id": "pack_10000",
        "product_id": "Fermoselle.Bullseye.tokens.10000",
        "label": "Power",
        "tokens": 10_000,
        "price_usd": 14.99,
        "subtitle": "~40 AI predictions",
    },
    "pack_50000": {
        "id": "pack_50000",
        "product_id": "Fermoselle.Bullseye.tokens.50000",
        "label": "Whale",
        "tokens": 50_000,
        "price_usd": 49.99,
        "subtitle": "~200 AI predictions",
    },
}

SUBSCRIPTION_PRODUCTS: dict[str, dict] = {
    "pro_monthly": {
        "id": "pro_monthly",
        "product_id": "Fermoselle.Bullseye.pro.monthly",
        "tier": "pro",
        "label": "Pro",
        "price_usd": 9.99,
        "period": "month",
    },
    "elite_monthly": {
        "id": "elite_monthly",
        "product_id": "Fermoselle.Bullseye.elite.monthly",
        "tier": "elite",
        "label": "Elite",
        "price_usd": 19.99,
        "period": "month",
    },
}


def catalog_payload() -> dict:
    return {
        "token_packs": list(TOKEN_PACKS.values()),
        "subscriptions": list(SUBSCRIPTION_PRODUCTS.values()),
    }


def resolve_token_pack(*, pack_id: str | None = None, product_id: str | None = None) -> dict | None:
    if pack_id and pack_id in TOKEN_PACKS:
        return TOKEN_PACKS[pack_id]
    if product_id:
        for pack in TOKEN_PACKS.values():
            if pack["product_id"] == product_id:
                return pack
    return None


def resolve_subscription(*, product_id: str | None = None, tier: str | None = None) -> dict | None:
    if product_id:
        for sub in SUBSCRIPTION_PRODUCTS.values():
            if sub["product_id"] == product_id:
                return sub
    if tier:
        for sub in SUBSCRIPTION_PRODUCTS.values():
            if sub["tier"] == tier:
                return sub
    return None
