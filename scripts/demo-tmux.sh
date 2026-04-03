#!/usr/bin/env bash
set -euo pipefail

# PostAgent Claude-to-Claude Demo — tmux launcher
#
# Launches 2 panes side by side:
#   Pane 0 (left):  Alice (Claude Code)
#   Pane 1 (right): Bob   (Claude Code)
#
# Both agents hit the production API at postagent.fly.dev
# and use test.mosquitto.org for MQTT. No local infra needed.
#
# Each Claude instance reads its CLAUDE.md which instructs it to:
#   1. Download the postagent binary
#   2. Init keypair + register via the CLI
#   3. Discover the other agent and start debating
#
# Usage: scripts/demo-tmux.sh
# Prerequisites: tmux, claude CLI

cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"

SESSION="postagent-demo"

# --- Preflight checks ---
for cmd in tmux claude; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: $cmd not found. Install it first." >&2
        exit 1
    fi
done

for agent in alice bob; do
    if [ ! -f "demo/$agent/CLAUDE.md" ]; then
        echo "ERROR: demo/$agent/CLAUDE.md not found." >&2
        exit 1
    fi
done

# Kill any existing session
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Clean stale state
rm -f "$HOME/.postagent/alice.json" "$HOME/.postagent/bob.json"
rm -f "$HOME/.postagent/alice_inbox.jsonl" "$HOME/.postagent/bob_inbox.jsonl"

# --- Create tmux session ---
tmux new-session -d -s "$SESSION" -x 200 -y 50

# Pane 0 (left): Alice
tmux send-keys -t "$SESSION:0.0" "echo '=== Launching Alice ===' && \
cd $PROJECT_ROOT/demo/alice && \
claude --dangerously-skip-permissions 'Follow your CLAUDE.md instructions. Set yourself up, then start the conversation with Bob.'" Enter

# Pane 1 (right): Bob — slight delay so Alice registers first
tmux split-window -h -t "$SESSION:0"
tmux send-keys -t "$SESSION:0.1" "sleep 5 && \
echo '=== Launching Bob ===' && \
cd $PROJECT_ROOT/demo/bob && \
claude --dangerously-skip-permissions 'Follow your CLAUDE.md instructions. Set yourself up, then wait for Alice to message you and respond.'" Enter

# Select Alice's pane
tmux select-pane -t "$SESSION:0.0"

echo "Attaching to tmux session '$SESSION'..."
echo ""
echo "  Pane 0 (left):  Alice — AI security researcher"
echo "  Pane 1 (right): Bob   — AI systems architect"
echo ""
echo "  Topic: What's the killer app for encrypted agent-to-agent comms?"
echo ""
echo "  Both agents download the postagent binary, register on prod,"
echo "  and debate over end-to-end encrypted MQTT messages."
echo ""
echo "Navigation: Ctrl-B + arrow keys | Scroll: Ctrl-B + ["
echo "Kill: tmux kill-session -t $SESSION"
echo ""

tmux attach -t "$SESSION"
