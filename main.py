from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from psycopg.errors import UniqueViolation
from pydantic import BaseModel

from database import (
	create_product,
	create_product_event,
	find_product,
	get_business_summary,
	get_product_metrics,
	initialize_database,
	list_products,
)


class ProductCreate(BaseModel):
	product_id: int
	name: str


class ProductEventCreate(BaseModel):
	event_type: Literal["view", "sale"]


@asynccontextmanager
async def lifespan(app: FastAPI):
	initialize_database()
	yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://localhost:5173"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.post("/products", status_code=status.HTTP_201_CREATED)
def post_product(product: ProductCreate):
	try:
		return create_product(product.product_id, product.name)
	except UniqueViolation:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="A product with this ID already exists",
		)


@app.post("/products/{product_id}/events", status_code=status.HTTP_201_CREATED)
def post_product_event(product_id: int, event: ProductEventCreate):
	created_event = create_product_event(product_id, event.event_type)
	if created_event is None:
		raise HTTPException(status_code=404, detail="Product not found")
	return created_event


@app.get("/")
def root():
	return {"message": "Hello World"}


@app.get("/products")
def get_products():
	return list_products()


@app.get("/analytics/summary")
def analytics_summary():
	return get_business_summary()


@app.get("/products/{product_id}")
def get_product(product_id: int, include_metrics: bool = False):
	product = find_product(product_id)
	if product is None:
		raise HTTPException(status_code=404, detail="Product not found")
	if include_metrics:
		product["metrics"] = get_product_metrics(product_id)
	return product