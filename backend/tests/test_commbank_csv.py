from datetime import date
from app.importers.commbank_csv import compute_dedupe_hash, normalise_merchant, parse_commbank_csv


def test_parse_headerless_and_headered_commbank_csv() -> None:
    headerless = (
        '17/11/2026,"+10.00","Fast Transfer From RUTH RAJEEV to PayID Phone nuggies","+70.36"\n'
        '16/11/2026,"-52.95","CHEMIST WAREHOUSE POINT COOK Card xx0374 Value Date: 14/11/2026","+60.36"\n'
        'bad-date,"-5.00","BROKEN ROW","+55.36"\n'
    )
    res = parse_commbank_csv(headerless)
    assert len(res.rows) == 2
    assert len(res.errors) == 1
    assert res.rows[0].tx_date == date(2026, 11, 17)
    assert res.rows[0].amount_cents == 1000
    assert res.rows[0].balance_cents == 7036
    assert res.rows[1].amount_cents == -5295
    assert res.rows[1].merchant == "CHEMIST WAREHOUSE POINT COOK"

    with_header = "Date,Amount,Description,Balance\n" + headerless
    res_h = parse_commbank_csv(with_header)
    assert len(res_h.rows) == 2
    assert len(res_h.errors) == 1


def test_merchant_normalisation_patterns() -> None:
    assert normalise_merchant("SQ *NO22 CAFE Melbourne Card xx0374") == "NO22 CAFE MELBOURNE"
    assert normalise_merchant("Transfer to xx0464 CommBank app") == "Transfer xx0464"
    assert normalise_merchant("Fast Transfer From - ANNIT THOMAS to PayID Phone flight") == "ANNIT THOMAS"


def test_dedupe_hash_is_deterministic() -> None:
    h1 = compute_dedupe_hash(1, date(2026, 11, 16), -5295, "CHEMIST WAREHOUSE", 6036)
    h2 = compute_dedupe_hash(1, date(2026, 11, 16), -5295, "CHEMIST WAREHOUSE", 6036)
    h3 = compute_dedupe_hash(1, date(2026, 11, 16), -5295, "CHEMIST WAREHOUSE", 1000)
    assert h1 == h2
    assert h1 != h3
