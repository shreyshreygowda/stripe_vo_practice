# Harbor clearinghouse — integration practice

Original practice for a Stripe-style **integration** interview. It is not a leaked Stripe question and it is not the Stripe API.

You get a short spec, an unfamiliar HTTP contract, and a messy dataset. The work is to read the contract, get one path working, then handle bad records and failed calls without making a mess.

This session is Part 1. Ask for a hint before looking up the answer.

## Rules

- Edit `reconcile.py`. Add helpers next to it if you want.
- Python 3.10+ and the standard library are enough. `urllib.request` can do the HTTP. Another HTTP library is fine if you already use it.
- Look up library docs as you go.
- Talk through what you are about to do, especially before a retry loop or a new abstraction.
- Finish Part 1 before Part 2, even though the later specs are in the repo. A working summary beats a half-built matcher.
- `mock_clearinghouse.py` contains the dataset. Calling the API is the exercise. Read the server only if you think the sandbox itself is wrong.

## Run

Terminal A:

```bash
python3 mock_clearinghouse.py
```

Terminal B, from this directory:

```bash
python3 reconcile.py acct_harbor
python3 check.py part1
```

The sample request is in `docs/api.md`. Hit that before writing the client.

| Read now | Later |
| --- | --- |
| `docs/part1.md` | `docs/part2.md` after Part 1 passes |
| `docs/api.md` sections through Charges | Invoices, then Payouts |

## Grader

`check.py` tells you which field disagreed and shows **your** value. It hides the expected totals.

```bash
python3 check.py part1
python3 check.py part2
python3 check.py part3
```

`--reveal` prints the expected JSON and ends the puzzle. Prefer a hint over that flag.

## What a good Part 1 looks like

A small client, a separate pass that turns records into totals, and a retry policy that matches the doc. Tests can target the pure pass with fake records so you are not debugging through the network.
