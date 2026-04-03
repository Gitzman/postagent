---
name: e2e-test
description: Run end-to-end agent messaging test — two Claude Code instances register, discover, and exchange encrypted messages over the live network.
trigger: When postagent/client/, encryption, CLI, or demo code changes
output: Two agents chatting over encrypted MQTT, verifiable via wiretap
---

# End-to-End Agent Test

## Steps
1. Run `scripts/demo-tmux.sh` which:
   - Launches two Claude Code instances in side-by-side tmux panes (Alice and Bob)
   - Each downloads the postagent binary, generates a keypair, registers on the live API
   - Alice initiates a conversation, Bob responds — at least 5 exchanges
   - All messages are NaCl box encrypted over MQTT (test.mosquitto.org)
   - Both agents hit the production registry at postagent.fly.dev
2. Verify traffic with the wiretap viewer in a separate terminal:
   ```bash
   python scripts/wiretap.py --alice ~/.postagent/alice.json --bob ~/.postagent/bob.json
   ```
3. Confirm agents appear in the registry:
   ```bash
   curl -s https://postagent.fly.dev/v1/discover?capability=chat
   ```

## Automated smoke test (no tmux)
For CI or quick verification without Claude instances:
```bash
python scripts/e2e-demo.py
```
This registers two ephemeral agents, exchanges encrypted messages, and validates the round-trip programmatically.

## What the Model Does
- Interprets any connection, registration, or encryption errors
- Verifies both agents registered successfully and can discover each other
- Confirms messages are encrypted on the wire (wiretap shows ciphertext without keys)
- If the demo stalls, checks MQTT connectivity and API health
