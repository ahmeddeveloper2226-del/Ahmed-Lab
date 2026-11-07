from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True  # allows building this directly from a SQLAlchemy Category object


class CategoryCreateRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=100)


class SubcategoryResponse(BaseModel):
    id: str
    category_id: str
    name: str
    sort_order: int

    class Config:
        from_attributes = True