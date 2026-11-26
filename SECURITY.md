# Security

## Scope

This kit starts coding agents with permission prompts disabled and guards them with hooks.
Treat it as a seat belt against honest mistakes, not as a sandbox.

- The Bash guard is a pattern match. A worker that deliberately builds a command around it
  will get through. Run workers under a low-privilege account, with a token that cannot merge
  or push to protected branches, on a machine without production credentials.
- Never put an API key in a worker's environment; the launcher unsets it so runs use the
  login session.
- Briefs and logs may contain what the worker saw. Do not publish them without reading them.

## Reporting a vulnerability

Please open a private security advisory on the GitHub repository (Security tab, "Report a
vulnerability"). Do not file a public issue for a bypass of a guard that exposes real users.
Expect an acknowledgement within a week. Bypasses of the regex guard that need deliberate
obfuscation are known and documented above; reports of accidental bypasses (a common command
that should be blocked and is not) are welcome as ordinary issues with a failing test.

## Supported versions

The latest tagged release.
