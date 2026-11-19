from app.models.finance import Category, MerchantRule
from app.services.categoriser import categorise_transaction


def test_rule_priority_and_transfer_detection() -> None:
    groceries = Category(id=1, name="Groceries", group="Essential", is_income=False, is_system=False)
    dining = Category(id=2, name="Restaurants", group="Lifestyle", is_income=False, is_system=False)
    transfer = Category(id=3, name="Internal transfer", group="Transfer", is_income=False, is_system=True)
    uncat = Category(id=4, name="Uncategorised", group="Other", is_income=False, is_system=True)
    cats = {c.id: c for c in [groceries, dining, transfer, uncat]}

    rules = [
        MerchantRule(id=1, pattern="COLES", match_type="contains", category_id=1, priority=100, source="seed", is_active=True),
        MerchantRule(id=2, pattern="COLES 0602 MELBOURNE", match_type="exact", category_id=2, priority=10, source="learned", is_active=True),
    ]

    # Learned rule overrides seeded rule
    r1 = categorise_transaction("COLES 0602 MELBOURNE AU", "COLES 0602 MELBOURNE", -470, rules, 3, 4, cats)
    assert r1.category_id == 2
    assert r1.is_transfer is False

    # Internal CommBank transfer
    r2 = categorise_transaction("Transfer to xx0464 CommBank app", "Transfer xx0464", -8000, rules, 3, 4, cats)
    assert r2.category_id == 3
    assert r2.is_transfer is True

    # Unknown merchant falls back to Uncategorised
    r3 = categorise_transaction("RANDOM CORNER SHOP", "RANDOM CORNER SHOP", -1200, rules, 3, 4, cats)
    assert r3.category_id == 4
    assert r3.category_source == "default"
