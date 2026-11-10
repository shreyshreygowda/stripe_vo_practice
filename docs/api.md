# Clearinghouse sandbox API

Base URL: the value of `CLEARINGHOUSE_BASE_URL`, or `http://127.0.0.1:8765` if that variable is unset.

This is a local mock. It is not the Stripe API. Follow this document when it differs from Stripe's public docs.

Amounts are integers in the currency's minor unit (cents for `usd`). Do not divide by 100.

## Authentication

Send this header on every request:

```
Authorization: Bearer test_sk
```

A missing or wrong key returns 401. Do not retry 401.

## Errors and retries

Error JSON:

```json
{
  "error": {
    "type": "rate_limit_error",
    "message": "too many requests",
    "request_id": "req_2"
  }
}
```

Every response also has a `Request-Id` header. If you abandon a call, print the error `type` and that id to stderr.

| Status | `error.type` | Retry? |
| --- | --- | --- |
| 400 | `invalid_request_error` | No |
| 401 | `authentication_error` | No |
| 404 | `invalid_request_error` | No |
| 408 | `timeout_error` | Yes |
| 409 | `idempotency_error` | No |
| 429 | `rate_limit_error` | Yes. Wait `Retry-After` seconds first. |
| 500 | `api_error` | Yes |

Retry the same request up to 3 times (4 attempts total). This sandbox sends `Retry-After: 0` on 429.

Faults injected by this sandbox, only on `GET /v1/charges`, once per merchant per server process:

- The first request returns **408**.
- The first request that includes `starting_after` returns **429**.

Restarting the server arms both faults again. Other endpoints do not inject faults. A 400 does not consume a fault.

## Pagination

List endpoints accept:

| Query param | Meaning |
| --- | --- |
| `merchant_id` | Required. An unknown merchant is an empty list, not a 404. |
| `limit` | Optional. Default 3. Minimum 1. Maximum 10. |
| `starting_after` | Optional opaque cursor. Pass back `next_cursor` exactly. Do not build a cursor from an object id. |

Response:

```json
{
  "object": "list",
  "data": [],
  "has_more": false,
  "next_cursor": null
}
```

Stop when `has_more` is false, `data` is empty, or `next_cursor` is null. If `next_cursor` is the same cursor you just sent, stop. An unknown cursor is 400 `unknown starting_after cursor`.

## Charges

`GET /v1/charges`

A charge is intended to look like this. The sandbox sometimes breaks that shape.

| Field | Intended type | Notes |
| --- | --- | --- |
| `id` | string | Not unique in this sandbox. |
| `amount` | integer | Minor units, `>= 0`. |
| `currency` | string | Lowercase ISO code, such as `usd`. |
| `status` | string | `settled`, `pending`, or `failed`. |
| `fee` | integer | Minor units, `>= 0`. |
| `memo` | string | Non-empty. |
| `created`, `object`, `metadata`, others | various | Ignore unknown fields. |

What to do with a bad or out-of-scope record is defined in the part spec, not here.

## Invoices

Used in Part 2. `GET /v1/invoices` uses the same pagination, auth, and error rules. It does not inject 408 or 429.

| Field | Intended type | Notes |
| --- | --- | --- |
| `id` | string | |
| `amount` | integer | Minor units, `>= 0`. |
| `currency` | string | Lowercase ISO code. |
| `status` | string | `open`, `paid`, or `void`. |
| `reference` | string | Non-empty. Compared to a charge `memo`. |

## Payouts

Used in Part 3. `POST /v1/payouts`

Header `Idempotency-Key` is required. Reusing a key with the same canonical body returns the original payout with **200**. Reusing it with a different body returns **409** and does not create a second payout. The server treats `charge_ids` as a set, so order alone is not a different body.

```json
{
  "merchant_id": "acct_harbor",
  "currency": "usd",
  "amount": 0,
  "charge_ids": ["ch_1001"]
}
```

`amount` must equal the sum of `amount - fee` for those charges. Only the first valid settled `usd` copy of a charge is eligible. Others produce 400 `unknown or ineligible charge_id: ...`. A wrong total produces 400 `amount does not match net of charge_ids`. Duplicate ids in the array produce 400 `duplicate charge_id`.

Creation returns **201**:

```json
{
  "id": "po_1001",
  "object": "payout",
  "merchant_id": "acct_harbor",
  "currency": "usd",
  "amount": 0,
  "charge_ids": ["ch_1001"],
  "status": "pending"
}
```

The numbers above are the shape, not the dataset.

## Debug log

`GET /_sandbox/requests` returns the requests this process has handled. It is for debugging retries. It resets when the server restarts.

## Try one request

Start `python3 mock_clearinghouse.py`, then:

```bash
curl -sS -D - \
  -H "Authorization: Bearer test_sk" \
  "http://127.0.0.1:8765/v1/charges?merchant_id=acct_harbor&limit=3"
```

Read the status line before the body. The first call for a merchant is a fault described above.
