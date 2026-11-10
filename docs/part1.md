# Part 1 — Settled charge summary

Time box about 45 minutes. Finish this before Part 2.

Write `reconcile.py` so this prints one JSON object to stdout:

```bash
python3 reconcile.py acct_harbor
```

Read `CLEARINGHOUSE_BASE_URL` (default `http://127.0.0.1:8765`). The grader starts its own server and sets that variable. Hardcoding port 8765 fails the grader.

Also handle `acct_empty`, which has no charges. Any other merchant id is the same shape as an empty merchant.

## Outcome

Fetch every charge page for the merchant. Build this object. Extra keys are allowed later; these keys are required now. Pretty-printed JSON is fine. Logs go to stderr, not stdout.

```json
{
  "merchant_id": "acct_example",
  "currency": "usd",
  "charge_count": 1,
  "gross": 100,
  "fees": 3,
  "net": 97,
  "warnings": [
    {"id": "ch_example", "reason": "missing_amount"}
  ]
}
```

`acct_example` is not a merchant in the sandbox. The numbers show the shape only.

- `currency` is always `"usd"`.
- `gross` is the sum of included `amount` values.
- `fees` is the sum of included `fee` values.
- `net` is `gross - fees`.
- Keep minor units. Do not convert to dollars.
- `warnings` is sorted by `id` ascending. Use `null` for a missing id and sort those last.

On a merchant with no included charges, the totals are 0 and `warnings` is empty or contains only data-quality warnings.

## Which charges count

Walk records in API order, across pages. Do not sort them first.

1. If `id` was already seen, append `{id, reason: "duplicate_id"}` and ignore the record.
2. If `id` is missing, append `{id: null, reason: "missing_id"}` and ignore the record.
3. Otherwise mark `id` seen, including when the rest of the record is bad.
4. Validate the remaining fields in this order: `amount`, `currency`, `status`, `fee`, `memo`. The first problem wins.

| Problem | Reason |
| --- | --- |
| Field missing, null, or `""` | `missing_<field>` |
| `amount` or `fee` present but not a JSON integer, or `< 0` | `invalid_amount` or `invalid_fee` |
| `currency` present but not a 3-letter lowercase code | `invalid_currency` |
| `status` present but not `settled`, `pending`, or `failed` | `invalid_status` |

A JSON integer means a whole number, not a numeric string. `"20"` is invalid.

5. A valid charge is included only when `status` is `settled` and `currency` is `usd`. Pending, failed, and other currencies are excluded with **no** warning.

Ignore unknown fields.

## Transport

Follow `docs/api.md`. Use `limit=3`. Retry what the contract says to retry. Do not retry 400 or 401.

If retries run out, or the API returns a non-retryable error, exit non-zero, print the error type and `Request-Id` to stderr, and print no summary.

## Done

`python3 check.py part1` passes both merchants. You can explain, from the records you fetched, why each warning is there and why the net is right.

The grader names fields that disagree. It does not print the expected totals unless you pass `--reveal`.
