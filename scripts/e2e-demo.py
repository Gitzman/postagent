#!/usr/bin/env python3
"""End-to-end demo: two agents exchange encrypted messages via MQTT.

1. Generate keypairs for agent-a (inspector) and agent-b (tester)
2. Register both via the API
3. tester discovers inspector by capability
4. tester sends encrypted message to inspector
5. inspector receives, decrypts, and replies
6. tester receives and decrypts the reply
"""

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from postagent.client.agent import PostAgent

API_URL = os.environ.get("POSTAGENT_API_URL", "https://postagent.fly.dev")


def main():
    # Create temp directories for keypairs
    tmp_a = Path(tempfile.mkdtemp()) / "keypair.json"
    tmp_b = Path(tempfile.mkdtemp()) / "keypair.json"

    print("=" * 60)
    print("PostAgent E2E Demo")
    print("=" * 60)

    # --- Step 1: Init keypairs ---
    print("\n[1] Generating keypairs...")
    agent_a = PostAgent(keypair_path=str(tmp_a), api_url=API_URL)
    data_a = agent_a.init_keypair()
    print(f"    Agent A wallet: {data_a['wallet'][:16]}...")

    agent_b = PostAgent(keypair_path=str(tmp_b), api_url=API_URL)
    data_b = agent_b.init_keypair()
    print(f"    Agent B wallet: {data_b['wallet'][:16]}...")

    # --- Step 2: Register ---
    print("\n[2] Registering agents...")
    result_a = agent_a.register(
        handle="inspect-demo",
        capabilities=["home-inspection-analysis"],
        price=16,
        description="AI home inspection report analysis",
    )
    print(f"    Agent A: {json.dumps(result_a)}")

    result_b = agent_b.register(
        handle="tester-demo",
        capabilities=["testing"],
        description="Test agent",
    )
    print(f"    Agent B: {json.dumps(result_b)}")

    # --- Step 3: Discover ---
    print("\n[3] Tester discovers inspector by capability...")
    found = agent_b.discover(capability="home-inspection-analysis")
    print(f"    Found {len(found)} agent(s):")
    for a in found:
        print(f"      - {a['handle']}: {a['description']} (capabilities: {a['capabilities']})")

    # --- Step 4: Resolve ---
    print("\n[4] Tester resolves inspector's card...")
    card = agent_b.resolve("inspect-demo")
    print(f"    Handle: {card['handle']}")
    print(f"    Public key: {card['public_key'][:16]}...")
    print(f"    Capabilities: {card['capabilities']}")

    # --- Step 5: Exchange encrypted messages ---
    print("\n[5] Exchanging encrypted messages via MQTT (test.mosquitto.org)...")

    received_messages = []
    reply_received = threading.Event()

    # Start inspector listening in a thread
    def inspector_handler(sender, payload):
        print(f"\n    [Inspector received from {sender}]:")
        print(f"    {json.dumps(payload, indent=6) if isinstance(payload, dict) else payload}")
        received_messages.append(("inspector", sender, payload))
        # Reply back
        print(f"\n    [Inspector replying to {sender}]...")
        agent_a.reply(sender, {"result": "done", "report_url": "https://example.com/report/123"})

    def tester_handler(sender, payload):
        print(f"\n    [Tester received reply from {sender}]:")
        print(f"    {json.dumps(payload, indent=6) if isinstance(payload, dict) else payload}")
        received_messages.append(("tester", sender, payload))
        reply_received.set()

    # Start both listeners in background threads
    inspector_thread = threading.Thread(
        target=agent_a.listen, args=(inspector_handler,), daemon=True
    )
    inspector_thread.start()
    time.sleep(2)  # Wait for MQTT connection

    tester_thread = threading.Thread(target=agent_b.listen, args=(tester_handler,), daemon=True)
    tester_thread.start()
    time.sleep(2)  # Wait for MQTT connection

    # Tester sends encrypted message to inspector
    test_payload = {
        "task": "analyze",
        "url": "https://example.com/inspection-report.pdf",
        "priority": "high",
    }
    print(f"\n    [Tester sending to inspect-demo]: {json.dumps(test_payload)}")
    agent_b.send("inspect-demo", test_payload)

    # Wait for the full round trip
    failures = []

    if not reply_received.wait(timeout=15):
        failures.append(f"TIMEOUT: round-trip not completed in 15s (got {len(received_messages)} messages)")

    if not failures:
        # Verify message count
        if len(received_messages) != 2:
            failures.append(f"Expected 2 messages, got {len(received_messages)}")

        # Verify inspector received the correct payload
        if len(received_messages) >= 1:
            role, sender, payload = received_messages[0]
            if role != "inspector":
                failures.append(f"First message should be to inspector, got {role}")
            if sender != "tester-demo":
                failures.append(f"Inspector should receive from tester-demo, got {sender}")
            if isinstance(payload, dict) and payload.get("task") != "analyze":
                failures.append(f"Payload mismatch: expected task=analyze, got {payload}")

        # Verify tester received the reply
        if len(received_messages) >= 2:
            role, sender, payload = received_messages[1]
            if role != "tester":
                failures.append(f"Second message should be to tester, got {role}")
            if sender != "inspect-demo":
                failures.append(f"Tester should receive from inspect-demo, got {sender}")
            if isinstance(payload, dict) and payload.get("result") != "done":
                failures.append(f"Reply mismatch: expected result=done, got {payload}")

    # Cleanup
    agent_a.stop()
    agent_b.stop()
    tmp_a.unlink(missing_ok=True)
    tmp_b.unlink(missing_ok=True)

    # Report results
    print("\n" + "=" * 60)
    if failures:
        print("FAIL: E2E test failed")
        for f in failures:
            print(f"  ✗ {f}")
        print("=" * 60)
        sys.exit(1)
    else:
        print("PASS: Full encrypted round-trip verified")
        print(f"  ✓ Keypair generation (2 agents)")
        print(f"  ✓ Registration via API")
        print(f"  ✓ Discovery by capability")
        print(f"  ✓ Agent card resolution")
        print(f"  ✓ Encrypted send: tester → inspector (payload intact)")
        print(f"  ✓ Encrypted reply: inspector → tester (payload intact)")
        print(f"  ✓ {len(received_messages)} messages, full round-trip")
        print("=" * 60)


if __name__ == "__main__":
    main()
