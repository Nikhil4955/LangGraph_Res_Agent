from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, StateGraph


TERMINATION_SEQUENCE = "TERMINATE"
MAX_ORDER_ATTEMPTS = 3
MAX_SERVE_RETRIES = 3

# The menu keeps the database's three required columns explicit.
MENU = [
	{"dish": "pizza", "price": 12.0, "quantity available": 10},
	{"dish": "burger", "price": 9.0, "quantity available": 8},
	{"dish": "pasta", "price": 11.0, "quantity available": 6},
]


class OrderState(TypedDict, total=False):
	request: str
	dish: str
	quantity: int
	order_attempts: Annotated[int, operator.add]
	serve_retries: Annotated[int, operator.add]
	cook_should_fail: bool
	serve_should_fail: bool
	order_valid: bool
	cook_succeeded: bool
	serve_succeeded: bool
	status: str
	message: str


def _count(state: OrderState, name: Literal["order_attempts", "serve_retries"]) -> int:
	return state.get(name, 0)


def take_order(dish: str, quantity: int) -> bool:
	"""Return whether the requested dish and quantity are available."""
	if quantity <= 0:
		return False
	return any(
		item["dish"].casefold() == dish.casefold()
		and item["quantity available"] >= quantity
		for item in MENU
	)


def cook() -> bool:
	"""Prepare the order; the graph can inject a kitchen failure for testing."""
	return True


def serve() -> bool:
	"""Deliver the order; the graph can inject a delivery failure for testing."""
	return True


def validate_request(state: OrderState) -> dict:
	"""Reject non-order requests before any restaurant tool is called."""
	if _count(state, "order_attempts") >= MAX_ORDER_ATTEMPTS:
		return {
			"status": "terminated",
			"message": "Your maximum order attempts are exhausted.",
		}
	if state.get("dish") and state.get("quantity") is not None:
		return {"status": "order", "message": "Order request accepted."}
	return {
		"status": "terminated",
		"message": f"{TERMINATION_SEQUENCE}: I can only help with restaurant orders.",
	}


def order_node(state: OrderState) -> dict:
	dish = state.get("dish", "")
	quantity = state.get("quantity", 0)
	if take_order(dish, quantity):
		return {"order_valid": True, "message": "Order accepted."}
	attempts = _count(state, "order_attempts")
	if attempts + 1 >= MAX_ORDER_ATTEMPTS:
		return {
			"order_valid": False,
			"order_attempts": 1,
			"status": "terminated",
			"message": (
				"That dish is not available. Your maximum order attempts are "
				"exhausted."
			),
		}
	return {
		"order_valid": False,
		"order_attempts": 1,
		"status": "needs_new_order",
		"message": "That dish is not available. Please select another dish.",
	}


def cook_node(state: OrderState) -> dict:
	succeeded = not state.get("cook_should_fail", False) and cook()
	if succeeded:
		return {"cook_succeeded": True, "message": "Your order is cooking."}
	attempts = _count(state, "order_attempts")
	exhausted = attempts + 1 >= MAX_ORDER_ATTEMPTS
	return {
		"cook_succeeded": False,
		"order_attempts": 1,
		"status": "terminated" if exhausted else "needs_new_order",
		"message": (
			"The kitchen could not prepare that dish. Your maximum order attempts "
			"are exhausted."
			if exhausted
			else "The kitchen had a problem. Please select a different dish."
		),
	}


def serve_node(state: OrderState) -> dict:
	succeeded = not state.get("serve_should_fail", False) and serve()
	if succeeded:
		return {
			"serve_succeeded": True,
			"status": "completed",
			"message": "The serve has been done. Thank you!",
		}

	retries = _count(state, "serve_retries")
	if retries + 1 < MAX_SERVE_RETRIES:
		return {
			"serve_succeeded": False,
			"serve_retries": 1,
			"status": "retry_serving",
			"message": "Serving failed. The kitchen is preparing your order again.",
		}

	return {
		"serve_succeeded": False,
		"serve_retries": 1,
		"order_attempts": 1,
		"status": "needs_new_order",
		"message": "Serving failed three times. Please select a completely new dish.",
	}


def route_request(state: OrderState) -> Literal["order", "end"]:
	return "order" if state.get("status") == "order" else "end"


def route_order(state: OrderState) -> Literal["cook", "end"]:
	return "cook" if state.get("order_valid") else "end"


def route_cook(state: OrderState) -> Literal["serve", "end"]:
	return "serve" if state.get("cook_succeeded") else "end"


def route_serve(state: OrderState) -> Literal["cook", "end"]:
	return "cook" if state.get("status") == "retry_serving" else "end"


builder = StateGraph(OrderState)
builder.add_node("validate_request", validate_request)
builder.add_node("take_order", order_node)
builder.add_node("cook", cook_node)
builder.add_node("serve", serve_node)
builder.set_entry_point("validate_request")
builder.add_conditional_edges(
	"validate_request", route_request, {"order": "take_order", "end": END}
)
builder.add_conditional_edges("take_order", route_order, {"cook": "cook", "end": END})
builder.add_conditional_edges("cook", route_cook, {"serve": "serve", "end": END})
builder.add_conditional_edges("serve", route_serve, {"cook": "cook", "end": END})

graph = builder.compile()


def print_menu() -> None:
	print("\nAvailable menu:")
	print("+------+----------------+---------+-------------------+")
	print("| No.  | Dish           | Price   | Quantity Available |")
	print("+------+----------------+---------+-------------------+")
	for number, item in enumerate(MENU, start=1):
		print(
			f"| {number:<4} | {item['dish'].title():<14} | "
			f"${item['price']:>6.2f} | "
			f"{item['quantity available']:^17} |"
		)
	print("+------+----------------+---------+-------------------+")


if __name__ == "__main__":
	print_menu()
	order_attempts = 0
	while order_attempts < MAX_ORDER_ATTEMPTS:
		print(f"\nOrder attempt {order_attempts + 1} of {MAX_ORDER_ATTEMPTS}")
		choice_text = input("Enter the number of your dish: ").strip()
		try:
			choice = int(choice_text)
		except ValueError:
			order_attempts += 1
			print("Please enter a valid menu number.")
			continue

		if not 1 <= choice <= len(MENU):
			order_attempts += 1
			print("That menu number is not available. Please choose a listed number.")
			continue

		dish = MENU[choice - 1]["dish"]
		quantity_text = input("How many would you like? ").strip()

		try:
			quantity = int(quantity_text)
		except ValueError:
			order_attempts += 1
			print("Please enter the quantity as a whole number.")
			continue

		result = graph.invoke(
			{
				"request": f"{dish} {quantity}",
				"dish": dish,
				"quantity": quantity,
				"order_attempts": order_attempts,
			}
		)
		print(result["message"])
		order_attempts = result.get("order_attempts", order_attempts)

		if result.get("status") == "completed":
			break
		if order_attempts < MAX_ORDER_ATTEMPTS:
			print("Please choose another dish.")
	else:
		print("Your maximum order attempts are exhausted. The process is terminated.")
