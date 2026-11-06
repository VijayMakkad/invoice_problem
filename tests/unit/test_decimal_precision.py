from decimal import Decimal, ROUND_HALF_UP

def test_no_float_leakage_in_monetary_math():
    # Demonstrating float IEEE-754 binary representation flaw:
    float_sum = 0.1 + 0.2
    assert float_sum != 0.3  # 0.30000000000000004 in float!

    # Demonstrating Decimal precision invariant:
    dec_sum = Decimal("0.10") + Decimal("0.20")
    assert dec_sum == Decimal("0.30")

def test_fractional_tax_rounding_round_half_up():
    # 18% GST on ₹1,000.03 = ₹180.0054 -> rounds to ₹180.01 with ROUND_HALF_UP
    base = Decimal("1000.03")
    tax_rate = Decimal("0.18")
    raw_tax = base * tax_rate
    quantized_tax = raw_tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert quantized_tax == Decimal("180.01")

def test_tolerance_expanded_ceiling_precision():
    qty = Decimal("5.0")
    unit_price = Decimal("1000.00")
    tolerance = Decimal("0.03")
    ceiling = (qty * unit_price * (Decimal("1.0") + tolerance)).quantize(Decimal("0.01"))
    assert ceiling == Decimal("5150.00")

