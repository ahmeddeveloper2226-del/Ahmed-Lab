import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.order import Order, OrderStatus
from ..models.review import Review
from ..models.shop import Shop

logger = logging.getLogger("wasla.review_service")


async def _recompute_shop_rating(db: AsyncSession, shop_id: str) -> None:
    """
    Shop.rating has always existed as a plain float column, but nothing
    in the codebase ever wrote to it — there was no review data to
    average. Now that reviews exist, this keeps it as a real, live
    average instead of a stale/manually-set number, called every time a
    review is created for that shop.
    """
    result = await db.execute(select(func.avg(Review.rating)).where(Review.shop_id == shop_id))
    avg_rating = result.scalar()
    shop_result = await db.execute(select(Shop).where(Shop.id == shop_id))
    shop = shop_result.scalar_one_or_none()
    if shop is not None:
        shop.rating = round(float(avg_rating), 2) if avg_rating is not None else 0.0


async def create_review(db: AsyncSession, uid: str, order_id: str, rating: int, comment: str | None) -> Review:
    try:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error("Failed to look up order_id=%s for review: %s", order_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر إرسال التقييم الآن.")

    if order is None or order.user_id != uid:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "الطلب غير موجود.")
    if order.status != OrderStatus.delivered:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "يمكن تقييم الطلبات التي تم توصيلها فقط.")

    try:
        existing = await db.execute(select(Review).where(Review.order_id == order_id))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "تم تقييم هذا الطلب من قبل.")

        review = Review(
            id=str(uuid.uuid4()),
            order_id=order_id,
            shop_id=order.shop_id,
            user_id=uid,
            rating=rating,
            comment=comment,
        )
        db.add(review)
        await _recompute_shop_rating(db, order.shop_id)
        await db.commit()
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to create review for order_id=%s: %s", order_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر إرسال التقييم الآن.")

    await db.refresh(review)
    return review


async def reply_to_review(db: AsyncSession, shop_id: str, review_id: str, reply: str) -> Review:
    try:
        result = await db.execute(select(Review).where(Review.id == review_id))
        review = result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error("Failed to look up review_id=%s: %s", review_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر إرسال الرد الآن.")

    if review is None or review.shop_id != shop_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "التقييم غير موجود.")

    try:
        review.shop_reply = reply
        review.shop_replied_at = datetime.now(timezone.utc)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to save reply for review_id=%s: %s", review_id, e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر إرسال الرد الآن.")

    await db.refresh(review)
    return review
