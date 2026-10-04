import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def connect():
	if DATABASE_URL is None:
		raise RuntimeError("DATABASE_URL is not set")
	return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def initialize_database():
	with connect() as connection:
		connection.execute(
			"""
			CREATE TABLE IF NOT EXISTS products (
				product_id INTEGER PRIMARY KEY,
				name TEXT NOT NULL
			)
			"""
		)
		connection.execute(
			"""
			INSERT INTO products (product_id, name)
			VALUES (1, 'Product 1')
			ON CONFLICT (product_id) DO NOTHING
			"""
		)
		connection.execute(
			"""
			CREATE TABLE IF NOT EXISTS product_events (
				event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
				product_id INTEGER NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
				event_type TEXT NOT NULL CHECK (event_type IN ('view', 'sale')),
				created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
			)
			"""
		)


def find_product(product_id: int):
	with connect() as connection:
		cursor = connection.execute(
			"SELECT product_id, name FROM products WHERE product_id = %s",
			(product_id,),
		)
		return cursor.fetchone()


def create_product(product_id: int, name: str):
	with connect() as connection:
		cursor = connection.execute(
			"""
			INSERT INTO products (product_id, name)
			VALUES (%s, %s)
			RETURNING product_id, name
			""",
			(product_id, name),
		)
		return cursor.fetchone()


def create_product_event(product_id: int, event_type: str):
	with connect() as connection:
		cursor = connection.execute(
			"""
			INSERT INTO product_events (product_id, event_type)
			SELECT product_id, %s
			FROM products
			WHERE product_id = %s
			RETURNING event_id, product_id, event_type
			""",
			(event_type, product_id),
		)
		return cursor.fetchone()


def get_product_metrics(product_id: int):
	with connect() as connection:
		cursor = connection.execute(
			"""
			SELECT
				COUNT(*) FILTER (WHERE event_type = 'view') AS views,
				COUNT(*) FILTER (WHERE event_type = 'sale') AS sales
			FROM product_events
			WHERE product_id = %s
			""",
			(product_id,),
		)
		return cursor.fetchone()