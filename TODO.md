# PostAgent — Next Steps

## Blocking: demo reliability

- **Handle conflicts in demo**: Alice and Bob register with static handles (`alice`, `bob`) which fail with 409 after the first run. Options:
  - Append a random suffix at registration time (e.g. `alice-a3f9`)
  - Add a `--force` flag that re-registers over an existing handle if the keypair matches
  - Have the demo clean up registrations on exit
  - Add a `DELETE /v1/agents/{handle}` endpoint (authenticated with keypair)

## Blocking: distribution

- **PyPI publish**: Wheel is built (`dist/postagent-0.1.0-py3-none-any.whl`), needs a PyPI API token to upload. Then `pip install postagent` works everywhere. Consider adding PyPI publish to the GitHub Actions release workflow via `pypa/gh-action-pypi-publish`.

## Trust & safety

- **Reserved handles**: Block registration of handles that impersonate real companies/services. Maintain a blocklist (e.g. `google`, `openai`, `anthropic`, `amazon`, `homedepot`, `microsoft`, `apple`, etc.) checked at registration time. Start simple — a hardcoded list in the register endpoint, graduate to a file or config later.
- **Handle format rules**: Enforce lowercase alphanumeric + hyphens, min 3 chars, max 32 chars. No leading/trailing hyphens.
- **Rate limiting on registration**: Prevent handle squatting. Limit registrations per wallet or per IP.
- **Handle expiry / reclaim**: Handles registered but unused (no messages sent/received) for 90+ days could be released. Needs a last_active timestamp.

## Features

- **Agent deregistration**: `DELETE /v1/agents/{handle}` — authenticated, lets agents clean up after themselves. Required for demo reliability and general hygiene.
- **Message persistence / history**: Right now messages are fire-and-forget over MQTT. If the listener isn't running, messages are lost (unless MQTT persistent sessions catch them). Options: store message history server-side (encrypted), or add a `postagent history` command that replays from a local log.
- **Message schemas / types**: Right now payloads are freeform JSON. Consider a `type` field in the envelope (`chat`, `task`, `result`, `error`) so agents can route messages programmatically.
- **Agent card updates**: Currently no way to update capabilities or description after registration. Add `PATCH /v1/agents/{handle}`.
- **Webhook / callback support**: Some agents might want HTTP notifications when a message arrives, in addition to MQTT. Optional webhook URL in the agent card.

## Infrastructure

- **Production MQTT broker**: Currently using `test.mosquitto.org` which is free, public, and has no SLA. Fine for demo, not for production. Options: self-hosted mosquitto on Fly.io, or a managed service (HiveMQ, CloudMQTT, EMQX Cloud).
- **Postgres migration**: API runs SQLite on Fly with a 1GB volume. Works for now but won't scale. `DATABASE_URL` env var is already wired up for asyncpg — just need to provision Fly Postgres and set the var.
- **Monitoring / alerting**: No observability yet. Add structured logging, health check monitoring, and alerts for API errors or MQTT disconnects.

## Developer experience

- **macOS Intel binary**: CI only builds ARM64 for macOS. Add an `macos-13` matrix entry for Intel Macs.
- **Shell completions**: Typer supports `--install-completion`. Document it or auto-install.
- **MCP server**: Wrap the PostAgent client as an MCP tool server so Claude Desktop / other MCP clients can send messages without the CLI.
- **Python client docs**: The `PostAgent` class in `postagent/client/agent.py` is usable as a library but undocumented. Add usage examples for programmatic integration.

## Cleanup

- **Git author**: Commits show `gitzman <gitzman@pop-os.localdomain>`. Set proper `user.name` and `user.email` in the repo config.
- **v0.1.0 release on GitHub**: The manually-uploaded v0.1.0 release only has a Linux binary and predates the CI workflow. Delete it or update it to avoid confusion — v0.2.0 is the real first release.
- **Stale agent registrations**: The prod database has leftover agents from testing (`alice`, `alice-sec`, `inspect-demo`, `tester-demo`). Either add an admin cleanup endpoint or SSH into Fly and wipe the db for a clean start.
