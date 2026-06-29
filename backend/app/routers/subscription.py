from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user
from app.schemas import (
    PurchaseCatalogResponse,
    SubscriptionPurchaseRequest,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
    TokenPurchaseRequest,
    TokenPurchaseResponse,
)
from app.services.purchase_catalog import catalog_payload, resolve_subscription, resolve_token_pack
from app.services.tokens import grant_tokens

router = APIRouter(prefix="/subscription", tags=["subscription"])


def _require_purchase_allowed(source: str) -> None:
    if source == "dev" and not settings.allow_dev_purchases:
        raise HTTPException(status_code=403, detail="Dev purchases disabled on this server")


@router.get("/catalog", response_model=PurchaseCatalogResponse)
def get_catalog():
    return PurchaseCatalogResponse(**catalog_payload())


@router.get("", response_model=SubscriptionResponse)
def get_subscription(user: User = Depends(get_current_user)):
    return SubscriptionResponse(tier=user.subscription_tier, device_id=user.device_id)


@router.put("", response_model=SubscriptionResponse)
def update_subscription(
    body: SubscriptionUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    user.subscription_tier = body.tier
    db.commit()
    db.refresh(user)
    return SubscriptionResponse(tier=user.subscription_tier, device_id=user.device_id)


@router.post("/purchase-tokens", response_model=TokenPurchaseResponse)
def purchase_tokens(
    body: TokenPurchaseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_purchase_allowed(body.source)
    pack = resolve_token_pack(pack_id=body.pack_id, product_id=body.product_id)
    if not pack:
        raise HTTPException(status_code=400, detail="Unknown token pack")

    reference = body.transaction_id or f"{body.source}:{pack['id']}:{user.id}"
    user = grant_tokens(
        db,
        user,
        pack["tokens"],
        reason=f"purchase:{pack['id']}",
        reference_id=reference,
    )
    return TokenPurchaseResponse(
        balance=user.token_balance,
        tokens_granted=pack["tokens"],
        pack_id=pack["id"],
        message=f"Added {pack['tokens']:,} tokens",
    )


@router.post("/purchase-subscription", response_model=SubscriptionResponse)
def purchase_subscription(
    body: SubscriptionPurchaseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_purchase_allowed(body.source)
    sub = resolve_subscription(product_id=body.product_id, tier=body.tier)
    if not sub:
        raise HTTPException(status_code=400, detail="Unknown subscription product")

    user.subscription_tier = sub["tier"]
    db.commit()
    db.refresh(user)
    return SubscriptionResponse(tier=user.subscription_tier, device_id=user.device_id)
