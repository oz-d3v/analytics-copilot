import unittest

from fastapi.testclient import TestClient

from database import connect
from main import app


class ProductEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()
        self.addCleanup(self.client_context.__exit__, None, None, None)
        self.created_product_id = 762520
        self.delete_created_product()
        self.addCleanup(self.delete_created_product)

    def delete_created_product(self):
        with connect() as connection:
            connection.execute(
                "DELETE FROM product_events WHERE product_id IN (%s, %s)",
                (self.created_product_id, self.created_product_id + 1),
            )
            connection.execute(
                "DELETE FROM products WHERE product_id IN (%s, %s)",
                (self.created_product_id, self.created_product_id + 1),
            )

    def test_creates_product_and_returns_it(self):
        product = {"product_id": self.created_product_id, "name": "New Product"}

        response = self.client.post("/products", json=product)
        retrieved = self.client.get(f"/products/{self.created_product_id}")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), product)
        self.assertEqual(retrieved.status_code, 200)
        self.assertEqual(retrieved.json(), product)

    def test_returns_409_for_duplicate_product_id(self):
        response = self.client.post(
            "/products",
            json={"product_id": 1, "name": "Duplicate Product"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(),
            {"detail": "A product with this ID already exists"},
        )

    def test_returns_known_product(self):
        response = self.client.get("/products/1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"product_id": 1, "name": "Product 1"})

    def test_returns_404_for_unknown_product(self):
        response = self.client.get("/products/999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Product not found"})

    def test_includes_metrics_when_requested(self):
        response = self.client.get("/products/1?include_metrics=true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "product_id": 1,
                "name": "Product 1",
                "metrics": {"views": 0, "sales": 0},
            },
        )

    def test_returns_business_summary(self):
        product = {"product_id": self.created_product_id, "name": "Summary Product"}
        self.client.post("/products", json=product)
        self.client.post(f"/products/{self.created_product_id}/events", json={"event_type": "view"})
        self.client.post(f"/products/{self.created_product_id}/events", json={"event_type": "sale"})

        response = self.client.get("/analytics/summary")
        summary = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(summary["total_products"], 2)
        self.assertGreaterEqual(summary["total_views"], 1)
        self.assertGreaterEqual(summary["total_sales"], 1)

    def test_analytics_query_returns_answer(self):
        response = self.client.post(
            "/analytics/query",
            json={"question": "Give me an overall summary of product performance"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("answer", response.json())
        self.assertIn("total_products", response.json()["summary"])

    def test_analytics_query_answers_specific_product_questions(self):
        product = {"product_id": self.created_product_id, "name": "Performance Product"}
        self.client.post("/products", json=product)
        self.client.post(f"/products/{self.created_product_id}/events", json={"event_type": "view"})
        self.client.post(f"/products/{self.created_product_id}/events", json={"event_type": "sale"})

        response = self.client.post(
            "/analytics/query",
            json={"question": f"How is product {self.created_product_id} performing?"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("performing", response.json()["answer"].lower())
        self.assertIn("view", response.json()["answer"].lower())
        self.assertIn("sale", response.json()["answer"].lower())

    def test_analytics_query_finds_best_performing_product(self):
        first = {"product_id": self.created_product_id, "name": "Best Product"}
        second = {"product_id": self.created_product_id + 1, "name": "Runner Up"}
        self.client.post("/products", json=first)
        self.client.post("/products", json=second)
        self.client.post(f"/products/{self.created_product_id}/events", json={"event_type": "sale"})
        self.client.post(f"/products/{self.created_product_id}/events", json={"event_type": "sale"})
        self.client.post(f"/products/{self.created_product_id + 1}/events", json={"event_type": "sale"})

        response = self.client.post(
            "/analytics/query",
            json={"question": "Which product has the most sales?"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Best Product", response.json()["answer"])
        self.assertIn("2 sales", response.json()["answer"])

    def test_recorded_events_update_product_metrics(self):
        product = {"product_id": self.created_product_id, "name": "Event Product"}
        self.client.post("/products", json=product)

        first_view = self.client.post(
            f"/products/{self.created_product_id}/events",
            json={"event_type": "view"},
        )
        second_view = self.client.post(
            f"/products/{self.created_product_id}/events",
            json={"event_type": "view"},
        )
        sale = self.client.post(
            f"/products/{self.created_product_id}/events",
            json={"event_type": "sale"},
        )
        metrics = self.client.get(
            f"/products/{self.created_product_id}?include_metrics=true"
        )

        self.assertEqual(first_view.status_code, 201)
        self.assertEqual(second_view.status_code, 201)
        self.assertEqual(sale.status_code, 201)
        self.assertEqual(
            metrics.json()["metrics"],
            {"views": 2, "sales": 1},
        )

    def test_rejects_events_for_unknown_products(self):
        response = self.client.post(
            "/products/999/events",
            json={"event_type": "view"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Product not found"})

    def test_rejects_unsupported_event_types(self):
        response = self.client.post(
            "/products/1/events",
            json={"event_type": "refund"},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()