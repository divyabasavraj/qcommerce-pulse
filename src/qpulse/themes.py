"""Theme taxonomy v1 (PLAN.md section 6). A review can carry several themes."""

THEMES = {
    "delivery_delay": "Delivery took longer than promised, late or very slow delivery, order stuck or never arrived",
    "missing_wrong_item": "Item missing from the order, wrong item / brand / size / quantity delivered",
    "quality_expiry": "Rotten, damaged, stale, leaking or expired products; poor product quality",
    "refund_support": "Refund not received or delayed, return refused, customer support / chatbot unhelpful or unreachable",
    "pricing_fees": "Delivery / handling / surge / platform / small-cart fees, prices higher than market or MRP, overcharging, coupons not working",
    "app_payment_bug": "App crashes, login/OTP problems, app slow or buggy, payment failed or money debited without order",
    "partner_behaviour": "Delivery partner rude, asked for extra money or tip, didn't come to the door, fake 'delivered' status",
    "availability_stock": "Items out of stock, service unavailable at the address, store closed, limited selection",
    "positive": "Praise: fast delivery, good service, good offers, love the app",
    "other": "Anything else, including reviews too vague to classify (e.g. 'bad', 'ok', emojis only)",
}

THEME_KEYS = list(THEMES)
