# EWPE Smart — Swing Controls (Phase 3)

**Date:** 2026-08-09
**Status:** Approved
**Author:** Amando Ippel (via Claude)

## Problem

The integration currently implements only Phase 1 parameters (power, HVAC
mode, target temperature, fan speed, indoor temperature sensor). The user's
EWPE Smart mobile app can also drive the unit's motorised vane up / down /
left / right, but the Home Assistant integration exposes no way to do this.
This is exactly "Phase 3" on the project's own roadmap: *"swing controls
(up/down, left/right, and 4-way for cassettes)"*.

The user owns a split unit with a single vane that is motorised on both axes
(confirmed via the EWPE app's separate up/down and left/right controls), so
both vertical and horizontal swing need to be implemented, not just vertical.

## Scope

In scope:

- Vertical swing control (`SwUpDn`) exposed via Home Assistant's native
  `ClimateEntityFeature.SWING_MODE` (`swing_mode` / `swing_modes` /
  `async_set_swing_mode`)
- Horizontal swing control (`SwingLfRig`) exposed via Home Assistant's native
  `ClimateEntityFeature.SWING_HORIZONTAL_MODE` (`swing_horizontal_mode` /
  `swing_horizontal_modes` / `async_set_swing_horizontal_mode`), available
  since HA 2024.2 — the integration already targets HA ≥ 2024.8.0
- Both parameters added to the default status-poll column list so the
  coordinator picks them up
- Unit tests mirroring the existing `test_climate.py` mock-based style
- README roadmap updated to mark Phase 3 done
- Value mapping (device integer → HA string label) confirmed against the
  user's real device (192.168.40.11) before being hard-coded, since Gree-
  family firmwares are known to vary slightly between models

Out of scope (deferred):

- 4-way *independent* cassette swing (NE/NW/SE/SW quadrant control) — that is
  a different physical mechanism (multiple independent vanes) than this
  user's single 2-axis vane and needs its own device to test against
- Any Phase 2 (sleep/turbo/quiet/x-fan/health/light/save/fresh-air) or
  Phase 4 (frost protection, child lock) features — unrelated to this change

## Approach

Two independent HA climate features map cleanly onto the two independent
device parameters. This was chosen over two alternatives:

- **Separate `select` entities per axis** — rejected: adds two new entities
  per device instead of using the climate card's existing swing dropdowns,
  and diverges from how the roadmap already frames this ("swing controls").
- **Single combined swing mode** (e.g. `"Upper-Left"`) — rejected: conflates
  two independent axes into an unwieldy cartesian product of string values,
  harder to test and to extend later.

## Protocol additions

Both keys already exist in the wider Gree/EWPE protocol family (see
`tomikaa87/gree-remote`), alongside the six Phase 1 keys already implemented:

| Key | Meaning | Known range (to be confirmed live) |
|-----|---------|-------------------------------------|
| `SwUpDn` | Vertical (up/down) vane position | 0=default, 1=full swing, 2–6=fixed positions top→bottom |
| `SwingLfRig` | Horizontal (left/right) vane position | 0=default, 1=full swing, 2–6=fixed positions left→right |

The exact value → position mapping is confirmed by binding directly to
192.168.40.11 with a throwaway script built on the repo's own
`protocol.py`/`device.py`, cycling candidate values, and observing the
physical vane / EWPE app. This happens before the mapping is hard-coded into
`const.py` — Gree-family firmware has historically shipped small variations
in this range (e.g. some models omit the four intermediate fixed positions).

## Component changes

### `const.py`

- `PARAM_SWING_VERTICAL = "SwUpDn"`, `PARAM_SWING_HORIZONTAL = "SwingLfRig"`
- Value constants for each confirmed device state (named analogously to the
  existing `MODE_*` / `FAN_SPEED_*` constants)
- Both keys added to the list of columns polled by default (alongside
  `PHASE1_PARAMS`, without renaming that existing list, to avoid an
  unrelated rename churn)

### `device.py`

No changes needed — `get_status()` and `set_state()` already accept
arbitrary parameter keys.

### `climate.py`

- `SWING_MODE_TO_DEVICE` / `DEVICE_TO_SWING_MODE` and
  `SWING_HORIZONTAL_MODE_TO_DEVICE` / `DEVICE_TO_SWING_HORIZONTAL_MODE` dicts,
  following the existing `HVAC_MODE_TO_DEVICE` pattern
- `_attr_swing_modes` / `_attr_swing_horizontal_modes` class attributes
- `swing_mode` / `swing_horizontal_mode` properties reading from
  `self._data`, returning `None` when the key is absent or the raw value is
  unrecognised (same defensive pattern as `DEVICE_TO_HVAC_MODE.get(mode)`)
- `async_set_swing_mode` / `async_set_swing_horizontal_mode` methods sending
  `{PARAM_SWING_VERTICAL: value}` / `{PARAM_SWING_HORIZONTAL: value}` via the
  existing `_send()` helper
- `_attr_supported_features` extended with `SWING_MODE | SWING_HORIZONTAL_MODE`

## Error handling

Same pattern as every other property on this entity: a missing or
unrecognised raw value yields `None` (HA shows the attribute as unknown)
rather than raising. This matters here specifically because not every EWPE
unit supports both axes — a future user with a vertical-only unit will
simply see `swing_horizontal_mode` stay `None` instead of the entity
breaking.

## Testing strategy

- `tests/test_climate.py`: parametrised tests for `swing_mode` /
  `swing_horizontal_mode` property mapping (mirroring
  `test_modes_map_correctly`), plus `async_set_swing_mode` /
  `async_set_swing_horizontal_mode` emitting the right `set_state` call
  (mirroring `test_set_hvac_mode_heat_emits_pow_on_and_mode_heat`)
- Full existing suite (`pytest`) must keep passing
- Live verification against 192.168.40.11 is required before merging: both
  dropdowns on the HA climate card must visibly move the vane

## Rollout

1. Fork (`amandoippel/ewpe-smart-ha`) and local clone already set up, branch
   `feature/swing-controls`
2. Probe + bind against 192.168.40.11, confirm protocol version and current
   `SwUpDn`/`SwingLfRig` values are present in status replies
3. Determine confirmed value mapping interactively with the user
4. Implement `const.py` / `climate.py` changes + tests
5. Update `README.md` roadmap section
6. Install into the user's real HA instance for final live confirmation
7. Commit, push to fork; open a PR upstream to `anaryk/ewpe-smart-ha` if the
   user still wants to after seeing it work

## Open questions / future work

- 4-way independent cassette swing (deferred, needs different hardware to
  test against)
- Whether `SwingLfRig` is present at all on every split-unit model, or only
  on this user's — the defensive `None`-on-missing-key handling covers this
  regardless
