# Windows EXE Release And Final Test Plan

## Goal

Ship a student-ready Windows build that behaves like a normal desktop application:

- double-clickable `.exe` entrypoint
- no Python or venv required on student machines
- stable watchdog restart behavior
- consent, ERP, access-code, widget, sync, and shutdown flows all verified
- clear rollback path if packaging breaks collector behavior

## Scope

This plan covers the local Windows agent only:

- `agent.main`
- `agent.watchdog`
- supporting modules under `agent/`
- local startup/autostart registration
- packaged runtime validation on clean Windows machines

This plan does not cover:

- backend deployment
- dashboard deployment
- macOS packaging

## Deliverables

1. One packaged student launcher `.exe`
2. One packaged setup or diagnostics `.exe` if needed
3. A reproducible build command and build notes
4. A clean test matrix and sign-off checklist
5. A rollback path to the current source-run workflow

## Packaging Strategy

### Recommended shape

Use one visible entry launcher and keep the watchdog behavior inside the packaged build:

- Primary student app: `MarkazSentinel.exe`
- Optional support utility: `MarkazSentinelSetup.exe`

The student should open only one file. That launcher should start the watchdog flow, and the watchdog should launch the packaged agent child process rather than `python -m agent.main`.

### Recommended tool

Use PyInstaller first because it is the shortest path from the current codebase:

- supports bundling Python runtime
- handles `tkinter`
- works well for single-file or one-folder desktop packaging
- is easy to debug during first packaging passes

Start with `--onedir` for debugging and switch to `--onefile` only after behavior is stable.

## Code Changes Needed Before Packaging

### 1. Packaged runtime detection

Add a helper used by watchdog and autostart code so the app can tell whether it is running:

- from source
- from a PyInstaller bundle

This helper should provide:

- executable path
- app working directory
- command for launching the packaged agent child

### 2. Watchdog child launch

`agent.watchdog` currently launches:

- `sys.executable -m agent.main`

For packaged builds, change this to launch the packaged agent entrypoint directly. The watchdog should not assume Python source execution when frozen.

### 3. Config loading

Decide how production Windows builds receive:

- `BACKEND_URL`
- `BACKEND_API_KEY`
- `EXAM_ID`

Recommended order:

1. packaged `.env` in the app directory for controlled test builds
2. bundled config file for production exam-specific builds
3. environment variables only for developer use

Do not rely on students manually exporting variables.

### 4. Startup/autostart

Verify Windows autostart registration still works when frozen:

- scheduled task path
- helper `.vbs` behavior
- current working directory
- log paths

Autostart must point to the packaged executable, not Python.

### 5. Logging

Add or confirm clear local log files for packaged runs:

- launcher log
- watchdog log
- agent runtime log

These are critical for final QA and lab debugging.

## Packaging Steps

### Phase A: Debug-friendly package

1. Create a PyInstaller spec for the watchdog launcher
2. Build with `--onedir`
3. Include all `agent/` modules and runtime dependencies
4. Verify bundled `tkinter`, `pynput`, `pygetwindow`, `pyperclip`, `httpx`, and config loading
5. Run the packaged app from a clean folder outside the repo

### Phase B: Freeze child-process behavior

1. Confirm the packaged watchdog launches the packaged agent
2. Confirm restart-after-crash still works
3. Confirm autostart registration writes correct executable paths
4. Confirm the agent can resume after reboot using packaged paths

### Phase C: Release candidate build

1. Decide whether to keep `--onedir` or move to `--onefile`
2. Add icon and metadata
3. Build release candidate
4. Smoke test on clean Windows machine
5. Archive build output and matching config

## Final Test Matrix

### Environment matrix

Test on at least:

- Windows 10
- Windows 11

Use at least one clean machine or VM with no Python installed.

### Functional test cases

#### A. First launch

- Launch packaged app by double-click
- ERP prompt appears
- consent flow appears
- access code returns
- widget becomes visible
- no terminal dependency for the student

#### B. Session start

- valid ERP starts session
- invalid ERP shows clean error
- backend unavailable shows clean network error

#### C. Collectors

- keystrokes captured
- clipboard copy captured
- window titles captured
- browser tab titles captured on supported Windows browsers

#### D. Sync

- telemetry sync initializes
- keystrokes/windows/clipboard reach backend
- offline periods recorded after temporary disconnect

#### E. Widget and student end flow

- widget stays topmost
- passcode gate works
- student end flow calls backend and shuts down cleanly

#### F. Invigilator control flow

- remote pause works
- remote restart works
- remote terminate works
- `force_stop` path works

#### G. Crash recovery

- kill agent process while watchdog is running
- watchdog restarts agent
- restart marker is created
- session resumes correctly

#### H. Reboot recovery

- autostart registration succeeds
- reboot or relogin restarts watchdog
- agent resumes saved session

#### I. Clean shutdown and device block

- end session removes active session file
- device block behavior still matches intended policy
- autostart entries are removed when expected

## QA Checklist

Mark each item pass/fail:

- packaged app launches without Python installed
- ERP input works
- consent works
- access code displays
- widget works
- keystrokes reach dashboard
- clipboard reaches dashboard
- window titles reach dashboard
- session summary renders correctly
- remote pause/restart/end work
- watchdog restart works
- reboot recovery works
- autostart registration works
- logs are readable
- uninstall/cleanup path works

## Risks To Watch

### 1. Frozen child-process launch

The watchdog/source assumption is the highest packaging risk. If not handled cleanly, the packaged watchdog may fail to relaunch the agent.

### 2. Antivirus or SmartScreen friction

Unsigned Windows executables may be flagged or warned on first launch.

### 3. Tkinter packaging

The ERP/consent/widget UI must be verified in the frozen runtime, especially font/layout differences.

### 4. Keyboard hooks

`pynput` can behave differently in packaged apps, so collector tests must be real, not assumed from source behavior.

### 5. Path handling

Any code relying on source-relative paths can break when frozen.

## Rollback Plan

If the packaged Windows build fails late in testing:

1. keep the current source-run workflow available for controlled pilot exams
2. ship only after watchdog restart, collectors, and autostart are stable
3. prefer a working `--onedir` build over a broken `--onefile` build

## Recommended Order Of Work

1. Add frozen-runtime path helpers
2. Update watchdog launch behavior for packaged runs
3. Update autostart paths for packaged runs
4. Create first PyInstaller `--onedir` build
5. Run clean-machine smoke test
6. Fix packaging issues
7. Run full QA matrix
8. Create release candidate
