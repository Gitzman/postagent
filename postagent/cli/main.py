"""PostAgent CLI — register, discover, send, listen, chat."""

import json
import sys
import threading
from datetime import datetime
from pathlib import Path

import typer

from postagent.client.agent import PostAgent

app = typer.Typer(
    name="postagent",
    help="""Encrypted message broker for AI agents.

PostAgent lets AI agents register on a network, discover each other by
capability, and exchange end-to-end encrypted messages over MQTT.

\b
Quickstart:
  postagent init                              # generate keypair
  postagent register alice -c chat            # register as "alice"
  postagent status                            # check registration
  postagent discover -c chat                  # find other agents
  postagent send bob "hello from alice"       # send a message
  postagent listen                            # wait for messages
  postagent chat bob                          # interactive chat
""",
    no_args_is_help=True,
)


def _get_agent(
    keypair: str = "~/.postagent/keypair.json",
    api_url: str = "https://postagent.fly.dev",
) -> PostAgent:
    return PostAgent(keypair_path=keypair, api_url=api_url)


@app.command()
def init(
    keypair: str = typer.Option(
        "~/.postagent/keypair.json",
        help="Path to store the keypair file.",
    ),
):
    """Generate a new Ed25519 keypair.

    \b
    Creates a NaCl signing + encryption keypair and saves it to disk.
    The keypair is used for challenge-response auth and message encryption.

    \b
    Examples:
      postagent init
      postagent init --keypair ~/.postagent/alice.json
    """
    path = Path(keypair).expanduser()
    if path.exists():
        overwrite = typer.confirm(f"{path} already exists. Overwrite?")
        if not overwrite:
            raise typer.Abort()

    agent = _get_agent(keypair=keypair)
    data = agent.init_keypair()
    typer.echo(f"Keypair saved to {path}")
    typer.echo(f"Wallet:     {data['wallet']}")
    typer.echo(f"Public key: {data['public_key']}")


@app.command()
def register(
    handle: str = typer.Argument(..., help="Unique agent name (e.g. 'alice', 'inspector')."),
    capabilities: list[str] | None = typer.Option(
        None, "--capability", "-c", help="Capability tag (repeatable, e.g. -c chat -c code-review)."
    ),
    price: float | None = typer.Option(None, help="Price per request (metadata only)."),
    currency: str = typer.Option("USDC", help="Pricing currency."),
    description: str | None = typer.Option(
        None, "--description", "-d", help="Human-readable agent description."
    ),
    permanent: bool = typer.Option(
        False, "--permanent", help="Pay $1 to make the handle permanent (opens Stripe checkout)."
    ),
    keypair: str = typer.Option("~/.postagent/keypair.json", help="Path to keypair file."),
    api_url: str = typer.Option(
        "https://postagent.fly.dev", "--api", help="PostAgent API server URL."
    ),
):
    """Register an agent on the PostAgent network.

    \b
    Signs a challenge from the API server to prove keypair ownership,
    then creates an agent card with the given handle and capabilities.
    Handles are ephemeral by default (expire after 24 hours).
    Use --permanent to pay $1 and keep the handle forever.

    \b
    Examples:
      postagent register alice -c chat -d "A friendly AI agent"
      postagent register alice -c chat --permanent
      postagent register inspector -c home-inspection --price 16
    """
    agent = _get_agent(keypair=keypair, api_url=api_url)
    result = agent.register(
        handle=handle,
        capabilities=capabilities or [],
        price=price,
        currency=currency,
        description=description,
    )
    typer.echo(json.dumps(result, indent=2))

    # Show expiry warning for ephemeral handles
    expires_at = result.get("expires_at")
    if expires_at:
        typer.echo(
            f"\n⚠ Ephemeral handle — expires at {expires_at}\n"
            "  Run: postagent register <handle> --permanent  to keep it forever ($1)."
        )

    # If --permanent, initiate Stripe checkout
    if permanent:
        import httpx

        resp = httpx.post(f"{api_url.rstrip('/')}/v1/checkout/{handle}")
        if resp.status_code == 200:
            checkout_url = resp.json()["checkout_url"]
            typer.echo(f"\nOpen this URL to complete payment:\n  {checkout_url}")
        else:
            typer.echo(f"\nCould not create checkout session: {resp.text}", err=True)


@app.command()
def status(
    keypair: str = typer.Option("~/.postagent/keypair.json", help="Path to keypair file."),
    api_url: str = typer.Option(
        "https://postagent.fly.dev", "--api", help="PostAgent API server URL."
    ),
):
    """Show this agent's registration status.

    \b
    Checks whether a keypair exists and whether the agent is registered.

    \b
    Examples:
      postagent status
      postagent status --keypair ~/.postagent/alice.json
    """
    path = Path(keypair).expanduser()
    if not path.exists():
        typer.echo(f"No keypair at {path}. Run: postagent init --keypair {keypair}")
        raise typer.Exit(1)

    agent = _get_agent(keypair=keypair, api_url=api_url)
    info = {
        "handle": agent.handle or "(not registered)",
        "keypair_path": str(path),
        "api_url": api_url,
    }
    if agent.handle:
        try:
            card = agent.resolve(agent.handle)
            info["public_key"] = card.get("public_key", "")[:16] + "..."
            info["capabilities"] = card.get("capabilities", [])
            info["description"] = card.get("description", "")
            expires_at = card.get("expires_at")
            if expires_at:
                info["expires_at"] = expires_at
                info["handle_type"] = "ephemeral"
            else:
                info["handle_type"] = "permanent"
        except Exception:
            info["note"] = "Registered locally but could not resolve from API"

    typer.echo(json.dumps(info, indent=2))

    # Show expiry warning
    if info.get("handle_type") == "ephemeral":
        typer.echo(
            f"\n⚠ Ephemeral handle — expires at {info['expires_at']}\n"
            "  Run: postagent register <handle> --permanent  to keep it forever ($1)."
        )


def _inbox_path(handle: str) -> Path:
    """Return the inbox file path for a given handle."""
    return Path(f"~/.postagent/{handle}_inbox.jsonl").expanduser()


@app.command()
def listen(
    keypair: str = typer.Option("~/.postagent/keypair.json", help="Path to keypair file."),
    api_url: str = typer.Option(
        "https://postagent.fly.dev", "--api", help="PostAgent API server URL."
    ),
):
    """Listen for incoming encrypted messages (blocks forever).

    \b
    Subscribes to this agent's MQTT inbox. Incoming messages are printed
    to stdout AND saved to ~/.postagent/{handle}_inbox.jsonl so that
    'postagent check' can read them. Press Ctrl+C to stop.

    \b
    Run in background after registering:
      postagent listen --keypair ~/.postagent/alice.json &

    \b
    Examples:
      postagent listen
      postagent listen --keypair ~/.postagent/bob.json
    """
    agent = _get_agent(keypair=keypair, api_url=api_url)
    if not agent.handle:
        typer.echo("Error: no handle in keypair. Register first.", err=True)
        raise typer.Exit(1)

    inbox = _inbox_path(agent.handle)

    def handler(sender: str, payload):
        timestamp = datetime.now().strftime("%H:%M:%S")
        # Print to stdout
        typer.echo(f"\n[{timestamp}] from {sender}:")
        if isinstance(payload, dict):
            typer.echo(json.dumps(payload, indent=2))
        else:
            typer.echo(payload)
        # Append to inbox file
        entry = {"from": sender, "payload": payload, "received_at": timestamp}
        with open(inbox, "a") as f:
            f.write(json.dumps(entry) + "\n")

    typer.echo(f"Listening as [{agent.handle}]... (Ctrl+C to stop)")
    typer.echo(f"Inbox: {inbox}")
    agent.listen(handler=handler)


@app.command()
def send(
    target: str = typer.Argument(..., help="Target agent handle."),
    message: str | None = typer.Argument(
        None, help="Message text to send (or use --payload/--file for JSON)."
    ),
    payload: str | None = typer.Option(None, "--payload", "-p", help="JSON payload string."),
    file: Path | None = typer.Option(None, "--file", "-f", help="Path to JSON file to send."),
    keypair: str = typer.Option("~/.postagent/keypair.json", help="Path to keypair file."),
    api_url: str = typer.Option(
        "https://postagent.fly.dev", "--api", help="PostAgent API server URL."
    ),
):
    """Send an encrypted message to another agent.

    \b
    Resolves the target's public key, encrypts with NaCl box,
    and publishes to their MQTT inbox.

    \b
    Accepts a plain text message, JSON payload, JSON file, or stdin:
      postagent send bob "hello from alice"
      postagent send bob --payload '{"task": "analyze", "url": "..."}'
      postagent send bob --file request.json
      echo '{"msg": "hi"}' | postagent send bob

    \b
    Examples:
      postagent send bob "hello!"
      postagent send inspector -p '{"task": "review", "pr": 42}'
    """
    agent = _get_agent(keypair=keypair, api_url=api_url)
    if not agent.handle:
        typer.echo("Error: no handle in keypair. Register first.", err=True)
        raise typer.Exit(1)

    if file:
        data = json.loads(file.read_text())
    elif payload:
        data = json.loads(payload)
    elif message:
        data = {"msg": message, "from_agent": agent.handle}
    elif not sys.stdin.isatty():
        data = json.loads(sys.stdin.read())
    else:
        typer.echo("Error: provide a message, --payload, --file, or pipe JSON to stdin.", err=True)
        raise typer.Exit(1)

    agent.send(target, data)
    typer.echo(f"Sent encrypted message to {target}")


@app.command()
def check(
    keypair: str = typer.Option("~/.postagent/keypair.json", help="Path to keypair file."),
):
    """Check for new messages (non-blocking).

    \b
    Reads messages from the inbox file written by 'postagent listen'.
    Prints any new messages and clears the inbox. Instant — no MQTT needed.

    \b
    Requires 'postagent listen' running in the background.

    \b
    Examples:
      postagent check
      postagent check --keypair ~/.postagent/alice.json
    """
    agent = _get_agent(keypair=keypair)
    if not agent.handle:
        typer.echo("Error: no handle in keypair. Register first.", err=True)
        raise typer.Exit(1)

    inbox = _inbox_path(agent.handle)
    if not inbox.exists() or inbox.stat().st_size == 0:
        typer.echo("No new messages.")
        return

    messages = []
    for line in inbox.read_text().strip().splitlines():
        try:
            messages.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    # Clear the inbox
    inbox.write_text("")

    if not messages:
        typer.echo("No new messages.")
    else:
        for msg in messages:
            payload = msg["payload"]
            if isinstance(payload, dict) and "msg" in payload:
                text = payload["msg"]
            elif isinstance(payload, dict):
                text = json.dumps(payload)
            else:
                text = str(payload)
            typer.echo(f"[{msg['from']}]: {text}")


@app.command()
def discover(
    capability: str = typer.Option(..., "--capability", "-c", help="Capability tag to search for."),
    limit: int = typer.Option(10, help="Maximum number of results."),
    keypair: str = typer.Option("~/.postagent/keypair.json", help="Path to keypair file."),
    api_url: str = typer.Option(
        "https://postagent.fly.dev", "--api", help="PostAgent API server URL."
    ),
):
    """Search for agents by capability tag.

    \b
    Queries the PostAgent API for agents that advertise a given capability.

    \b
    Examples:
      postagent discover -c chat
      postagent discover -c home-inspection --limit 5
    """
    agent = _get_agent(keypair=keypair, api_url=api_url)
    results = agent.discover(capability=capability, limit=limit)
    if not results:
        typer.echo(f"No agents found with capability '{capability}'")
        raise typer.Exit(0)
    typer.echo(json.dumps(results, indent=2))


@app.command()
def resolve(
    handle: str = typer.Argument(..., help="Agent handle to look up."),
    keypair: str = typer.Option("~/.postagent/keypair.json", help="Path to keypair file."),
    api_url: str = typer.Option(
        "https://postagent.fly.dev", "--api", help="PostAgent API server URL."
    ),
):
    """Look up an agent's full card by handle.

    \b
    Returns the agent's public key, capabilities, description, and pricing.

    \b
    Examples:
      postagent resolve alice
      postagent resolve inspector --api https://postagent.fly.dev
    """
    agent = _get_agent(keypair=keypair, api_url=api_url)
    try:
        result = agent.resolve(handle)
        typer.echo(json.dumps(result, indent=2))
    except Exception as e:
        typer.echo(f"Agent '{handle}' not found: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def chat(
    target: str = typer.Argument(..., help="Agent handle to chat with."),
    keypair: str = typer.Option("~/.postagent/keypair.json", help="Path to keypair file."),
    api_url: str = typer.Option(
        "https://postagent.fly.dev", "--api", help="PostAgent API server URL."
    ),
):
    """Interactive encrypted chat with another agent.

    \b
    Opens a bidirectional channel: type messages and hit enter to send.
    Incoming messages appear inline. Press Ctrl+C to quit.

    \b
    Examples:
      postagent chat bob
      postagent chat alice --keypair ~/.postagent/bob.json
    """
    agent = _get_agent(keypair=keypair, api_url=api_url)
    if not agent.handle:
        typer.echo("Error: no handle in keypair. Register first.", err=True)
        raise typer.Exit(1)

    typer.echo(f"[{agent.handle}] chatting with [{target}] (Ctrl+C to quit)")
    typer.echo("-" * 50)

    # Listen for incoming messages in background
    def handler(sender: str, payload):
        if isinstance(payload, dict) and "msg" in payload:
            text = payload["msg"]
        elif isinstance(payload, dict):
            text = json.dumps(payload)
        elif isinstance(payload, bytes):
            text = payload.decode()
        else:
            text = str(payload)
        timestamp = datetime.now().strftime("%H:%M:%S")
        typer.echo(f"\r\033[K  [{timestamp}] {sender}: {text}")
        sys.stdout.write(f"  [{agent.handle}] > ")
        sys.stdout.flush()

    listen_thread = threading.Thread(target=agent.listen, args=(handler,), daemon=True)
    listen_thread.start()

    # Interactive send loop
    try:
        while True:
            text = input(f"  [{agent.handle}] > ")
            if not text.strip():
                continue
            agent.send(target, {"msg": text})
    except (KeyboardInterrupt, EOFError):
        typer.echo("\nBye!")
        agent.stop()


if __name__ == "__main__":
    app()
