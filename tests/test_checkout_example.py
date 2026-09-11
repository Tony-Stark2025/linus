import pytest
from examples.checkout_service import calculate_order_total


def test_order_total_with_bulk_discount():
    cart = {
        "items": [
            {"id": "item-1", "price": 60.0, "quantity": 2, "category": "electronics"}
        ]
    }
    # 120 - 15% (18) = 102.0
    assert calculate_order_total(cart) == 102.0


def test_order_total_below_discount_threshold():
    cart = {
        "items": [
            {"id": "item-2", "price": 40.0, "quantity": 1, "category": "books"}
        ]
    }
    assert calculate_order_total(cart) == 40.0
