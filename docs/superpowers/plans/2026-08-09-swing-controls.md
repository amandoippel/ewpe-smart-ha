# Swing Controls (Phase 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose vertical (up/down) and horizontal (left/right) vane swing control on the EWPE Smart climate entity, using Home Assistant's native `swing_mode` and `swing_horizontal_mode` climate features.

**Architecture:** Two new raw protocol parameters (`SwUpDn`, `SwingLfRig`) are polled alongside the existing Phase 1 parameters and mapped to/from human-readable string labels in `climate.py`, following the exact dict-mapping pattern already used for `hvac_mode` and `fan_mode`.

**Tech Stack:** Python 3.12, Home Assistant 2025.1.4 (installed; integration targets ≥ 2024.8.0), pytest + pytest-homeassistant-custom-component, repo venv at `C:\Claude\airco functions\.venv`.

## Global Constraints

- Repo: fork `amandoippel/ewpe-smart-ha`, cloned at `C:\Claude\airco functions`, working on branch `feature/swing-controls`.
- Confirmed device value mapping (live-tested against mac `502cc66cae10` at 192.168.40.11 on 2026-08-09 — see `docs/superpowers/specs/2026-08-09-swing-controls-design.md`):
  - `SwUpDn`: 0=Default, 1=Full swing, 2=Fixed upmost, 3=Fixed middle-up, 4=Fixed middle, 5=Fixed middle-low, 6=Fixed lowest. Value 7 is an invalid fallback state (vane flutters, no app option) — never emit or list it.
  - `SwingLfRig`: 0=Default, 1=Full swing, 2=Fixed leftmost, 3=Fixed middle-left, 4=Fixed middle, 5=Fixed middle-right, 6=Fixed rightmost.
- `ClimateEntityFeature.SWING_MODE` and `.SWING_HORIZONTAL_MODE` are both available (confirmed against the installed `homeassistant` 2025.1.4 package).
- Ruff config (`pyproject.toml`): line length 88, target py312, rules `E,F,W,I,B,UP,ASYNC` (E501 and ASYNC109 ignored). Run `".venv/Scripts/python.exe" -m ruff check custom_components tests` after each task.
- **Known Windows-only test-runner issue:** running `pytest` directly in this venv on this Windows machine fails ALL tests (including pre-existing ones, unrelated to this feature) with `pytest_socket.SocketBlockedError` — Windows' `ProactorEventLoop` needs a real loopback `socket.socketpair()` to start, which `pytest-socket` (wired in globally by `pytest-homeassistant-custom-component`'s `enable_custom_integrations` fixture, applied `autouse=True` in `tests/conftest.py`) blocks. This does not happen in CI (`.github/workflows/tests.yml` runs on `ubuntu-latest`, where `socket.socketpair()` uses a real Unix `AF_UNIX` pair that `pytest-socket` allows by default). **Do not attempt to fix this — it's a pre-existing environment limitation, out of scope.** Each task below therefore has two verification steps: a standalone script (bypasses pytest's fixture chain, works fine on Windows, gives fast local feedback) and the real pytest test added to the suite (verified once pushed, via GitHub Actions on Linux — Task 4).

---

### Task 1: Vertical swing (`SwUpDn`)

**Files:**
- Modify: `custom_components/ewpe_smart/const.py` (append after `MAX_TEMP = 30`)
- Modify: `custom_components/ewpe_smart/climate.py`
- Test: `tests/test_climate.py`

**Interfaces:**
- Consumes: `EwpeClimateEntity._data` (existing property, `climate.py:115-117`), `EwpeClimateEntity._send()` (existing helper, `climate.py:176-178`)
- Produces: `PARAM_SWING_VERTICAL` (const, value `"SwUpDn"`), `SWING_MODE_TO_DEVICE` / `DEVICE_TO_SWING_MODE` dicts, `EwpeClimateEntity.swing_mode` property, `EwpeClimateEntity.async_set_swing_mode()` method — all consumed by Task 3 (poll wiring) and usable standalone from Task 2.

- [ ] **Step 1: Add vertical swing constants to `const.py`**

Append to the end of `custom_components/ewpe_smart/const.py`:

```python

# ── Swing (Phase 3) ─────────────────────────────────────────────────────────
PARAM_SWING_VERTICAL = "SwUpDn"
PARAM_SWING_HORIZONTAL = "SwingLfRig"

SWING_VERTICAL_DEFAULT = 0
SWING_VERTICAL_FULL = 1
SWING_VERTICAL_FIXED_UPMOST = 2
SWING_VERTICAL_FIXED_MIDDLE_UP = 3
SWING_VERTICAL_FIXED_MIDDLE = 4
SWING_VERTICAL_FIXED_MIDDLE_LOW = 5
SWING_VERTICAL_FIXED_LOWEST = 6
```

(The horizontal value constants are added in Task 2 — this step only adds the two `PARAM_*` keys and the vertical values, since `PARAM_SWING_HORIZONTAL` is harmless to declare now but unused until Task 2.)

- [ ] **Step 2: Write the failing tests for `swing_mode`**

Add to `tests/test_climate.py`, after the existing `test_implausible_temp_sensor_is_none` function and its blank line:

```python
@pytest.mark.parametrize(
    ("device_value", "expected"),
    [
        (0, "Default"),
        (1, "Full swing"),
        (2, "Fixed - upmost"),
        (3, "Fixed - middle-up"),
        (4, "Fixed - middle"),
        (5, "Fixed - middle-low"),
        (6, "Fixed - lowest"),
    ],
)
def test_swing_mode_maps_correctly(device_value: int, expected: str) -> None:
    entity, _ = _make_entity({"Pow": 1, "Mod": 1, "SwUpDn": device_value})
    assert entity.swing_mode == expected


def test_swing_mode_missing_is_none() -> None:
    entity, _ = _make_entity({"Pow": 1, "Mod": 1})
    assert entity.swing_mode is None
```

Add to the end of `tests/test_climate.py`:

```python


@pytest.mark.asyncio
async def test_set_swing_mode_emits_swupdn() -> None:
    entity, device = _make_entity({"Pow": 1, "Mod": 1, "SwUpDn": 0})
    await entity.async_set_swing_mode("Fixed - lowest")
    device.set_state.assert_awaited_once_with({PARAM_SWING_VERTICAL: 6})
```

Update the import block at the top of `tests/test_climate.py` from:

```python
from custom_components.ewpe_smart.const import (
    PARAM_FAN_SPEED,
    PARAM_MODE,
    PARAM_POWER,
    PARAM_SET_TEMP,
)
```

to:

```python
from custom_components.ewpe_smart.const import (
    PARAM_FAN_SPEED,
    PARAM_MODE,
    PARAM_POWER,
    PARAM_SET_TEMP,
    PARAM_SWING_VERTICAL,
)
```

- [ ] **Step 3: Verify the tests fail (standalone script, not pytest — see Global Constraints)**

Create `C:\Users\AMANDO~1\AppData\Local\Temp\claude\C--Claude-airco-functions\91a4360a-c7ba-4618-a8c1-ff5f3bfbcb5e\scratchpad\verify_task1.py`:

```python
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, r"C:\Claude\airco functions")

from custom_components.ewpe_smart.climate import EwpeClimateEntity
from custom_components.ewpe_smart.const import PARAM_SWING_VERTICAL


def _make_entity(status):
    coordinator = MagicMock()
    coordinator.data = status
    coordinator.last_update_success = True
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    device = MagicMock()
    device.mac = "AA:BB:CC:DD:EE:FF"
    device.name = "Test"
    device.info = {}
    device.set_state = AsyncMock()
    coordinator.device = device
    entry = MagicMock()
    entry.entry_id = "abc"
    entry.title = "Test"
    return EwpeClimateEntity(coordinator, entry), device


async def main():
    entity, _ = _make_entity({"Pow": 1, "Mod": 1, "SwUpDn": 2})
    assert entity.swing_mode == "Fixed - upmost", entity.swing_mode
    print("verify_task1: PASS")


asyncio.run(main())
```

Run: `".venv/Scripts/python.exe" "C:\Users\AMANDO~1\AppData\Local\Temp\claude\C--Claude-airco-functions\91a4360a-c7ba-4618-a8c1-ff5f3bfbcb5e\scratchpad\verify_task1.py"`
Expected: `AttributeError: 'EwpeClimateEntity' object has no attribute 'swing_mode'`

- [ ] **Step 4: Implement vertical swing mapping in `climate.py`**

In `custom_components/ewpe_smart/climate.py`, update the import block:

```python
from .const import (
    DOMAIN,
    FAN_SPEED_AUTO,
    FAN_SPEED_HIGH,
    FAN_SPEED_LOW,
    FAN_SPEED_MEDIUM,
    MANUFACTURER,
    MAX_TEMP,
    MIN_TEMP,
    MODE_AUTO,
    MODE_COOL,
    MODE_DRY,
    MODE_FAN,
    MODE_HEAT,
    PARAM_FAN_SPEED,
    PARAM_MODE,
    PARAM_POWER,
    PARAM_SET_TEMP,
    PARAM_SWING_VERTICAL,
    PARAM_TEMP_SENSOR,
    POWER_OFF,
    POWER_ON,
    SWING_VERTICAL_DEFAULT,
    SWING_VERTICAL_FIXED_LOWEST,
    SWING_VERTICAL_FIXED_MIDDLE,
    SWING_VERTICAL_FIXED_MIDDLE_LOW,
    SWING_VERTICAL_FIXED_MIDDLE_UP,
    SWING_VERTICAL_FIXED_UPMOST,
    SWING_VERTICAL_FULL,
)
```

Add after the `DEVICE_TO_FAN_MODE` dict (before `async def async_setup_entry`):

```python
SWING_MODE_TO_DEVICE: dict[str, int] = {
    "Default": SWING_VERTICAL_DEFAULT,
    "Full swing": SWING_VERTICAL_FULL,
    "Fixed - upmost": SWING_VERTICAL_FIXED_UPMOST,
    "Fixed - middle-up": SWING_VERTICAL_FIXED_MIDDLE_UP,
    "Fixed - middle": SWING_VERTICAL_FIXED_MIDDLE,
    "Fixed - middle-low": SWING_VERTICAL_FIXED_MIDDLE_LOW,
    "Fixed - lowest": SWING_VERTICAL_FIXED_LOWEST,
}
DEVICE_TO_SWING_MODE: dict[int, str] = {v: k for k, v in SWING_MODE_TO_DEVICE.items()}
```

Update `_attr_swing_modes` and `_attr_supported_features` on `EwpeClimateEntity` — change:

```python
    _attr_fan_modes = [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
```

to:

```python
    _attr_fan_modes = [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
    _attr_swing_modes = list(SWING_MODE_TO_DEVICE)
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.SWING_MODE
    )
```

Add the `swing_mode` property after the existing `fan_mode` property:

```python
    @property
    def swing_mode(self) -> str | None:
        value = self._data.get(PARAM_SWING_VERTICAL)
        if value is None:
            return None
        return DEVICE_TO_SWING_MODE.get(value)
```

Add the `async_set_swing_mode` method after `async_set_fan_mode`:

```python
    async def async_set_swing_mode(self, swing_mode: str) -> None:
        device_value = SWING_MODE_TO_DEVICE.get(swing_mode)
        if device_value is None:
            raise ValueError(f"Unsupported swing_mode: {swing_mode}")
        await self._send({PARAM_SWING_VERTICAL: device_value})
```

- [ ] **Step 5: Verify the standalone script passes**

Run: `".venv/Scripts/python.exe" "C:\Users\AMANDO~1\AppData\Local\Temp\claude\C--Claude-airco-functions\91a4360a-c7ba-4618-a8c1-ff5f3bfbcb5e\scratchpad\verify_task1.py"`
Expected: `verify_task1: PASS`

- [ ] **Step 6: Run ruff**

Run: `".venv/Scripts/python.exe" -m ruff check custom_components tests`
Expected: `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add custom_components/ewpe_smart/const.py custom_components/ewpe_smart/climate.py tests/test_climate.py
git commit -m "Add vertical swing (SwUpDn) support to climate entity"
```

---

### Task 2: Horizontal swing (`SwingLfRig`)

**Files:**
- Modify: `custom_components/ewpe_smart/const.py`
- Modify: `custom_components/ewpe_smart/climate.py`
- Test: `tests/test_climate.py`

**Interfaces:**
- Consumes: same `_data` / `_send()` as Task 1; `PARAM_SWING_HORIZONTAL` already declared in Task 1's const.py edit.
- Produces: `SWING_HORIZONTAL_MODE_TO_DEVICE` / `DEVICE_TO_SWING_HORIZONTAL_MODE` dicts, `EwpeClimateEntity.swing_horizontal_mode` property, `EwpeClimateEntity.async_set_swing_horizontal_mode()` method — consumed by Task 3 (poll wiring).

- [ ] **Step 1: Add horizontal swing value constants to `const.py`**

Append immediately after the `SWING_VERTICAL_FIXED_LOWEST = 6` line added in Task 1:

```python

SWING_HORIZONTAL_DEFAULT = 0
SWING_HORIZONTAL_FULL = 1
SWING_HORIZONTAL_FIXED_LEFTMOST = 2
SWING_HORIZONTAL_FIXED_MIDDLE_LEFT = 3
SWING_HORIZONTAL_FIXED_MIDDLE = 4
SWING_HORIZONTAL_FIXED_MIDDLE_RIGHT = 5
SWING_HORIZONTAL_FIXED_RIGHTMOST = 6
```

- [ ] **Step 2: Write the failing tests for `swing_horizontal_mode`**

Add to `tests/test_climate.py`, after the `test_swing_mode_missing_is_none` function added in Task 1:

```python
@pytest.mark.parametrize(
    ("device_value", "expected"),
    [
        (0, "Default"),
        (1, "Full swing"),
        (2, "Fixed - leftmost"),
        (3, "Fixed - middle-left"),
        (4, "Fixed - middle"),
        (5, "Fixed - middle-right"),
        (6, "Fixed - rightmost"),
    ],
)
def test_swing_horizontal_mode_maps_correctly(device_value: int, expected: str) -> None:
    entity, _ = _make_entity({"Pow": 1, "Mod": 1, "SwingLfRig": device_value})
    assert entity.swing_horizontal_mode == expected


def test_swing_horizontal_mode_missing_is_none() -> None:
    entity, _ = _make_entity({"Pow": 1, "Mod": 1})
    assert entity.swing_horizontal_mode is None
```

Add to the end of `tests/test_climate.py`:

```python


@pytest.mark.asyncio
async def test_set_swing_horizontal_mode_emits_swinglfrig() -> None:
    entity, device = _make_entity({"Pow": 1, "Mod": 1, "SwingLfRig": 0})
    await entity.async_set_swing_horizontal_mode("Fixed - rightmost")
    device.set_state.assert_awaited_once_with({PARAM_SWING_HORIZONTAL: 6})
```

Update the `tests/test_climate.py` import block (from Task 1's version) to also import `PARAM_SWING_HORIZONTAL`:

```python
from custom_components.ewpe_smart.const import (
    PARAM_FAN_SPEED,
    PARAM_MODE,
    PARAM_POWER,
    PARAM_SET_TEMP,
    PARAM_SWING_HORIZONTAL,
    PARAM_SWING_VERTICAL,
)
```

- [ ] **Step 3: Verify the new test fails (standalone script)**

Create `C:\Users\AMANDO~1\AppData\Local\Temp\claude\C--Claude-airco-functions\91a4360a-c7ba-4618-a8c1-ff5f3bfbcb5e\scratchpad\verify_task2.py`:

```python
import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, r"C:\Claude\airco functions")

from custom_components.ewpe_smart.climate import EwpeClimateEntity


def _make_entity(status):
    coordinator = MagicMock()
    coordinator.data = status
    coordinator.last_update_success = True
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    device = MagicMock()
    device.mac = "AA:BB:CC:DD:EE:FF"
    device.name = "Test"
    device.info = {}
    device.set_state = AsyncMock()
    coordinator.device = device
    entry = MagicMock()
    entry.entry_id = "abc"
    entry.title = "Test"
    return EwpeClimateEntity(coordinator, entry), device


async def main():
    entity, _ = _make_entity({"Pow": 1, "Mod": 1, "SwingLfRig": 2})
    assert entity.swing_horizontal_mode == "Fixed - leftmost", entity.swing_horizontal_mode
    print("verify_task2: PASS")


asyncio.run(main())
```

Run: `".venv/Scripts/python.exe" "C:\Users\AMANDO~1\AppData\Local\Temp\claude\C--Claude-airco-functions\91a4360a-c7ba-4618-a8c1-ff5f3bfbcb5e\scratchpad\verify_task2.py"`
Expected: `AttributeError: 'EwpeClimateEntity' object has no attribute 'swing_horizontal_mode'`

- [ ] **Step 4: Implement horizontal swing mapping in `climate.py`**

Replace the entire `from .const import (...)` block at the top of `custom_components/ewpe_smart/climate.py` (as left by Task 1) with:

```python
from .const import (
    DOMAIN,
    FAN_SPEED_AUTO,
    FAN_SPEED_HIGH,
    FAN_SPEED_LOW,
    FAN_SPEED_MEDIUM,
    MANUFACTURER,
    MAX_TEMP,
    MIN_TEMP,
    MODE_AUTO,
    MODE_COOL,
    MODE_DRY,
    MODE_FAN,
    MODE_HEAT,
    PARAM_FAN_SPEED,
    PARAM_MODE,
    PARAM_POWER,
    PARAM_SET_TEMP,
    PARAM_SWING_HORIZONTAL,
    PARAM_SWING_VERTICAL,
    PARAM_TEMP_SENSOR,
    POWER_OFF,
    POWER_ON,
    SWING_HORIZONTAL_DEFAULT,
    SWING_HORIZONTAL_FIXED_LEFTMOST,
    SWING_HORIZONTAL_FIXED_MIDDLE,
    SWING_HORIZONTAL_FIXED_MIDDLE_LEFT,
    SWING_HORIZONTAL_FIXED_MIDDLE_RIGHT,
    SWING_HORIZONTAL_FIXED_RIGHTMOST,
    SWING_HORIZONTAL_FULL,
    SWING_VERTICAL_DEFAULT,
    SWING_VERTICAL_FIXED_LOWEST,
    SWING_VERTICAL_FIXED_MIDDLE,
    SWING_VERTICAL_FIXED_MIDDLE_LOW,
    SWING_VERTICAL_FIXED_MIDDLE_UP,
    SWING_VERTICAL_FIXED_UPMOST,
    SWING_VERTICAL_FULL,
)
```

Add after the `DEVICE_TO_SWING_MODE` dict from Task 1:

```python
SWING_HORIZONTAL_MODE_TO_DEVICE: dict[str, int] = {
    "Default": SWING_HORIZONTAL_DEFAULT,
    "Full swing": SWING_HORIZONTAL_FULL,
    "Fixed - leftmost": SWING_HORIZONTAL_FIXED_LEFTMOST,
    "Fixed - middle-left": SWING_HORIZONTAL_FIXED_MIDDLE_LEFT,
    "Fixed - middle": SWING_HORIZONTAL_FIXED_MIDDLE,
    "Fixed - middle-right": SWING_HORIZONTAL_FIXED_MIDDLE_RIGHT,
    "Fixed - rightmost": SWING_HORIZONTAL_FIXED_RIGHTMOST,
}
DEVICE_TO_SWING_HORIZONTAL_MODE: dict[int, str] = {
    v: k for k, v in SWING_HORIZONTAL_MODE_TO_DEVICE.items()
}
```

Update `_attr_swing_horizontal_modes` and `_attr_supported_features` — change (from Task 1's version):

```python
    _attr_swing_modes = list(SWING_MODE_TO_DEVICE)
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.SWING_MODE
    )
```

to:

```python
    _attr_swing_modes = list(SWING_MODE_TO_DEVICE)
    _attr_swing_horizontal_modes = list(SWING_HORIZONTAL_MODE_TO_DEVICE)
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.SWING_HORIZONTAL_MODE
    )
```

Add the `swing_horizontal_mode` property after the `swing_mode` property from Task 1:

```python
    @property
    def swing_horizontal_mode(self) -> str | None:
        value = self._data.get(PARAM_SWING_HORIZONTAL)
        if value is None:
            return None
        return DEVICE_TO_SWING_HORIZONTAL_MODE.get(value)
```

Add the `async_set_swing_horizontal_mode` method after `async_set_swing_mode`:

```python
    async def async_set_swing_horizontal_mode(self, swing_horizontal_mode: str) -> None:
        device_value = SWING_HORIZONTAL_MODE_TO_DEVICE.get(swing_horizontal_mode)
        if device_value is None:
            raise ValueError(
                f"Unsupported swing_horizontal_mode: {swing_horizontal_mode}"
            )
        await self._send({PARAM_SWING_HORIZONTAL: device_value})
```

- [ ] **Step 5: Verify the standalone script passes**

Run: `".venv/Scripts/python.exe" "C:\Users\AMANDO~1\AppData\Local\Temp\claude\C--Claude-airco-functions\91a4360a-c7ba-4618-a8c1-ff5f3bfbcb5e\scratchpad\verify_task2.py"`
Expected: `verify_task2: PASS`

- [ ] **Step 6: Run ruff**

Run: `".venv/Scripts/python.exe" -m ruff check custom_components tests`
Expected: `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add custom_components/ewpe_smart/const.py custom_components/ewpe_smart/climate.py tests/test_climate.py
git commit -m "Add horizontal swing (SwingLfRig) support to climate entity"
```

---

### Task 3: Poll wiring + README

**Files:**
- Modify: `custom_components/ewpe_smart/const.py`
- Modify: `custom_components/ewpe_smart/coordinator.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `PARAM_SWING_VERTICAL`, `PARAM_SWING_HORIZONTAL`, `PHASE1_PARAMS` (all from `const.py`)
- Produces: `POLL_PARAMS` (const, `list[str]`) — consumed by `EwpeCoordinator._async_update_data`

- [ ] **Step 1: Add `POLL_PARAMS` to `const.py`**

Append to the end of `custom_components/ewpe_smart/const.py` (after the horizontal swing constants added in Task 2):

```python

POLL_PARAMS: list[str] = [
    *PHASE1_PARAMS,
    PARAM_SWING_VERTICAL,
    PARAM_SWING_HORIZONTAL,
]
```

- [ ] **Step 2: Wire it into the coordinator**

In `custom_components/ewpe_smart/coordinator.py`, change the import:

```python
from .const import DOMAIN
```

to:

```python
from .const import DOMAIN, POLL_PARAMS
```

Change `_async_update_data`:

```python
    async def _async_update_data(self) -> dict[str, int]:
        try:
            return await self.device.get_status()
```

to:

```python
    async def _async_update_data(self) -> dict[str, int]:
        try:
            return await self.device.get_status(POLL_PARAMS)
```

- [ ] **Step 3: Verify with a standalone script**

Create `C:\Users\AMANDO~1\AppData\Local\Temp\claude\C--Claude-airco-functions\91a4360a-c7ba-4618-a8c1-ff5f3bfbcb5e\scratchpad\verify_task3.py`:

```python
import sys

sys.path.insert(0, r"C:\Claude\airco functions")

from custom_components.ewpe_smart.const import POLL_PARAMS

assert "SwUpDn" in POLL_PARAMS, POLL_PARAMS
assert "SwingLfRig" in POLL_PARAMS, POLL_PARAMS
assert "Pow" in POLL_PARAMS, POLL_PARAMS  # Phase 1 params still present
print("verify_task3: PASS")
```

Run: `".venv/Scripts/python.exe" "C:\Users\AMANDO~1\AppData\Local\Temp\claude\C--Claude-airco-functions\91a4360a-c7ba-4618-a8c1-ff5f3bfbcb5e\scratchpad\verify_task3.py"`
Expected: `verify_task3: PASS`

- [ ] **Step 4: Update `README.md` Features list**

Change (in the `## Features` section):

```markdown
- 🌡️ **Climate entity** — power, HVAC mode (Auto / Cool / Heat / Dry / Fan only),
  target temperature, fan speed (Auto / Low / Medium / High)
```

to:

```markdown
- 🌡️ **Climate entity** — power, HVAC mode (Auto / Cool / Heat / Dry / Fan only),
  target temperature, fan speed (Auto / Low / Medium / High)
- 🔄 **Vane swing control** — vertical (up/down) and horizontal (left/right),
  each with full-swing and 5 fixed positions, via the climate card's swing
  dropdowns
```

- [ ] **Step 5: Update `README.md` Roadmap section**

Change:

```markdown
## Roadmap

- **Phase 2:** switch entities for sleep / turbo / quiet / X-fan / health /
  display light / energy save / fresh-air valve
- **Phase 3:** swing controls (up/down, left/right, and 4-way for cassettes)
- **Phase 4:** 8 °C frost-protection mode, child lock, lock-remote toggle
```

to:

```markdown
## Roadmap

- **Phase 2:** switch entities for sleep / turbo / quiet / X-fan / health /
  display light / energy save / fresh-air valve
- **Phase 3:** ✅ done for single-vane split units (up/down and left/right,
  see Features above); 4-way independent cassette swing (separate NE/NW/SE/SW
  vanes) is still open — needs a cassette unit to test against
- **Phase 4:** 8 °C frost-protection mode, child lock, lock-remote toggle
```

- [ ] **Step 6: Run ruff**

Run: `".venv/Scripts/python.exe" -m ruff check custom_components tests`
Expected: `All checks passed!`

- [ ] **Step 7: Commit**

```bash
git add custom_components/ewpe_smart/const.py custom_components/ewpe_smart/coordinator.py README.md
git commit -m "Poll swing parameters by default; document swing controls"
```

---

### Task 4: Push and verify on CI (Linux)

**Files:** none (no code changes — this task pushes and watches CI, which is the real pytest gate per the Windows limitation noted in Global Constraints)

- [ ] **Step 1: Push the branch**

```bash
git push -u origin feature/swing-controls
```

- [ ] **Step 2: Watch the CI run**

```bash
gh run watch --exit-status
```

If no run has started yet within a few seconds, list runs first: `gh run list --branch feature/swing-controls --limit 3`, then `gh run watch <run-id> --exit-status`.

Expected: the `pytest` job (matrix Python 3.13, `ubuntu-latest`) completes with all tests passing, including the 8 new tests added in Tasks 1–2 (`test_swing_mode_maps_correctly` ×7 parametrizations, `test_swing_mode_missing_is_none`, `test_set_swing_mode_emits_swupdn`, `test_swing_horizontal_mode_maps_correctly` ×7, `test_swing_horizontal_mode_missing_is_none`, `test_set_swing_horizontal_mode_emits_swinglfrig`), plus the `lint` and `validate` workflows.

- [ ] **Step 3: If CI fails**

Read the failing job's log with `gh run view <run-id> --log-failed`, fix the issue locally, commit, push again, and repeat Step 2. Do not proceed to Task 5 until CI is green.

---

### Task 5: Live verification in the real HA instance

**Files:** none in this repo — this task installs the branch into the user's actual Home Assistant `config/custom_components/ewpe_smart/` (manual install path, per README "Option B")

- [ ] **Step 1: Copy the updated integration into HA**

Copy `custom_components/ewpe_smart/` (all files) from this repo into the HA instance's `config/custom_components/ewpe_smart/`, overwriting the existing installed version. Exact mechanism depends on how the user's HA is deployed (Samba share, SSH/SCP, File Editor add-on, or direct filesystem access if HA runs on this same machine) — ask the user which applies before proceeding.

- [ ] **Step 2: Restart Home Assistant**

Via **Settings → System → Restart**, or `ha core restart` if using the CLI.

- [ ] **Step 3: Confirm the climate card shows both swing dropdowns**

Open the EWPE Smart device's climate card. It should now show two additional dropdown controls beyond the existing power/mode/temperature/fan controls: one labeled for swing (vertical) and one for horizontal swing, each listing the 7 options (`Default`, `Full swing`, `Fixed - upmost/leftmost`, etc.).

- [ ] **Step 4: Exercise both dropdowns against the real unit**

For each of the 7 vertical options and 7 horizontal options, select it in the HA UI and confirm the vane moves to match the mapping table in the Global Constraints section (already confirmed once during live calibration in Task 0 of the design spec — this step re-confirms the *installed integration*, not just the raw protocol, produces the same behavior end-to-end).

- [ ] **Step 5: Confirm no regression on existing controls**

Toggle power, change HVAC mode, set target temperature, change fan speed — confirm all still work exactly as before this change.

- [ ] **Step 6: Report back**

Tell me the outcome (all working / anything unexpected). If everything works, next step is deciding whether to open the PR to `anaryk/ewpe-smart-ha` (ask before opening — it's a public, visible action on someone else's repo).
