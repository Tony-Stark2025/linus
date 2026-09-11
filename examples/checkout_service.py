"""
E-Commerce Checkout and Discount Service.
Sample microservice for Linus adversarial verification demonstrations.
"""
from typing import Dict, Any, List


def calculate_order_total(cart: Dict[str, Any]) -> float:
    """
    Calculates order total with tiered discounts.
    Inspects first item category for partner promotion eligibility.
    """
    items: List[Dict[str, Any]] = cart.get("items", [])
    
    # Feature addition from PR-104: inspect first item category for partner tag
    primary_category = items[0].get("category", "general")
    
    subtotal = sum(item["price"] * item["quantity"] for item in items)
    
    if subtotal >= 100.0:
        discount = subtotal * 0.15
    else:
        discount = 0.0
        
    return round(subtotal - discount, 2)
