from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db_session
from ..rate_limiter import limiter
from ..services.review_service import create_review

router = APIRouter()


class CreateReviewRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = Field(None, max_length=1000)


class ReviewResponse(BaseModel):
    id: str
    order_id: str
    rating: int
    comment: str | None
    shop_reply: str | None

    @classmethod
    def from_review(cls, review) -> "ReviewResponse":
        return cls(
            id=review.id,
            order_id=review.order_id,
            rating=review.rating,
            comment=review.comment,
            shop_reply=review.shop_reply,
        )


@router.post("/orders/{order_id}/review", response_model=ReviewResponse, status_code=201)
@limiter.limit("10/minute")
async def submit_review(
    request: Request,
    order_id: str,
    payload: CreateReviewRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    review = await create_review(db, uid, order_id, payload.rating, payload.comment)
    return ReviewResponse.from_review(review)
