import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Shoeproduct, Order, Contactmessage, Sitereview

app = FastAPI(title="Premium Shoes API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers

def to_str_id(doc: dict):
    if not doc:
        return doc
    doc = dict(doc)
    if doc.get("_id"):
        doc["id"] = str(doc.pop("_id"))
    # Convert datetime objects to isoformat
    for k, v in list(doc.items()):
        try:
            from datetime import datetime
            if isinstance(v, datetime):
                doc[k] = v.isoformat()
        except Exception:
            pass
    return doc

# Root & health
@app.get("/")
def read_root():
    return {"message": "Premium Shoes Backend Running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["connection_status"] = "Connected"
            response["collections"] = db.list_collection_names()
            response["database"] = "✅ Connected & Working"
        else:
            response["database"] = "❌ Database not initialized"
    except Exception as e:
        response["database"] = f"⚠️ {str(e)[:80]}"
    return response

# Product Endpoints
@app.get("/api/products")
def list_products(
    brand: Optional[str] = None,
    size: Optional[int] = None,
    min_price: Optional[float] = Query(None, alias="minPrice"),
    max_price: Optional[float] = Query(None, alias="maxPrice"),
    color: Optional[str] = None,
    is_new: Optional[bool] = Query(None, alias="new"),
    best: Optional[bool] = Query(None, alias="best"),
    limit: int = 60
):
    q = {}
    if brand:
        q["brand"] = brand
    if size is not None:
        q["sizes"] = {"$in": [size]}
    if color:
        q["colors"] = {"$in": [color]}
    if min_price is not None or max_price is not None:
        price_q = {}
        if min_price is not None:
            price_q["$gte"] = min_price
        if max_price is not None:
            price_q["$lte"] = max_price
        q["price"] = price_q
    if is_new is not None:
        q["is_new"] = is_new
    if best is not None:
        q["is_best_seller"] = best

    docs = get_documents("shoeproduct", q, limit)
    return [to_str_id(d) for d in docs]

@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    try:
        doc = db["shoeproduct"].find_one({"_id": ObjectId(product_id)})
    except Exception:
        doc = None
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return to_str_id(doc)

# Reviews (testimonials)
@app.get("/api/reviews")
def get_reviews(limit: int = 10):
    docs = get_documents("sitereview", {}, limit)
    return [to_str_id(d) for d in docs]

# Contact messages
@app.post("/api/contact")
def create_contact(msg: Contactmessage):
    inserted_id = create_document("contactmessage", msg)
    return {"id": inserted_id, "status": "received"}

# Orders
@app.post("/api/orders")
def create_order(order: Order):
    # Basic recompute of totals for safety
    subtotal = sum(i.price * i.quantity for i in order.items)
    total = subtotal + order.shipping
    order.subtotal = round(subtotal, 2)
    order.total = round(total, 2)
    order_id = create_document("order", order)
    # Simulate UPI intent link (mock)
    upi_provider = order.upi_provider or "PhonePe"
    upi_link = f"upi://pay?pn=PremiumShoes&am={order.total}&cu=INR&pa=premium@upi&tn=Order%20{order_id}"
    return {"id": order_id, "status": "pending", "upi_provider": upi_provider, "upi_link": upi_link}

# Seed initial products and testimonials (idempotent-ish)
class SeedResponse(BaseModel):
    products: int
    reviews: int

@app.post("/api/seed", response_model=SeedResponse)
def seed_data():
    brands = ["Nike", "Jordan", "Adidas", "Puma", "Gucci"]
    count_products = db["shoeproduct"].count_documents({}) if db else 0
    added_p = 0
    if count_products == 0:
        sample_products: List[Shoeproduct] = []
        base_imgs = {
            "Nike": [
                "https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=1200&auto=format&fit=crop",
            ],
            "Jordan": [
                "https://images.unsplash.com/photo-1519741497674-611481863552?q=80&w=1200&auto=format&fit=crop",
            ],
            "Adidas": [
                "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?q=80&w=1200&auto=format&fit=crop",
            ],
            "Puma": [
                "https://images.unsplash.com/photo-1542291026-787b19a2f5b6?q=80&w=1200&auto=format&fit=crop",
            ],
            "Gucci": [
                "https://images.unsplash.com/photo-1584735175315-9d5df6c7e8a0?q=80&w=1200&auto=format&fit=crop",
            ],
        }
        for b in brands:
            for idx in range(1, 7):
                p = Shoeproduct(
                    title=f"{b} Elite {idx}",
                    brand=b,
                    price=round(99 + idx * 20 + (0 if b != "Gucci" else 300), 2),
                    colors=["Black", "White", "Red", "Blue"][0:3],
                    sizes=[38, 39, 40, 41, 42, 43, 44],
                    description=f"Premium {b} sneaker crafted for comfort and performance.",
                    images=base_imgs[b],
                    is_new=idx >= 5,
                    is_best_seller=idx % 2 == 0,
                    rating=4.5,
                    reviews_count=120 + idx,
                )
                create_document("shoeproduct", p)
                added_p += 1
    # Seed testimonials
    count_reviews = db["sitereview"].count_documents({}) if db else 0
    added_r = 0
    if count_reviews == 0:
        reviews = [
            Sitereview(name="Aarav", rating=5, comment="Top-notch quality and super fast delivery!"),
            Sitereview(name="Isha", rating=4.5, comment="Loved the comfort. The packaging felt premium."),
            Sitereview(name="Kabir", rating=4.8, comment="Great prices for authentic sneakers."),
        ]
        for r in reviews:
            create_document("sitereview", r)
            added_r += 1
    return SeedResponse(products=added_p, reviews=added_r)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
