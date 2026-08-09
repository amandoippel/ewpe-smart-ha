"""Climate entity for EWPE Smart air conditioners."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

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
from .coordinator import EwpeCoordinator

HVAC_MODE_TO_DEVICE: dict[HVACMode, int] = {
    HVACMode.AUTO: MODE_AUTO,
    HVACMode.COOL: MODE_COOL,
    HVACMode.DRY: MODE_DRY,
    HVACMode.FAN_ONLY: MODE_FAN,
    HVACMode.HEAT: MODE_HEAT,
}
DEVICE_TO_HVAC_MODE: dict[int, HVACMode] = {
    v: k for k, v in HVAC_MODE_TO_DEVICE.items()
}

FAN_MODE_TO_DEVICE: dict[str, int] = {
    FAN_AUTO: FAN_SPEED_AUTO,
    FAN_LOW: FAN_SPEED_LOW,
    FAN_MEDIUM: FAN_SPEED_MEDIUM,
    FAN_HIGH: FAN_SPEED_HIGH,
}
DEVICE_TO_FAN_MODE: dict[int, str] = {v: k for k, v in FAN_MODE_TO_DEVICE.items()}

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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register the climate entity for this config entry."""
    coordinator: EwpeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EwpeClimateEntity(coordinator, entry)])


class EwpeClimateEntity(CoordinatorEntity[EwpeCoordinator], ClimateEntity):
    """Climate entity backed by an :class:`EwpeDevice`."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.AUTO,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
    ]
    _attr_fan_modes = [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
    _attr_swing_modes = list(SWING_MODE_TO_DEVICE)
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.SWING_MODE
    )

    def __init__(self, coordinator: EwpeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        device = coordinator.device
        self._attr_unique_id = f"{device.mac}_climate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.mac or entry.entry_id)},
            name=device.name or entry.title,
            manufacturer=MANUFACTURER,
            model=device.info.get("model") if device.info else None,
            sw_version=device.info.get("ver") if device.info else None,
        )

    @property
    def _data(self) -> dict[str, int]:
        return self.coordinator.data or {}

    @property
    def hvac_mode(self) -> HVACMode | None:
        if self._data.get(PARAM_POWER) == POWER_OFF:
            return HVACMode.OFF
        mode = self._data.get(PARAM_MODE)
        if mode is None:
            return None
        return DEVICE_TO_HVAC_MODE.get(mode)

    @property
    def fan_mode(self) -> str | None:
        speed = self._data.get(PARAM_FAN_SPEED)
        if speed is None:
            return None
        return DEVICE_TO_FAN_MODE.get(speed)

    @property
    def swing_mode(self) -> str | None:
        value = self._data.get(PARAM_SWING_VERTICAL)
        if value is None:
            return None
        return DEVICE_TO_SWING_MODE.get(value)

    @property
    def target_temperature(self) -> float | None:
        value = self._data.get(PARAM_SET_TEMP)
        return float(value) if value is not None else None

    @property
    def current_temperature(self) -> float | None:
        value = self._data.get(PARAM_TEMP_SENSOR)
        if value is None:
            return None
        if not -10 <= value <= 60:
            return None
        return float(value)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._send({PARAM_POWER: POWER_OFF})
            return
        device_mode = HVAC_MODE_TO_DEVICE.get(hvac_mode)
        if device_mode is None:
            raise ValueError(f"Unsupported hvac_mode: {hvac_mode}")
        await self._send({PARAM_POWER: POWER_ON, PARAM_MODE: device_mode})

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        device_speed = FAN_MODE_TO_DEVICE.get(fan_mode)
        if device_speed is None:
            raise ValueError(f"Unsupported fan_mode: {fan_mode}")
        await self._send({PARAM_FAN_SPEED: device_speed})

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        device_value = SWING_MODE_TO_DEVICE.get(swing_mode)
        if device_value is None:
            raise ValueError(f"Unsupported swing_mode: {swing_mode}")
        await self._send({PARAM_SWING_VERTICAL: device_value})

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self._send({PARAM_SET_TEMP: int(round(float(temperature)))})

    async def async_turn_on(self) -> None:
        await self._send({PARAM_POWER: POWER_ON})

    async def async_turn_off(self) -> None:
        await self._send({PARAM_POWER: POWER_OFF})

    async def _send(self, params: dict[str, int]) -> None:
        await self.coordinator.device.set_state(params)
        await self.coordinator.async_request_refresh()
