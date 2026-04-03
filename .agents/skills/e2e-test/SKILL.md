---
name: e2e-test
description: Run end-to-end agent messaging test when changes affect MQTT, encryption, or the client library. Registers two test agents, exchanges encrypted messages, validates decryption round-trip.
trigger: When postagent/client/ or encryption-related code changes
output: Pass/fail with message exchange log showing encrypt → publish → receive → decrypt
---

# End-to-End Agent Test

## Steps
1. Run `python scripts/e2e-demo.py` which:
   - Generates two ephemeral keypairs in temp directories
   - Registers agent-a (inspector) and agent-b (tester) via the API
   - Tester discovers inspector by capability
   - Tester sends an encrypted message to inspector's MQTT inbox
   - Inspector receives, decrypts, and replies
   - Tester receives and decrypts the reply
2. The script validates the full round-trip automatically and exits 0 on success
3. Uses the production API (postagent.fly.dev) and test.mosquitto.org by default
   - Override with `POSTAGENT_API_URL=http://localhost:8000` for local testing

## What the Model Does
- Interprets any connection or encryption errors
- Verifies the test exercises the real MQTT broker (test.mosquitto.org)
- Confirms the encryption/decryption path is correct
- If the script times out (15s), investigates whether MQTT connectivity or API registration is the bottleneck
