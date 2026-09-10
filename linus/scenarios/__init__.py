"""
Pre-loaded Enterprise Scenarios for Linus demonstrations and benchmarks.
"""

from typing import Dict, Any


SCENARIO_CHECKOUT_DISCOUNT = {
    "id": "PR-104",
    "title": "feat(pricing): add tiered bulk volume discounts to checkout",
    "author": "@alex-dev",
    "repository": "acme-corp/ecommerce-service",
    "branch": "feature/tiered-discounts",
    "target_file": "checkout_service.py",
    "pr_description": (
        "Implements tiered bulk discount logic: orders over $100 receive a 15% discount. "
        "Also inspects first item category for partner promotion eligibility. "
        "All unit tests are passing!"
    ),
    "source_code": '''"""
E-Commerce Checkout and Discount Service.
"""
from typing import Dict, Any, List

def calculate_order_total(cart: Dict[str, Any]) -> float:
    """Calculates order total with bulk discounts."""
    items: List[Dict[str, Any]] = cart.get("items", [])
    
    # Feature addition from PR: inspect first item category for partner tag
    primary_category = items[0].get("category", "general")
    
    subtotal = sum(item["price"] * item["quantity"] for item in items)
    
    if subtotal >= 100.0:
        discount = subtotal * 0.15
    else:
        discount = 0.0
        
    return round(subtotal - discount, 2)
''',
    "baseline_test_code": '''import pytest
from checkout_service import calculate_order_total

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
''',
    "adversarial_test_code": '''import pytest
from checkout_service import calculate_order_total

def test_empty_cart_boundary_linus():
    """Linus Adversarial Test: Verify empty cart boundary state."""
    empty_cart = {"items": []}
    # Should safely return 0.0, but unpatched code raises IndexError on items[0]
    total = calculate_order_total(empty_cart)
    assert total == 0.0
''',
    "patched_code": '''"""
E-Commerce Checkout and Discount Service.
"""
from typing import Dict, Any, List

def calculate_order_total(cart: Dict[str, Any]) -> float:
    """Calculates order total with bulk discounts."""
    items: List[Dict[str, Any]] = cart.get("items", [])
    
    # Guard against empty cart boundary condition
    if not items:
        return 0.0
        
    primary_category = items[0].get("category", "general")
    
    subtotal = sum(item["price"] * item["quantity"] for item in items)
    
    if subtotal >= 100.0:
        discount = subtotal * 0.15
    else:
        discount = 0.0
        
    return round(subtotal - discount, 2)
''',
    "explanation": "Added guard `if not items: return 0.0` to safely handle empty carts without raising IndexError on items[0].",
}


SCENARIO_GUEST_SUBSCRIPTION = {
    "id": "PR-209",
    "title": "feat(auth): enable guest checkout pricing for anonymous sessions",
    "author": "@sarah-sre",
    "repository": "saas-platform/billing-api",
    "branch": "feature/guest-checkout",
    "target_file": "subscription_billing.py",
    "pr_description": (
        "Permits unauthenticated guest visitors to view discounted rates before signing in. "
        "Pro users still receive their 20% discount. Passes all test suites."
    ),
    "source_code": '''"""
SaaS Subscription Billing Rate Calculator.
"""
from typing import Dict, Any, Optional

def compute_subscription_rate(user: Optional[Dict[str, Any]], base_monthly_fee: float) -> float:
    """Computes monthly subscription rate based on user tier."""
    # Direct tier lookup from PR
    user_tier = user["tier"]
    
    if user_tier == "enterprise":
        return round(base_monthly_fee * 0.70, 2)
    elif user_tier == "pro":
        return round(base_monthly_fee * 0.80, 2)
        
    return round(base_monthly_fee, 2)
''',
    "baseline_test_code": '''import pytest
from subscription_billing import compute_subscription_rate

def test_pro_user_rate():
    user = {"id": "usr-1", "tier": "pro"}
    assert compute_subscription_rate(user, 100.0) == 80.0

def test_enterprise_user_rate():
    user = {"id": "usr-2", "tier": "enterprise"}
    assert compute_subscription_rate(user, 100.0) == 70.0
''',
    "adversarial_test_code": '''import pytest
from subscription_billing import compute_subscription_rate

def test_guest_user_none_boundary_linus():
    """Linus Adversarial Test: Guest user represented by None."""
    # Guest user has user=None; unpatched code raises TypeError: 'NoneType' object is not subscriptable
    rate = compute_subscription_rate(None, 50.0)
    assert rate == 50.0
''',
    "patched_code": '''"""
SaaS Subscription Billing Rate Calculator.
"""
from typing import Dict, Any, Optional

def compute_subscription_rate(user: Optional[Dict[str, Any]], base_monthly_fee: float) -> float:
    """Computes monthly subscription rate based on user tier."""
    if not user:
        return round(base_monthly_fee, 2)
        
    user_tier = user.get("tier", "standard")
    
    if user_tier == "enterprise":
        return round(base_monthly_fee * 0.70, 2)
    elif user_tier == "pro":
        return round(base_monthly_fee * 0.80, 2)
        
    return round(base_monthly_fee, 2)
''',
    "explanation": "Added `if not user: return round(base_monthly_fee, 2)` to safely default guest visitors without raising TypeError.",
}


SCENARIO_FINANCIAL_AOV = {
    "id": "PR-318",
    "title": "feat(analytics): compute daily Average Order Value (AOV)",
    "author": "@david-analytics",
    "repository": "fintech-corp/ledger-metrics",
    "branch": "feature/daily-aov-metric",
    "target_file": "ledger_metrics.py",
    "pr_description": (
        "Calculates Average Order Value metric across regional merchants. "
        "Tested with historical test data."
    ),
    "source_code": '''"""
Financial Ledger & Metric Engine.
"""
from typing import Dict, Any

def compute_average_order_value(total_revenue: float, total_orders: int) -> float:
    """Calculates AOV (revenue / order count)."""
    # Direct division from PR
    aov = total_revenue / total_orders
    return round(aov, 2)
''',
    "baseline_test_code": '''import pytest
from ledger_metrics import compute_average_order_value

def test_aov_calculation():
    assert compute_average_order_value(1000.0, 10) == 100.0
    assert compute_average_order_value(250.0, 5) == 50.0
''',
    "adversarial_test_code": '''import pytest
from ledger_metrics import compute_average_order_value

def test_zero_orders_division_linus():
    """Linus Adversarial Test: New store or zero orders day."""
    # Zero orders should return 0.0, but unpatched code raises ZeroDivisionError
    res = compute_average_order_value(0.0, 0)
    assert res == 0.0
''',
    "patched_code": '''"""
Financial Ledger & Metric Engine.
"""
from typing import Dict, Any

def compute_average_order_value(total_revenue: float, total_orders: int) -> float:
    """Calculates AOV (revenue / order count)."""
    if total_orders <= 0:
        return 0.0
    aov = total_revenue / total_orders
    return round(aov, 2)
''',
    "explanation": "Added guard `if total_orders <= 0: return 0.0` to eliminate ZeroDivisionError on empty trading periods.",
}


SCENARIO_SOUND_PAYMENT_GATEWAY = {
    "id": "PR-401",
    "title": "feat(payments): resilient payment intent processor with defensive null guards",
    "author": "@marcus-core",
    "repository": "fintech-corp/payments-core",
    "branch": "feature/resilient-payment-intent",
    "target_file": "payment_processor.py",
    "pr_description": (
        "Implements payment intent processing with defensive guards for null accounts, "
        "empty metadata, and zero amounts. Thoroughly guarded against edge-case crashes."
    ),
    "source_code": '''"""
Resilient Payment Intent Processor.
"""
from typing import Dict, Any, Optional

def process_payment_intent(account: Optional[Dict[str, Any]], amount_cents: int) -> Dict[str, Any]:
    """Processes payment intent safely with defensive checks."""
    if not account:
        return {"status": "REJECTED", "reason": "ACCOUNT_MISSING", "fee": 0.0}
        
    if amount_cents <= 0:
        return {"status": "REJECTED", "reason": "INVALID_AMOUNT", "fee": 0.0}

    tier = account.get("tier", "standard")
    fee_rate = 0.025 if tier == "pro" else 0.035
    fee = round((amount_cents / 100.0) * fee_rate, 2)

    return {
        "status": "APPROVED",
        "account_id": account.get("id", "unknown"),
        "amount_cents": amount_cents,
        "fee": fee,
    }
''',
    "baseline_test_code": '''import pytest
from payment_processor import process_payment_intent

def test_standard_payment():
    account = {"id": "acc-1", "tier": "standard"}
    res = process_payment_intent(account, 10000)
    assert res["status"] == "APPROVED"
    assert res["fee"] == 3.50

def test_pro_payment():
    account = {"id": "acc-2", "tier": "pro"}
    res = process_payment_intent(account, 10000)
    assert res["status"] == "APPROVED"
    assert res["fee"] == 2.50
''',
    "adversarial_test_code": '''import pytest
from payment_processor import process_payment_intent

def test_null_account_and_zero_amount_linus():
    """Linus Adversarial Test: Boundary conditions for null account and zero amount."""
    # Both boundary conditions should be handled cleanly with zero unhandled exceptions
    res1 = process_payment_intent(None, 5000)
    assert res1["status"] == "REJECTED"
    
    res2 = process_payment_intent({"id": "acc-1"}, 0)
    assert res2["status"] == "REJECTED"
''',
    "patched_code": None,
    "explanation": "Code is already defensively guarded against boundary states. Zero defects proven; Linus remains ambient and silent.",
}


ALL_SCENARIOS = {
    "PR-104": SCENARIO_CHECKOUT_DISCOUNT,
    "PR-209": SCENARIO_GUEST_SUBSCRIPTION,
    "PR-318": SCENARIO_FINANCIAL_AOV,
    "PR-401": SCENARIO_SOUND_PAYMENT_GATEWAY,
}
