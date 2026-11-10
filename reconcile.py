#!/usr/bin/env python3
"""Harbor clearinghouse reconciliation.

Spec: docs/part1.md
API:  docs/api.md

Environment:
  CLEARINGHOUSE_BASE_URL   default http://127.0.0.1:8765
"""

import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 reconcile.py <merchant_id>", file=sys.stderr)
        return 2
    merchant_id = sys.argv[1]
    base_url = os.environ.get("CLEARINGHOUSE_BASE_URL", "http://127.0.0.1:8765")
    print(
        f"not implemented: merchant={merchant_id} base_url={base_url}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
