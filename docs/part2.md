# Part 2 — Match charges to invoices

Start this after `python3 check.py part1` passes. Keep the Part 1 fields and add the fields below.

Fetch `GET /v1/invoices` for the same merchant with the same pagination rules and `limit=3`.

## Eligible invoices

Walk invoices in API order.

- Dedupe and validate them the same way as charges. Required fields, in check order: `id`, `amount`, `currency`, `status`, `reference`.
- Reason codes use the same `missing_` / `invalid_` spellings. Put those warnings in `invoice_warnings`, not `warnings`.
- After validation, an invoice is eligible only when `status` is `open` and `currency` is `usd`. Paid, void, and other currencies are ignored with no warning.
- Filter first, then match. A paid invoice must not compete with an open one.

## Matching

Walk included charges in the order they were included. An invoice matches at most one charge. For each charge, try these tiers against invoices that are still unmatched. Use a tier only when it yields **exactly one** invoice. Zero matches: fall through. Two or more: do not pick one; fall through, and leave those invoices unmatched so the next tier still sees them.

1. `memo_and_amount`: `invoice.reference == charge.memo` and `invoice.amount == charge.amount`.
2. `exact_amount`: `invoice.amount == charge.amount`.
3. `amount_tolerance`: `abs(invoice.amount - charge.amount) <= 50`.

Compare `charge.amount`, not `amount - fee`.

Ambiguity example, not from this dataset: a charge of amount 10 and two open invoices of amount 10. The memo does not match. Exact amount finds two, so it does not match. Tolerance finds the same two (difference 0), so the charge stays unmatched.

## Added JSON

```json
{
  "matches": [
    {
      "charge_id": "ch_example",
      "invoice_id": "inv_example",
      "rule": "memo_and_amount"
    }
  ],
  "unmatched_charge_ids": [],
  "unmatched_invoice_ids": ["inv_example"],
  "invoice_warnings": [
    {"id": "inv_example", "reason": "missing_amount"}
  ]
}
```

- `matches` follows included-charge order.
- `rule` is `memo_and_amount`, `exact_amount`, or `amount_tolerance`.
- Unmatched id lists are sorted ascending.
- `invoice_warnings` is sorted by `id` the same way as `warnings`.

`python3 check.py part2` checks Part 1 and these fields.
