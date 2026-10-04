import json
import os
from contextlib import asynccontextmanager
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from psycopg.errors import UniqueViolation
from pydantic import BaseModel

load_dotenv()

try:
	from openai import OpenAI
except ImportError:
	OpenAI = None

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


class AnalyticsQuery(BaseModel):
	question: str


def build_analytics_answer(question: str, summary: dict) -> str:
	q = question.lower()

	if any(keyword in q for keyword in ["overall", "summary", "overview", "performance", "health"]):
		return (
			f"You currently have {summary['total_products']} products in the catalog, "
			f"{summary['total_views']} total views, and {summary['total_sales']} sales. "
			"This suggests the catalog is active, with measurable engagement and sales activity."
		)
	if "sales" in q:
		return f"Sales are currently {summary['total_sales']} across the catalog."
	if "view" in q:
		return f"Product views total {summary['total_views']} across all products."
	if "product" in q or "catalog" in q:
		return f"The catalog currently contains {summary['total_products']} products."
	return (
		f"I can help with product count, views, and sales. Right now the totals are "
		f"{summary['total_products']} products, {summary['total_views']} views, and {summary['total_sales']} sales."
	)


def get_model_answer(question: str, summary: dict) -> str:
	api_key = os.getenv("OPENAI_API_KEY")
	if not api_key or OpenAI is None:
		return build_analytics_answer(question, summary)

	try:
		client = OpenAI(api_key=api_key)
		response = client.chat.completions.create(
			model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
			temperature=0.2,
			messages=[
				{
					"role": "system",
					"content": (
						"You are a concise analytics assistant. Use only the provided summary "
						"data to answer the user's question. If the data is insufficient, "
						"say so briefly and stick to the numbers you have."
					),
				},
				{
					"role": "user",
					"content": f"Question: {question}\nSummary: {json.dumps(summary, separators=(',', ':'))}",
				},
			],
		)
		content = response.choices[0].message.content
		if content:
			return content.strip()
	except Exception:
		pass

	return build_analytics_answer(question, summary)


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


@app.post("/analytics/query")
def analytics_query(payload: AnalyticsQuery):
	summary = get_business_summary()
	answer = get_model_answer(payload.question, summary)
	return {"answer": answer, "summary": summary}


@app.get("/products/{product_id}")
def get_product(product_id: int, include_metrics: bool = False):
	product = find_product(product_id)
	if product is None:
		raise HTTPException(status_code=404, detail="Product not found")
	if include_metrics:
		product["metrics"] = get_product_metrics(product_id)
	return product