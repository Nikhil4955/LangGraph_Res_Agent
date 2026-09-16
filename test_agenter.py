import unittest

from agenter import MAX_ORDER_ATTEMPTS, MAX_SERVE_RETRIES, graph


class RestaurantOrderWorkflowTests(unittest.TestCase):
    def test_01_human_query_is_rejected(self):
        result = graph.invoke({"request": "What is the weather today?"})

        self.assertEqual(result["status"], "terminated")
        self.assertTrue(result["message"].startswith("TERMINATE"))

    def test_02_llm_rejects_input_without_structured_order(self):
        result = graph.invoke({"request": "I would like something to eat"})

        self.assertEqual(result["status"], "terminated")
        self.assertIn("only help with restaurant orders", result["message"])

    def test_03_failed_take_order_allows_another_order(self):
        failed_order = graph.invoke(
            {
                "dish": "sushi",
                "quantity": 1,
                "order_attempts": 0,
                "serve_retries": 0,
            }
        )

        self.assertEqual(failed_order["status"], "needs_new_order")
        self.assertEqual(failed_order["order_attempts"], 1)

        successful_order = graph.invoke(
            {
                "dish": "pizza",
                "quantity": 1,
                "order_attempts": failed_order["order_attempts"],
                "serve_retries": 0,
            }
        )

        self.assertEqual(successful_order["status"], "completed")
        self.assertEqual(successful_order["message"], "The serve has been done. Thank you!")

    def test_04_cook_failure_counts_as_order_attempt(self):
        result = graph.invoke(
            {
                "dish": "pizza",
                "quantity": 1,
                "cook_should_fail": True,
                "order_attempts": 0,
                "serve_retries": 0,
            }
        )

        self.assertEqual(result["status"], "needs_new_order")
        self.assertEqual(result["order_attempts"], 1)
        self.assertIn("kitchen", result["message"])

    def test_05_serve_failure_retries_then_requests_new_order(self):
        result = graph.invoke(
            {
                "dish": "pizza",
                "quantity": 1,
                "serve_should_fail": True,
                "order_attempts": 0,
                "serve_retries": 0,
            }
        )

        self.assertEqual(result["status"], "needs_new_order")
        self.assertEqual(result["serve_retries"], MAX_SERVE_RETRIES)
        self.assertEqual(result["order_attempts"], 1)
        self.assertIn("three times", result["message"])


if __name__ == "__main__":
    unittest.main()
