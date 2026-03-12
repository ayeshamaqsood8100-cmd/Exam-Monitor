# macOS Final Terminal Test

Use this flow for the final macOS sanity pass before compilation/distribution work.

## 1. Reset the Mac test state
From the repo root on the tester machine:

```bash
bash scripts/mac_final_reset.sh
```

Then manually revoke old permissions for the terminal app that will be used in the test:

- Accessibility
- Input Monitoring

If the tester uses Terminal.app, update Terminal permissions. If the tester uses iTerm, update iTerm permissions instead.

## 2. Export the test environment
Reuse the same environment values that were used in the previous Mac run:

```bash
export BACKEND_URL="..."
export BACKEND_API_KEY="..."
export EXAM_ID="..."
```

## 3. Run the final terminal pass
From the repo root:

```bash
bash scripts/mac_final_terminal_run.sh
```

This intentionally runs:

1. `python -m agent.setup_mac`
2. `python -m agent.main`

The primary final pass should not use `agent.watchdog`.

## 4. What must pass
- setup checks for keyboard, window detection, runtime warm-up, and clipboard
- ERP entry in terminal
- consent in terminal
- access code display
- visible monitoring widget on macOS
- keystrokes, clipboard, and active-window capture
- heartbeat and at least one sync cycle
- dashboard pause and restart behavior

Silent widget failure is a test failure.

## 5. Post-test cleanup verification
After the run, verify:

- no Markaz Python process is still running
- `~/Library/LaunchAgents/com.markaz.sentinel.plist` is absent if the run ended through the hard-stop path
- `~/.markaz_session.json` is absent
- `~/.markaz_restart.json` is absent
- `~/.markaz_blocked` exists only when the chosen end path intentionally blocks reuse
