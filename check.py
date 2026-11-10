#!/usr/bin/env python3
"""Grader for the Harbor practice round.

Prints the fields that disagree and your values.
Expected totals are hidden unless you pass --reveal.

Do not scroll to ANSWER KEY unless you want the solution.
"""

from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOKEN = "Bearer test_sk"


def main(argv: list[str]) -> int:
    reveal = "--reveal" in argv
    args = [arg for arg in argv if arg != "--reveal"]
    part = args[0] if args else "part1"
    if part not in {"part1", "part2", "part3", "all"}:
        print("usage: python3 check.py [part1|part2|part3|all] [--reveal]", file=sys.stderr)
        return 2
    parts = ["part1", "part2", "part3"] if part == "all" else [part]
    failed = False
    for name in parts:
        print(f"Harbor grader — {name}")
        if not reveal:
            print("expected values hidden; pass --reveal to show them")
        ok = run_part(name, reveal)
        failed = failed or not ok
        print()
    return 1 if failed else 0


def run_part(part: str, reveal: bool) -> bool:
    server = Sandbox()
    try:
        server.start()
        if part == "part1":
            return check_summary(server, "part1", reveal)
        if part == "part2":
            return check_summary(server, "part2", reveal)
        return check_part3(server, reveal)
    finally:
        server.stop()


def check_summary(server: Sandbox, part: str, reveal: bool) -> bool:
        empty_ok = grade_merchant(server, part, "acct_empty", EMPTY[part], reveal)
        harbor_ok = grade_merchant(server, part, "acct_harbor", HARBOR[part], reveal)
        if part != "part1":
            return empty_ok and harbor_ok
        if not (empty_ok and harbor_ok) and not statuses(
            server.fetch_log(), "/v1/charges", "acct_harbor"
        ):
            return False
        return empty_ok and harbor_ok and grade_retries(server, reveal)


def grade_merchant(server: Sandbox, part: str, merchant: str, expected: dict, reveal: bool) -> bool:
    result = server.run_reconcile(merchant)
    print(f"== {merchant}")
    if result.timed_out:
        print("  program still running after 30s")
        print("  Retry-After on 429 is 0, so a long sleep is not required")
        return False
    if result.returncode != 0 or result.data is None:
        print(f"  program exited {result.returncode}")
        show_streams(result)
        if "Connection refused" in (result.stderr or "") or "Failed to establish" in (result.stderr or ""):
            print("  read CLEARINGHOUSE_BASE_URL; the grader does not use a server you started yourself")
        return False
    diffs = diff_fields(result.data, expected, reveal)
    if diffs:
        print("  FAIL")
        for line in diffs:
            print(prefix_lines(line, "  "))
        return False
    print("  PASS")
    return True


def grade_retries(server: Sandbox, reveal: bool) -> bool:
    log = server.fetch_log()
    ok = True
    print("== transport")
    harbor = statuses(log, "/v1/charges", "acct_harbor")
    empty = statuses(log, "/v1/charges", "acct_empty")
    if not recovered(harbor, 408) or not recovered(harbor, 429):
        print("  FAIL acct_harbor did not recover from both the 408 and the 429")
        print(f"  charge statuses: {harbor}")
        ok = False
    else:
        print("  PASS acct_harbor recovered from 408 and 429")
    if not recovered(empty, 408):
        print("  FAIL acct_empty did not recover from the 408")
        print(f"  charge statuses: {empty}")
        ok = False
    else:
        print("  PASS acct_empty recovered from 408")
    if reveal and not ok:
        print("  expected harbor statuses to include 408 then a later 200, and 429 then a later 200")
    return ok


def check_part3(server: Sandbox, reveal: bool) -> bool:
    first = grade_merchant(server, "part3", "acct_harbor", HARBOR["part3"], reveal)
    second = server.run_reconcile("acct_harbor")
    print("== acct_harbor second run")
    second_ok = True
    if second.timed_out or second.returncode != 0 or second.data is None:
        print(f"  program exited {second.returncode}")
        show_streams(second)
        second_ok = False
    else:
        diffs = diff_fields(second.data, HARBOR["part3"], reveal)
        if diffs:
            print("  FAIL")
            for line in diffs:
                print(prefix_lines(line, "  "))
            second_ok = False
        elif first and second.data.get("payout_id") != server.first_payout_id:
            print("  FAIL payout_id changed between runs")
            second_ok = False
        else:
            print("  PASS")
    empty_ok = grade_merchant(server, "part3", "acct_empty", EMPTY["part3"], reveal)
    log = server.fetch_log()
    posts = [
        entry
        for entry in log
        if entry["method"] == "POST" and entry["path"] == "/v1/payouts"
    ]
    print("== payout log")
    log_ok = True
    created = [entry for entry in posts if entry["status"] == 201]
    replayed = [entry for entry in posts if entry["status"] == 200]
    if len(created) != 1 or len(replayed) != 1:
        print(f"  FAIL expected one 201 and one 200, saw statuses {[e['status'] for e in posts]}")
        if any(entry["status"] == 409 for entry in posts):
            print("  a 409 means the same Idempotency-Key was sent with a different body")
        if len(created) > 1:
            print("  more than one payout was created; the key was not stable")
        log_ok = False
    else:
        body = created[0].get("body") or {}
        got_ids = body.get("charge_ids")
        got_ids = sorted(got_ids) if isinstance(got_ids, list) else got_ids
        expected_body = {
            "merchant_id": "acct_harbor",
            "currency": "usd",
            "amount": PAYOUT_AMOUNT,
            "charge_ids": PAYOUT_CHARGE_IDS,
        }
        got_body = {
            "merchant_id": body.get("merchant_id"),
            "currency": body.get("currency"),
            "amount": body.get("amount"),
            "charge_ids": got_ids,
        }
        if got_body != expected_body:
            print("  FAIL payout body does not match the matched charges")
            print(prefix_lines("got " + show(got_body), "  "))
            if reveal:
                print(prefix_lines("expected " + show(expected_body), "  "))
            log_ok = False
        else:
            print("  PASS one payout created and replayed")
    empty_posts = [entry for entry in posts if entry.get("merchant_id") == "acct_empty"]
    if empty_posts:
        print("  FAIL acct_empty should not create a payout")
        log_ok = False
    return first and second_ok and empty_ok and log_ok


class RunResult:
    def __init__(self, returncode, data, stdout, stderr, timed_out=False):
        self.returncode = returncode
        self.data = data
        self.stdout = stdout
        self.stderr = stderr
        self.timed_out = timed_out


class Sandbox:
    def __init__(self):
        self.proc = None
        self.port = None
        self.err_path = None
        self.first_payout_id = None

    def start(self):
        handle = tempfile.NamedTemporaryFile(prefix="harbor-", suffix=".log", delete=False)
        self.err_path = handle.name
        handle.close()
        err = open(self.err_path, "w")
        env = os.environ.copy()
        env["PORT"] = "0"
        self.proc = subprocess.Popen(
            [sys.executable, str(ROOT / "mock_clearinghouse.py")],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=err,
            text=True,
        )
        line = ""
        if self.proc.stdout is not None:
            ready, _, _ = select.select([self.proc.stdout], [], [], 5)
            if ready:
                line = self.proc.stdout.readline()
        err.close()
        if self.proc.poll() is not None or not line.startswith("listening "):
            detail = Path(self.err_path).read_text()[-2000:]
            raise SystemExit(f"sandbox failed to start: {line!r} {detail}")
        self.port = int(line.strip().split()[-1])
        self._wait_until_listening()

    def _wait_until_listening(self):
        url = f"http://127.0.0.1:{self.port}/_sandbox/requests"
        for _ in range(50):
            try:
                urllib.request.urlopen(url, timeout=0.2)
                return
            except urllib.error.HTTPError:
                return
            except urllib.error.URLError:
                time.sleep(0.05)
        raise SystemExit("sandbox did not accept connections")

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self.err_path:
            try:
                os.unlink(self.err_path)
            except OSError:
                pass

    def run_reconcile(self, merchant: str) -> RunResult:
        env = os.environ.copy()
        env["CLEARINGHOUSE_BASE_URL"] = f"http://127.0.0.1:{self.port}"
        try:
            completed = subprocess.run(
                [sys.executable, str(ROOT / "reconcile.py"), merchant],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired as exc:
            return RunResult(124, None, exc.stdout or "", exc.stderr or "", timed_out=True)
        data = None
        stripped = completed.stdout.strip()
        if stripped:
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError:
                data = None
        if isinstance(data, dict) and self.first_payout_id is None and data.get("payout_id"):
            self.first_payout_id = data["payout_id"]
        return RunResult(completed.returncode, data, completed.stdout, completed.stderr)

    def fetch_log(self) -> list[dict]:
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/_sandbox/requests",
            headers={"Authorization": TOKEN},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode())
        return payload["requests"]


def statuses(log: list[dict], path: str, merchant: str) -> list[int]:
    return [
        entry["status"]
        for entry in log
        if entry["path"] == path and entry.get("merchant_id") == merchant
    ]


def recovered(status_list: list[int], bad: int) -> bool:
    if bad not in status_list:
        return False
    return 200 in status_list[status_list.index(bad) + 1 :]


def diff_fields(got, expected, reveal: bool) -> list[str]:
    if not isinstance(got, dict):
        return ["stdout must be one JSON object"]
    lines = []
    missing = [key for key in expected if key not in got]
    if missing:
        lines.append("missing keys: " + ", ".join(missing))
    for key, want in expected.items():
        if key not in got or got[key] == want:
            continue
        lines.append(f"{key}: got {show(got[key])}")
        if reveal:
            lines.append(f"{key}: expected {show(want)}")
    return lines


def show(value) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, sort_keys=True)
    return repr(value)


def show_streams(result: RunResult):
    if result.stdout and result.stdout.strip():
        print(prefix_lines("stdout: " + result.stdout.strip()[:1500], "  "))
    if result.stderr and result.stderr.strip():
        print(prefix_lines("stderr: " + result.stderr.strip()[:1500], "  "))


def prefix_lines(text: str, prefix: str) -> str:
    return "\n".join(prefix + line for line in text.splitlines())


# ANSWER KEY. Scrolling into this is the solution.

HARBOR_PART1 = {
    "merchant_id": "acct_harbor",
    "currency": "usd",
    "charge_count": 5,
    "gross": 26277,
    "fees": 655,
    "net": 25622,
    "warnings": [
        {"id": "ch_1002", "reason": "duplicate_id"},
        {"id": "ch_1006", "reason": "missing_amount"},
        {"id": "ch_1007", "reason": "missing_fee"},
        {"id": "ch_1010", "reason": "invalid_fee"},
    ],
}

HARBOR_MATCHES = [
    {"charge_id": "ch_1001", "invoice_id": "inv_1042", "rule": "memo_and_amount"},
    {"charge_id": "ch_1002", "invoice_id": "inv_1043", "rule": "memo_and_amount"},
    {"charge_id": "ch_1004", "invoice_id": "inv_4200", "rule": "exact_amount"},
    {"charge_id": "ch_1008", "invoice_id": "inv_1050", "rule": "amount_tolerance"},
]

PAYOUT_CHARGE_IDS = ["ch_1001", "ch_1002", "ch_1004", "ch_1008"]
PAYOUT_AMOUNT = 17945

HARBOR_PART2 = {
    **HARBOR_PART1,
    "matches": HARBOR_MATCHES,
    "unmatched_charge_ids": ["ch_1011"],
    "unmatched_invoice_ids": ["inv_5000", "inv_7777a", "inv_7777b"],
    "invoice_warnings": [{"id": "inv_bad", "reason": "missing_amount"}],
}

HARBOR_PART3 = {**HARBOR_PART2, "payout_id": "po_1001"}

EMPTY_PART1 = {
    "merchant_id": "acct_empty",
    "currency": "usd",
    "charge_count": 0,
    "gross": 0,
    "fees": 0,
    "net": 0,
    "warnings": [],
}

EMPTY_PART2 = {
    **EMPTY_PART1,
    "matches": [],
    "unmatched_charge_ids": [],
    "unmatched_invoice_ids": [],
    "invoice_warnings": [],
}

EMPTY_PART3 = {**EMPTY_PART2, "payout_id": None}

HARBOR = {"part1": HARBOR_PART1, "part2": HARBOR_PART2, "part3": HARBOR_PART3}
EMPTY = {"part1": EMPTY_PART1, "part2": EMPTY_PART2, "part3": EMPTY_PART3}


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
