#!/usr/bin/env bash
set -euo pipefail

# PostAgent Claude-to-Claude Demo — tmux launcher
#
# Launches 3 panes:
#   Pane 0 (top):          mosquitto + API server
#   Pane 1 (bottom-left):  Alice (Claude Code — uses postagent CLI)
#   Pane 2 (bottom-right): Bob   (Claude Code — uses postagent CLI)
#
# Each Claude instance reads its CLAUDE.md which instructs it to:
#   1. Init keypair + register via the CLI
#   2. Discover the other agent and start chatting
#
# No MCP required — agents use the postagent CLI via Bash tool.
#
# Usage: scripts/demo-tmux.sh
# Prerequisites: tmux, mosquitto, claude CLI, .venv set up

cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"

SESSION="postagent-demo"

# --- Preflight checks ---
for cmd in tmux mosquitto claude; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: $cmd not found. Install it first." >&2
        exit 1
    fi
done

if [ ! -d ".venv" ]; then
    echo "ERROR: .venv not found. Run: python -m venv .venv && pip install -e '.[dev]'" >&2
    exit 1
fi

for agent in alice bob; do
    if [ ! -f "demo/$agent/CLAUDE.md" ]; then
        echo "ERROR: demo/$agent/CLAUDE.md not found." >&2
        exit 1
    fi
done

# Kill any existing session
tmux kill-session -t "$SESSION" 2>/dev/null || true

# Kill stale processes from previous runs
pkill -f "uvicorn postagent.api.main:app" 2>/dev/null || true
pkill -f "mosquitto -p 1883" 2>/dev/null || true

# Clean stale state
rm -f "$PROJECT_ROOT/postagent.db"
rm -f "$HOME/.postagent/alice.json" "$HOME/.postagent/bob.json"

# --- Create tmux session ---
tmux new-session -d -s "$SESSION" -x 200 -y 50

# Pane 0 (top): Start mosquitto + API server
tmux send-keys -t "$SESSION:0.0" "echo '=== PostAgent Infrastructure ===' && \
mosquitto -p 1883 -d && \
echo 'mosquitto started on :1883' && \
cd $PROJECT_ROOT && \
source .venv/bin/activate && \
SQLITE_PATH=postagent.db MQTT_BROKER=localhost uvicorn postagent.api.main:app --port 8000" Enter

# Split bottom half into two panes for Alice and Bob
tmux split-window -v -t "$SESSION:0"
tmux split-window -h -t "$SESSION:0.1"

# Wait for API to be healthy before launching agents
WAIT_CMD="echo 'Waiting for API...' && for i in \$(seq 1 30); do curl -sf http://localhost:8000/health >/dev/null 2>&1 && break; sleep 1; done && echo 'API is up!'"

# Pane 1 (bottom-left): Alice — interactive Claude Code
tmux send-keys -t "$SESSION:0.1" "$WAIT_CMD && \
echo '=== Launching Alice ===' && \
cd $PROJECT_ROOT/demo/alice && \
claude" Enter

# Pane 2 (bottom-right): Bob — interactive Claude Code, slight delay
tmux send-keys -t "$SESSION:0.2" "$WAIT_CMD && sleep 3 && \
echo '=== Launching Bob ===' && \
cd $PROJECT_ROOT/demo/bob && \
claude" Enter

# Select Alice's pane
tmux select-pane -t "$SESSION:0.1"

echo "Attaching to tmux session '$SESSION'..."
echo ""
echo "  Pane 0 (top):          API server + mosquitto"
echo "  Pane 1 (bottom-left):  Alice (Claude Code)"
echo "  Pane 2 (bottom-right): Bob (Claude Code)"
echo ""
echo "Once attached, tell Alice or Bob:"
echo "  'Follow your CLAUDE.md instructions and start a conversation.'"
echo ""
echo "Navigation: Ctrl-B + arrow keys | Scroll: Ctrl-B + ["
echo "Kill: tmux kill-session -t $SESSION"
echo ""

tmux attach -t "$SESSION"
