from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
 
from app.database import Base

 
 
class Category(Base):
    __tablename__ = "categories"
 
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
 
    shops: Mapped[list["Shop"]] = relationship(back_populates="category")
    subcategories: Mapped[list["Subcategory"]] = relationship(back_populates="category")