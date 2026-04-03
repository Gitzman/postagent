---
name: e2e-test
description: Run end-to-end agent messaging test when changes affect MQTT, encryption, or the client library. Registers two test agents, exchanges encrypted messages, validates decryption round-trip.
trigger: When postagent/client/ or encryption-related code changes
output: Pass/fail with message exchange log showing encrypt → publish → receive → decrypt
---

# End-to-End Agent Test

## Steps
1. Run `scripts/e2e-test.sh` which:
   - Generates two ephemeral keypairs
   - Registers agent-a and agent-b via the API
   - agent-a sends an encrypted message to agent-b's inbox
   - agent-b receives and decrypts the message
   - agent-b replies encrypted to agent-a
   - agent-a receives and decrypts the reply
2. Compare sent plaintext with received plaintext — must match exactly
3. Verify messages were actually encrypted on the wire (not plaintext)

## What the Model Does
- Interprets any connection or encryption errors
- Verifies the test exercises the real MQTT broker (test.mosquitto.org)
- Confirms the encryption/decryption path is correct
