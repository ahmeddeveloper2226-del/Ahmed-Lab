from pydantic import BaseModel


class ProductSearchResult(BaseModel):
    id: str
    shop_id: str
    shop_name: str
    category_id: str
    name: str
    price: float
    stock_quantity: int
    in_stock: bool