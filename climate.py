"""Support for interface with a Gree climate systems."""
from __future__ import annotations

import logging
from typing import Any
from . import PLATFORMS


from homeassistant.components.climate import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    PRESET_NONE,
    PRESET_SLEEP,
    SWING_OFF,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_WHOLE,
    PRECISION_HALVES,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .bridge import DeviceDataUpdateCoordinator
from .const import COORDINATORS, DISPATCH_DEVICE_DISCOVERED, DISPATCHERS, DOMAIN

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = {
    "auto": HVACMode.AUTO,
    "cooling": HVACMode.COOL,
    "fan": HVACMode.FAN_ONLY,
    "heating": HVACMode.HEAT,
}
HVAC_MODES_REVERSE = {v: k for k, v in HVAC_MODES.items()}

PRESET_MODES = [
    PRESET_NONE,  # Default operating mode
    PRESET_SLEEP,  # Sleep mode
]

FAN_MODES = {
    0: FAN_AUTO,
    1: FAN_LOW,
    5: FAN_MEDIUM,
    10: FAN_HIGH,
}
FAN_MODES_REVERSE = {v: k for k, v in FAN_MODES.items()}

SWING_MODES = [SWING_OFF]


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Gree HVAC device from a config entry."""

    """Register the device."""
    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)
    async_add_entities(
        [
            SabianaClimateEntity(coordinator)
            for coordinator in hass.data[DOMAIN][COORDINATORS]
        ]
    )

    # for coordinator in hass.data[DOMAIN][COORDINATORS]:
    #     add_entities([SabianaClimateEntity(coordinator)])

    # hass.data[DOMAIN][DISPATCHERS].append(
    #     async_dispatcher_connect(hass, DISPATCH_DEVICE_DISCOVERED, init_device)
    # )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Gree HVAC device from a config entry."""
    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)
    async_add_entities(
        [
            SabianaClimateEntity(coordinator)
            for coordinator in hass.data[DOMAIN][COORDINATORS]
        ]
    )

    # @callback
    # def init_device(coordinator):
    #     """Register the device."""
    #     async_add_entities([SabianaClimateEntity(coordinator)])

    #     for coordinator in hass.data[DOMAIN][COORDINATORS]:
    #         init_device(coordinator)

    #     hass.data[DOMAIN][DISPATCHERS].append(
    #         async_dispatcher_connect(hass, DISPATCH_DEVICE_DISCOVERED, init_device)
    #     )


class SabianaClimateEntity(
    CoordinatorEntity[DeviceDataUpdateCoordinator], ClimateEntity
):
    """Representation of a Sabiana HVAC device."""

    _attr_precision = PRECISION_HALVES
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.PRESET_MODE
    )

    def __init__(self, coordinator: DeviceDataUpdateCoordinator) -> None:
        """Initialize the Gree device."""
        super().__init__(coordinator)
        self._name = coordinator.device.name
        self._mac = coordinator.device.id

    # async def async_update(self) -> None:
    #     await self.coordinator.async_request_refresh()

    # def icon(self):
    #     return "mdi:home-thermometer-outline"

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique id for the device."""
        return self._mac

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            manufacturer="Sabiana",
            name=self._name,
        )

    @property
    def temperature_unit(self) -> str:
        """Return the temperature units for the device."""
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self) -> float:
        """Return the reported current temperature for the device."""
        return self.coordinator.device.current_temp

    @property
    def target_temperature(self) -> float:
        """Return the target temperature for the device."""
        if self.coordinator.device.mode == "heating":
            return self.coordinator.device.heating_temp
        else:
            return self.coordinator.device.cooling_temp

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if ATTR_TEMPERATURE not in kwargs:
            raise ValueError(f"Missing parameter {ATTR_TEMPERATURE}")

        temperature = kwargs[ATTR_TEMPERATURE]
        _LOGGER.debug(
            "Setting temperature to %d for %s",
            temperature,
            self._name,
        )

        if self.coordinator.device.mode == "heating":
            # self.coordinator.device.heating_temp = round(temperature)
            self.coordinator.device.heating_temp = temperature
        else:
            self.coordinator.device.cooling_temp = temperature
        await self.coordinator.push_state_update()
        self.async_write_ha_state()

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature supported by the device."""
        return 10.0

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature supported by the device."""
        return 30.0

    # @property
    # def target_temperature_step(self) -> float:
    #     """Return the target temperature step support by the device."""
    #     return 0.5

    # @property
    # def target_temp_step(self) -> float:
    #     """Return the target temperature step support by the device."""
    #     return 0.5

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return the current HVAC mode for the device."""
        if not self.coordinator.device.on:
            return HVACMode.OFF
        return HVAC_MODES[self.coordinator.device.mode]
        # return HVAC_MODES.get(self.coordinator.device.mode)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode not in self.hvac_modes:
            raise ValueError(f"Invalid hvac_mode: {hvac_mode}")

        _LOGGER.debug(
            "Setting HVAC mode to %s for device %s",
            hvac_mode,
            self._name,
        )

        if hvac_mode == HVACMode.OFF:
            self.coordinator.device.on = False
            self.coordinator.device.mode = "off"
            await self.coordinator.push_state_update()
            self.async_write_ha_state()
            return

        if not self.coordinator.device.on:
            self.coordinator.device.on = True

        self.coordinator.device.mode = HVAC_MODES_REVERSE.get(hvac_mode)
        await self.coordinator.push_state_update()
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn on the device."""
        _LOGGER.debug("Turning on HVAC for device %s", self._name)

        self.coordinator.device.on = True
        await self.coordinator.push_state_update()
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn off the device."""
        _LOGGER.debug("Turning off HVAC for device %s", self._name)

        self.coordinator.device.on = False
        await self.coordinator.push_state_update()
        self.async_write_ha_state()

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the HVAC modes support by the device."""
        modes = [*HVAC_MODES_REVERSE]
        modes.append(HVACMode.OFF)
        return modes

    @property
    def preset_mode(self) -> str:
        """Return the current preset mode for the device."""
        if self.coordinator.device.night:
            return PRESET_SLEEP
        return PRESET_NONE

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode not in PRESET_MODES:
            raise ValueError(f"Invalid preset mode: {preset_mode}")

        _LOGGER.debug(
            "Setting preset mode to %s for device %s",
            preset_mode,
            self._name,
        )

        self.coordinator.device.night = False

        if preset_mode == PRESET_SLEEP:
            self.coordinator.device.night = True

        await self.coordinator.push_state_update()
        self.async_write_ha_state()

    @property
    def preset_modes(self) -> list[str]:
        """Return the preset modes support by the device."""
        return PRESET_MODES

    @property
    def fan_mode(self) -> str | None:
        """Return the current fan mode for the device."""
        speed = self.coordinator.device.fan
        return FAN_MODES.get(speed)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        if fan_mode not in FAN_MODES_REVERSE:
            raise ValueError(f"Invalid fan mode: {fan_mode}")

        self.coordinator.device.fan = FAN_MODES_REVERSE.get(fan_mode)
        await self.coordinator.push_state_update()
        self.async_write_ha_state()

    @property
    def fan_modes(self) -> list[str]:
        """Return the fan modes support by the device."""
        return [*FAN_MODES_REVERSE]

    @property
    def swing_mode(self) -> str:
        """Return the current swing mode for the device."""

        return SWING_OFF

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing operation."""

    @property
    def swing_modes(self) -> list[str]:
        """Return the swing modes currently supported for this device."""
        return SWING_MODES
