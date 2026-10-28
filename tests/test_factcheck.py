from qpulse.factcheck import check_summary

FACTS = [
    {"app": None, "status": None, "text": "13,714 reviews across the 4 apps this week."},
    {"app": "bigbasket", "status": "outside", "text": "Action 1, owner Ops: BigBasket availability / stock was 3.2% "
     "this week against a normal 1.6%; outside the expected range of 0.5% to 2.7% (worse than normal)."},
    {"app": "blinkit", "status": "inside", "text": "Blinkit positive reviews was 72.3% against a normal 70.2%; "
     "inside the expected range of 67.9% to 72.5% (normal variation, no action)."},
]


def test_faithful_summary_passes():
    s = ("BigBasket availability / stock was 3.2% against a normal 1.6%, outside its expected range. "
         "Blinkit positive reviews were 72.3%, within the expected range. We read 13,714 reviews.")
    assert check_summary(s, FACTS) == []


def test_invented_number_fails():
    assert check_summary("BigBasket availability rose 2.8%.", FACTS) == ['"2.8" is not in the facts']


def test_number_moved_to_another_app_fails():
    # A real number, wrong app: the old whole-report number check let this through.
    assert len(check_summary("Blinkit availability was 3.2%.", FACTS)) == 1


def test_wrong_range_claim_fails():
    # From the 2026-10-12 draft: an inside-range value described as outside.
    problems = check_summary("Blinkit positive reviews hit 72.3%, outside the expected range.", FACTS)
    assert problems and "outside" in problems[0]


def test_star_names_are_not_numbers():
    assert check_summary("BigBasket's 1-star and 1★ reviews matter; availability was 3.2%.", FACTS) == []
