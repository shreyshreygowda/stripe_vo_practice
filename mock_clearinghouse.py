#!/usr/bin/env python3
"""Local Clearinghouse sandbox.

Start it, then call the HTTP API described in docs/api.md.
The lists below are the dataset behind that API.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOST = "127.0.0.1"
TOKEN = "Bearer test_sk"
MIN_LIMIT = 1
MAX_LIMIT = 10
DEFAULT_LIMIT = 3

CHARGES = [
    {
        "id": "ch_1001",
        "object": "charge",
        "merchant_id": "acct_harbor",
        "amount": 2500,
        "currency": "usd",
        "status": "settled",
        "fee": 75,
        "memo": "INV-1042",
        "created": 1714521600,
        "metadata": {"source": "pos"},
    },
    {
        "id": "ch_1002",
        "object": "charge",
        "merchant_id": "acct_harbor",
        "amount": 1800,
        "currency": "usd",
        "status": "settled",
        "fee": 54,
        "memo": "INV-1043",
        "created": 1714521900,
    },
    {
        "id": "ch_1003",
        "object": "charge",
        "merchant_id": "acct_harbor",
        "amount": 5000,
        "currency": "usd",
        "status": "pending",
        "fee": 150,
        "memo": "INV-PEND",
        "created": 1714522200,
    },
    {
        "id": "ch_1004",
        "object": "charge",
        "merchant_id": "acct_harbor",
        "amount": 4200,
        "currency": "usd",
        "status": "settled",
        "fee": 126,
        "memo": "INV-1044",
        "created": 1714522500,
    },
    {
        "id": "ch_1005",
        "object": "charge",
        "merchant_id": "acct_harbor",
        "amount": 3000,
        "currency": "eur",
        "status": "settled",
        "fee": 90,
        "memo": "INV-EUR",
        "created": 1714522800,
    },
    {
        "id": "ch_1006",
        "object": "charge",
        "merchant_id": "acct_harbor",
        "currency": "usd",
        "status": "settled",
        "fee": 30,
        "memo": "INV-1046",
        "created": 1714523100,
    },
    {
        "id": "ch_1002",
        "object": "charge",
        "merchant_id": "acct_harbor",
        "amount": 1800,
        "currency": "usd",
        "status": "settled",
        "fee": 54,
        "memo": "INV-1043",
        "created": 1714523400,
    },
    {
        "id": "ch_1007",
        "object": "charge",
        "merchant_id": "acct_harbor",
        "amount": 500,
        "currency": "usd",
        "status": "settled",
        "memo": "INV-1047",
        "created": 1714523700,
    },
    {
        "id": "ch_1010",
        "object": "charge",
        "merchant_id": "acct_harbor",
        "amount": 800,
        "currency": "usd",
        "status": "settled",
        "fee": "20",
        "memo": "INV-BADFEE",
        "created": 1714524000,
    },
    {
        "id": "ch_1008",
        "object": "charge",
        "merchant_id": "acct_harbor",
        "amount": 10000,
        "currency": "usd",
        "status": "settled",
        "fee": 300,
        "memo": "INV-1048",
        "created": 1714524300,
    },
    {
        "id": "ch_1011",
        "object": "charge",
        "merchant_id": "acct_harbor",
        "amount": 7777,
        "currency": "usd",
        "status": "settled",
        "fee": 100,
        "memo": "NOMATCH",
        "created": 1714524600,
    },
    {
        "id": "ch_1009",
        "object": "charge",
        "merchant_id": "acct_harbor",
        "amount": 100,
        "currency": "usd",
        "status": "failed",
        "fee": 3,
        "memo": "INV-FAIL",
        "created": 1714524900,
    },
]

INVOICES = [
    {
        "id": "inv_paid",
        "object": "invoice",
        "merchant_id": "acct_harbor",
        "amount": 2500,
        "currency": "usd",
        "status": "paid",
        "reference": "INV-1042",
    },
    {
        "id": "inv_1042",
        "object": "invoice",
        "merchant_id": "acct_harbor",
        "amount": 2500,
        "currency": "usd",
        "status": "open",
        "reference": "INV-1042",
    },
    {
        "id": "inv_1043",
        "object": "invoice",
        "merchant_id": "acct_harbor",
        "amount": 1800,
        "currency": "usd",
        "status": "open",
        "reference": "INV-1043",
    },
    {
        "id": "inv_4200",
        "object": "invoice",
        "merchant_id": "acct_harbor",
        "amount": 4200,
        "currency": "usd",
        "status": "open",
        "reference": "MISC",
    },
    {
        "id": "inv_bad",
        "object": "invoice",
        "merchant_id": "acct_harbor",
        "currency": "usd",
        "status": "open",
        "reference": "BROKEN",
    },
    {
        "id": "inv_1050",
        "object": "invoice",
        "merchant_id": "acct_harbor",
        "amount": 10040,
        "currency": "usd",
        "status": "open",
        "reference": "MISC-2",
    },
    {
        "id": "inv_7777a",
        "object": "invoice",
        "merchant_id": "acct_harbor",
        "amount": 7777,
        "currency": "usd",
        "status": "open",
        "reference": "AAA",
    },
    {
        "id": "inv_7777b",
        "object": "invoice",
        "merchant_id": "acct_harbor",
        "amount": 7777,
        "currency": "usd",
        "status": "open",
        "reference": "BBB",
    },
    {
        "id": "inv_5000",
        "object": "invoice",
        "merchant_id": "acct_harbor",
        "amount": 5000,
        "currency": "usd",
        "status": "open",
        "reference": "INV-OPEN",
    },
    {
        "id": "inv_other",
        "object": "invoice",
        "merchant_id": "acct_other",
        "amount": 2500,
        "currency": "usd",
        "status": "open",
        "reference": "INV-1042",
    },
]


def usable_charges(merchant_id: str) -> dict[str, dict]:
    """First valid settled-usd charge for each id. Used to check payout math."""
    seen: set[str] = set()
    usable: dict[str, dict] = {}
    for charge in CHARGES:
        if charge.get("merchant_id") != merchant_id:
            continue
        charge_id = charge.get("id")
        if not isinstance(charge_id, str) or charge_id in seen:
            continue
        seen.add(charge_id)
        if _payout_eligible(charge):
            usable[charge_id] = charge
    return usable


def _payout_eligible(charge: dict) -> bool:
    for key in ("id", "amount", "currency", "status", "fee", "memo"):
        if key not in charge or charge[key] in (None, ""):
            return False
    if type(charge["amount"]) is not int or type(charge["fee"]) is not int:
        return False
    if charge["amount"] < 0 or charge["fee"] < 0:
        return False
    return charge["status"] == "settled" and charge["currency"] == "usd"


def _parse_cursor(raw: str | None, size: int) -> int:
    if raw is None or raw == "":
        return 0
    if not raw.startswith("cur_"):
        raise ValueError("unknown starting_after cursor")
    try:
        index = int(raw[4:])
    except ValueError as exc:
        raise ValueError("unknown starting_after cursor") from exc
    if index < 0 or index > size:
        raise ValueError("unknown starting_after cursor")
    return index


def _parse_limit(qs: dict) -> int:
    raw = qs.get("limit", [None])[0]
    if raw is None:
        return DEFAULT_LIMIT
    try:
        limit = int(raw)
    except ValueError as exc:
        raise ValueError("limit must be an integer") from exc
    if limit < MIN_LIMIT or limit > MAX_LIMIT:
        raise ValueError(f"limit must be between {MIN_LIMIT} and {MAX_LIMIT}")
    return limit


def _page(items: list[dict], qs: dict) -> tuple[list[dict], bool, str | None]:
    limit = _parse_limit(qs)
    cursor = qs.get("starting_after", [None])[0]
    start = _parse_cursor(cursor, len(items))
    chunk = items[start : start + limit]
    end = start + len(chunk)
    has_more = end < len(items)
    next_cursor = f"cur_{end}" if has_more else None
    return chunk, has_more, next_cursor


class ClearinghouseServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, address, handler):
        super().__init__(address, handler)
        self.lock = threading.Lock()
        self.did_408: set[str] = set()
        self.did_429: set[str] = set()
        self.log: list[dict] = []
        self.req_num = 0
        self.payouts: dict[str, dict] = {}
        self.payout_seq = 1000


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def _dispatch(self, method: str):
        try:
            with self.server.lock:
                self._route(method)
        except Exception:
            if not getattr(self, "_sent", False):
                self._send(
                    500,
                    {
                        "error": {
                            "type": "api_error",
                            "message": "internal sandbox error",
                            "request_id": self._next_request_id(),
                        }
                    },
                )

    def _route(self, method: str):
        self._sent = False
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)
        if not self._authorized():
            self._error(401, "authentication_error", "invalid API key", path, None)
            return
        if method == "GET" and path == "/v1/charges":
            self._list("charges", path, qs)
            return
        if method == "GET" and path == "/v1/invoices":
            self._list("invoices", path, qs)
            return
        if method == "POST" and path == "/v1/payouts":
            self._create_payout(path)
            return
        if method == "GET" and path == "/_sandbox/requests":
            self._send(200, {"requests": self.server.log}, path, None)
            return
        self._error(404, "invalid_request_error", "no such endpoint", path, None)

    def _authorized(self) -> bool:
        return self.headers.get("Authorization", "").strip() == TOKEN

    def _list(self, kind: str, path: str, qs: dict):
        merchant_id = qs.get("merchant_id", [None])[0]
        if not merchant_id:
            self._error(
                400,
                "invalid_request_error",
                "merchant_id is required",
                path,
                None,
            )
            return
        source = CHARGES if kind == "charges" else INVOICES
        items = [row for row in source if row.get("merchant_id") == merchant_id]
        try:
            cursor = qs.get("starting_after", [None])[0]
            chunk, has_more, next_cursor = _page(items, qs)
        except ValueError as exc:
            self._error(400, "invalid_request_error", str(exc), path, merchant_id)
            return
        if kind == "charges":
            fault = self._charge_fault(merchant_id, cursor)
            if fault is not None:
                status, err_type, message, headers = fault
                self._error(status, err_type, message, path, merchant_id, headers)
                return
        self._send(
            200,
            {
                "object": "list",
                "data": chunk,
                "has_more": has_more,
                "next_cursor": next_cursor,
            },
            path,
            merchant_id,
        )

    def _charge_fault(self, merchant_id: str, cursor: str | None):
        if merchant_id not in self.server.did_408:
            self.server.did_408.add(merchant_id)
            return 408, "timeout_error", "request timed out", None
        if cursor and merchant_id not in self.server.did_429:
            self.server.did_429.add(merchant_id)
            return (
                429,
                "rate_limit_error",
                "too many requests",
                [("Retry-After", "0")],
            )
        return None

    def _create_payout(self, path: str):
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw.decode() or "null")
        except json.JSONDecodeError:
            self._error(400, "invalid_request_error", "invalid JSON body", path, None)
            return
        if not isinstance(body, dict):
            self._error(400, "invalid_request_error", "invalid JSON body", path, None)
            return
        merchant_id = body.get("merchant_id")
        key = self.headers.get("Idempotency-Key", "").strip()
        if not key:
            self._error(
                400,
                "invalid_request_error",
                "Idempotency-Key is required",
                path,
                merchant_id if isinstance(merchant_id, str) else None,
                body=body,
            )
            return
        canonical, error = _canonicalize_payout(body)
        if error is not None:
            self._error(
                400,
                "invalid_request_error",
                error,
                path,
                merchant_id if isinstance(merchant_id, str) else None,
                body=body,
            )
            return
        stored = self.server.payouts.get(key)
        if stored is not None:
            if stored["canonical"] != canonical:
                self._error(
                    409,
                    "idempotency_error",
                    "key reused with a different body",
                    path,
                    canonical["merchant_id"],
                    body=body,
                )
                return
            self._send(200, stored["payout"], path, canonical["merchant_id"], body=body)
            return
        self.server.payout_seq += 1
        payout = {
            "id": f"po_{self.server.payout_seq}",
            "object": "payout",
            "merchant_id": canonical["merchant_id"],
            "currency": canonical["currency"],
            "amount": canonical["amount"],
            "charge_ids": canonical["charge_ids"],
            "status": "pending",
        }
        self.server.payouts[key] = {"canonical": canonical, "payout": payout}
        self._send(201, payout, path, canonical["merchant_id"], body=body)

    def _error(
        self,
        status: int,
        err_type: str,
        message: str,
        path: str,
        merchant_id: str | None,
        extra_headers=None,
        body=None,
    ):
        request_id = self._next_request_id()
        self._send(
            status,
            {
                "error": {
                    "type": err_type,
                    "message": message,
                    "request_id": request_id,
                }
            },
            path,
            merchant_id,
            extra_headers,
            request_id=request_id,
            body=body,
        )

    def _send(
        self,
        status: int,
        payload: dict,
        path: str | None = None,
        merchant_id: str | None = None,
        extra_headers=None,
        request_id: str | None = None,
        body=None,
    ):
        if request_id is None:
            request_id = self._next_request_id()
        encoded = json.dumps(payload).encode()
        self._sent = True
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Request-Id", request_id)
        self.send_header("Connection", "close")
        for name, value in extra_headers or []:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(encoded)
        if path is not None:
            entry = {
                "request_id": request_id,
                "method": self.command,
                "path": path,
                "status": status,
                "merchant_id": merchant_id,
            }
            if body is not None:
                entry["body"] = body
            self.server.log.append(entry)
            print(
                f"{request_id} {status} {self.command} {path} merchant={merchant_id}",
                file=sys.stderr,
                flush=True,
            )

    def _next_request_id(self) -> str:
        self.server.req_num += 1
        return f"req_{self.server.req_num}"


def _canonicalize_payout(body: dict) -> tuple[dict | None, str | None]:
    merchant_id = body.get("merchant_id")
    currency = body.get("currency")
    amount = body.get("amount")
    charge_ids = body.get("charge_ids")
    if not isinstance(merchant_id, str) or not merchant_id:
        return None, "merchant_id is required"
    if currency != "usd":
        return None, "currency must be usd"
    if type(amount) is not int:
        return None, "amount must be an integer"
    if not isinstance(charge_ids, list) or not charge_ids:
        return None, "charge_ids must not be empty"
    if any(type(charge_id) is not str for charge_id in charge_ids):
        return None, "charge_ids must be strings"
    if len(charge_ids) != len(set(charge_ids)):
        return None, "duplicate charge_id"
    usable = usable_charges(merchant_id)
    unknown = [charge_id for charge_id in charge_ids if charge_id not in usable]
    if unknown:
        return None, f"unknown or ineligible charge_id: {unknown[0]}"
    net = sum(usable[charge_id]["amount"] - usable[charge_id]["fee"] for charge_id in charge_ids)
    if amount != net:
        return None, "amount does not match net of charge_ids"
    canonical = {
        "merchant_id": merchant_id,
        "currency": "usd",
        "amount": amount,
        "charge_ids": sorted(charge_ids),
    }
    return canonical, None


def main():
    port = int(os.environ.get("PORT", "8765"))
    server = ClearinghouseServer((HOST, port), Handler)
    print(f"listening {server.server_address[1]}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("stopped", file=sys.stderr)


if __name__ == "__main__":
    main()
