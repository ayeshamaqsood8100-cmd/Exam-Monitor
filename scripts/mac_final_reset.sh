#!/usr/bin/env bash
set -euo pipefail

echo "== Markaz macOS final-test reset =="
echo

echo "Stopping any running Markaz agent/watchdog processes..."
pkill -f "agent.main" 2>/dev/null || true
pkill -f "agent.watchdog" 2>/dev/null || true

echo "Removing Markaz local state files..."
rm -f "$HOME/.markaz_session.json"
rm -f "$HOME/.markaz_restart.json"
rm -f "$HOME/.markaz_blocked"

PLIST_PATH="$HOME/Library/LaunchAgents/com.markaz.sentinel.plist"
echo "Removing LaunchAgent state..."
launchctl unload "$PLIST_PATH" 2>/dev/null || true
rm -f "$PLIST_PATH"

echo
echo "Manual step still required:"
echo "Revoke and then re-allow Accessibility and Input Monitoring"
echo "for the same terminal app you will use for the final run."
echo "- If using Terminal.app, update Terminal permissions."
echo "- If using iTerm, update iTerm permissions."
echo
echo "Reset complete."
