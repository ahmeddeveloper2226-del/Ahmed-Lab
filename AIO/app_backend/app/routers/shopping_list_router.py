import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user_id, get_db_session
from ..rate_limiter import limiter
from ..schemas.shopping_list_schemas import (
    AddListToCartResult,
    RecipeAddToCartRequest,
    RecipeParseRequest,
    RecipeParseResponse,
    ShoppingListCreate,
    ShoppingListItemCreate,
    ShoppingListItemUpdate,
    ShoppingListResponse,
    ShoppingListSummary,
    ShoppingListUpdate,
)
from ..services import shopping_list_service as service

logger = logging.getLogger("wasla.shopping_lists")

router = APIRouter()


# --- Lists -----------------------------------------------------------------

@router.get("/", response_model=list[ShoppingListSummary])
async def get_my_lists(db: AsyncSession = Depends(get_db_session), uid: str = Depends(get_current_user_id)):
    return await service.list_lists(db, uid)


@router.post("/", response_model=ShoppingListResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_shopping_list(
    request: Request,
    payload: ShoppingListCreate,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    return await service.create_list(db, uid, payload)


@router.get("/{list_id}", response_model=ShoppingListResponse)
async def get_shopping_list(
    list_id: str, db: AsyncSession = Depends(get_db_session), uid: str = Depends(get_current_user_id)
):
    return await service.get_list(db, uid, list_id)


@router.patch("/{list_id}", response_model=ShoppingListResponse)
async def update_shopping_list(
    list_id: str,
    payload: ShoppingListUpdate,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    return await service.update_list(db, uid, list_id, payload)


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shopping_list(
    list_id: str, db: AsyncSession = Depends(get_db_session), uid: str = Depends(get_current_user_id)
):
    await service.delete_list(db, uid, list_id)


# --- Items -------------------------------------------------------------

@router.post("/{list_id}/items", response_model=ShoppingListResponse, status_code=status.HTTP_201_CREATED)
async def add_shopping_list_item(
    list_id: str,
    payload: ShoppingListItemCreate,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    return await service.add_item(db, uid, list_id, payload)


@router.patch("/{list_id}/items/{item_id}", response_model=ShoppingListResponse)
async def update_shopping_list_item(
    list_id: str,
    item_id: str,
    payload: ShoppingListItemUpdate,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    return await service.update_item(db, uid, list_id, item_id, payload)


@router.delete("/{list_id}/items/{item_id}", response_model=ShoppingListResponse)
async def delete_shopping_list_item(
    list_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    return await service.delete_item(db, uid, list_id, item_id)


# --- Share / duplicate / add-to-cart ---------------------------------------

@router.post("/shared/{share_code}/copy", response_model=ShoppingListResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def copy_shared_list(
    request: Request,
    share_code: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    return await service.duplicate_shared_list(db, uid, share_code)


@router.post("/{list_id}/add-to-cart", response_model=AddListToCartResult)
@limiter.limit("15/minute")
async def add_list_to_cart(
    request: Request,
    list_id: str,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    return await service.add_list_to_cart(db, uid, list_id)


# --- AI Recipe Shopping ------------------------------------------------

@router.post("/recipe/parse", response_model=RecipeParseResponse)
@limiter.limit("10/minute")
async def parse_recipe(
    request: Request,
    payload: RecipeParseRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    try:
        ingredients = await service.parse_recipe(db, payload.dish_name, payload.servings)
    except RuntimeError as e:
        logger.error("Recipe shopping misconfigured: %s", e)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "ميزة الوصفات غير متاحة حاليًا.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Recipe parse failed for dish=%r: %s", payload.dish_name, e, exc_info=True)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "تعذر التعرف على مكونات الطبق الآن، حاول مرة أخرى.")

    return RecipeParseResponse(dish_name=payload.dish_name, servings=payload.servings, ingredients=ingredients)


@router.post("/recipe/add-to-cart", response_model=AddListToCartResult)
@limiter.limit("15/minute")
async def add_recipe_to_cart(
    request: Request,
    payload: RecipeAddToCartRequest,
    db: AsyncSession = Depends(get_db_session),
    uid: str = Depends(get_current_user_id),
):
    return await service.add_products_to_cart(db, uid, payload.product_ids)
