"""Tests for the climate entity state mapping and command emission."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    HVACMode,
)

from custom_components.ewpe_smart.climate import EwpeClimateEntity
from custom_components.ewpe_smart.const import (
    PARAM_FAN_SPEED,
    PARAM_MODE,
    PARAM_POWER,
    PARAM_SET_TEMP,
    PARAM_SWING_HORIZONTAL,
    PARAM_SWING_VERTICAL,
)


def _make_entity(status: dict[str, int]) -> tuple[EwpeClimateEntity, MagicMock]:
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

    entity = EwpeClimateEntity(coordinator, entry)
    return entity, device


def test_power_off_maps_to_hvac_off() -> None:
    entity, _ = _make_entity({"Pow": 0, "Mod": 1})
    assert entity.hvac_mode == HVACMode.OFF


@pytest.mark.parametrize(
    ("device_mode", "expected"),
    [
        (0, HVACMode.AUTO),
        (1, HVACMode.COOL),
        (2, HVACMode.DRY),
        (3, HVACMode.FAN_ONLY),
        (4, HVACMode.HEAT),
    ],
)
def test_modes_map_correctly(device_mode: int, expected: HVACMode) -> None:
    entity, _ = _make_entity({"Pow": 1, "Mod": device_mode})
    assert entity.hvac_mode == expected


@pytest.mark.parametrize(
    ("speed", "expected"),
    [(0, FAN_AUTO), (1, FAN_LOW), (3, FAN_MEDIUM), (5, FAN_HIGH)],
)
def test_fan_modes_map_correctly(speed: int, expected: str) -> None:
    entity, _ = _make_entity({"Pow": 1, "Mod": 1, "WdSpd": speed})
    assert entity.fan_mode == expected


def test_target_and_current_temperature() -> None:
    entity, _ = _make_entity({"Pow": 1, "Mod": 1, "SetTem": 23, "TemSen": 25})
    assert entity.target_temperature == 23.0
    assert entity.current_temperature == 25.0


def test_implausible_temp_sensor_is_none() -> None:
    entity, _ = _make_entity({"Pow": 1, "Mod": 1, "TemSen": -50})
    assert entity.current_temperature is None


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


@pytest.mark.asyncio
async def test_set_temperature_emits_set_tem() -> None:
    entity, device = _make_entity({"Pow": 1, "Mod": 1, "SetTem": 22})
    await entity.async_set_temperature(temperature=24)
    device.set_state.assert_awaited_once_with({PARAM_SET_TEMP: 24})


@pytest.mark.asyncio
async def test_set_hvac_mode_off_emits_pow_zero() -> None:
    entity, device = _make_entity({"Pow": 1, "Mod": 1})
    await entity.async_set_hvac_mode(HVACMode.OFF)
    device.set_state.assert_awaited_once_with({PARAM_POWER: 0})


@pytest.mark.asyncio
async def test_set_hvac_mode_heat_emits_pow_on_and_mode_heat() -> None:
    entity, device = _make_entity({"Pow": 0})
    await entity.async_set_hvac_mode(HVACMode.HEAT)
    device.set_state.assert_awaited_once_with({PARAM_POWER: 1, PARAM_MODE: 4})


@pytest.mark.asyncio
async def test_set_fan_mode_high_emits_wdspd_5() -> None:
    entity, device = _make_entity({"Pow": 1, "Mod": 1})
    await entity.async_set_fan_mode(FAN_HIGH)
    device.set_state.assert_awaited_once_with({PARAM_FAN_SPEED: 5})


@pytest.mark.asyncio
async def test_turn_on_off_shortcuts() -> None:
    entity, device = _make_entity({"Pow": 0})
    await entity.async_turn_on()
    device.set_state.assert_awaited_with({PARAM_POWER: 1})
    await entity.async_turn_off()
    device.set_state.assert_awaited_with({PARAM_POWER: 0})


@pytest.mark.asyncio
async def test_set_swing_mode_emits_swupdn() -> None:
    entity, device = _make_entity({"Pow": 1, "Mod": 1, "SwUpDn": 0})
    await entity.async_set_swing_mode("Fixed - lowest")
    device.set_state.assert_awaited_once_with({PARAM_SWING_VERTICAL: 6})


@pytest.mark.asyncio
async def test_set_swing_horizontal_mode_emits_swinglfrig() -> None:
    entity, device = _make_entity({"Pow": 1, "Mod": 1, "SwingLfRig": 0})
    await entity.async_set_swing_horizontal_mode("Fixed - rightmost")
    device.set_state.assert_awaited_once_with({PARAM_SWING_HORIZONTAL: 6})
