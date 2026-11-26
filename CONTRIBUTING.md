# Contributing

Small, evidenced changes are welcome.

1. Open an issue first for anything that changes a hook's behaviour or an environment variable.
2. Every behaviour change needs a test in `tests/`, and the test must fail without the change.
   Show that: revert the fix, run the test, paste the failure in the PR.
3. Run before pushing, without a pipe (a pipe hides the exit code):
   `ruff check . && python3 -m pytest -q tests > /tmp/out.log; echo $?`
4. Keep hooks and tools on the standard library. A new dependency needs a reason in the PR.
5. English only; no product names, hosts, addresses or personal data. CI greps for them.
6. A new rule in the docs comes with the incident that produced it (`docs/INCIDENTS.md`:
   symptom, cause, rule, check). A rule without a scar is an opinion.
7. Do not remove a guard to make a change easier. Propose a configurable variant.

Licence: MIT; contributions are under the same licence.
