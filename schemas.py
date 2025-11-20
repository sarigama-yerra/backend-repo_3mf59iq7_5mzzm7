"""
Database Schemas for Premium Shoes E‑commerce

Each Pydantic model represents one MongoDB collection. The collection name is the lowercase of the class name.

Use these schemas for validating input coming from the frontend.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, EmailStr

# Core domain models

class Shoeproduct(BaseModel):
    """
    Collection: "shoeproduct"
    Represents a shoe item in the catalogue
    """
    title: str = Field(..., description="Product title")
    brand: Literal["Nike", "Jordan", "Adidas", "Puma", "Gucci", "Reebok", "New Balance", "ASICS", "Other"] = Field(...)
    price: float = Field(..., ge=0)
    colors: List[str] = Field(default_factory=list, description="Available color names")
    sizes: List[int] = Field(default_factory=list, description="Available sizes (EU/US simplified)")
    description: Optional[str] = Field(None)
    images: List[str] = Field(default_factory=list, description="Image URLs (ordered for gallery/360)")
    is_new: bool = Field(default=False)
    is_best_seller: bool = Field(default=False)
    rating: float = Field(default=4.5, ge=0, le=5)
    reviews_count: int = Field(default=0, ge=0)
    # New attributes for richer filtering and merchandising
    gender: Literal["Men", "Women", "Unisex"] = Field(default="Unisex")
    material: Optional[str] = Field(default=None, description="Primary upper material, e.g., Leather, Mesh, Knit")
    popularity: int = Field(default=0, ge=0, description="Derived score for sorting by popularity")

class Orderitem(BaseModel):
    product_id: str
    title: str
    brand: str
    price: float
    size: int
    color: str
    quantity: int = Field(ge=1, default=1)
    thumbnail: Optional[str] = None

class Order(BaseModel):
    """Collection: "order""" 
    items: List[Orderitem]
    subtotal: float = Field(ge=0)
    shipping: float = Field(ge=0, default=0)
    total: float = Field(ge=0)
    customer_name: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    upi_provider: Optional[Literal["PhonePe", "Paytm", "Google Pay"]] = None
    upi_id: Optional[str] = None
    status: Literal["pending", "paid", "failed"] = "pending"

class Contactmessage(BaseModel):
    """Collection: "contactmessage"""
    name: str
    email: EmailStr
    message: str

# Optional: simple Site review (for testimonials on landing page)
class Sitereview(BaseModel):
    """Collection: "sitereview"""
    name: str
    rating: float = Field(ge=0, le=5)
    comment: str
