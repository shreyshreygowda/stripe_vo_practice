# Part 3 — Create one idempotent payout

Start this after `python3 check.py part2` passes.

Create one payout for the **matched** charges only. Do not include unmatched charges. The payout amount is the sum of `amount - fee` over the matches, in minor units.

If there are no matches, do not call the API. Set `payout_id` to `null`.

## Request

`POST /v1/payouts` with the body from `docs/api.md`.

`Idempotency-Key` must be stable across runs of the same merchant and the same matched set:

```text
{merchant_id}:{amount}:{charge ids sorted and joined with commas}
```

Example shape, not the dataset: `acct_example:97:ch_a,ch_b`.

Treat both 201 and 200 as success. Copy the payout's `id` into the summary as `payout_id`.

Running the program twice against the same server must return the same `payout_id` and must not create a second payout.

A 400 or 409 is not retryable. Exit non-zero, print the error type and `Request-Id` to stderr, and print no summary.

```json
{
  "payout_id": "po_example"
}
```

`python3 check.py part3` runs your program twice and checks the sandbox log.
