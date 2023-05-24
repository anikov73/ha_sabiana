"""Helper and wrapper classes for Sabiana module."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .sabiana.sabiana import Sabiana
from . import sabiana

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class DeviceDataUpdateCoordinator(DataUpdateCoordinator):
    """Manages polling for state changes from the device."""

    def __init__(
        self, hass: HomeAssistant, client: Sabiana, device: sabiana.SabianaDevice
    ) -> None:
        """Initialize the data update coordinator."""
        DataUpdateCoordinator.__init__(
            self,
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{device.name}",
            update_interval=timedelta(seconds=60),
            # update_method=self.update_tick,
        )
        self.device = device
        self._error_count = 0
        self.client = client
        self.hass = hass
        self.client.addListener(self)

    async def _async_update_data(self):
        try:
            await self.client.update_state(self.device)
            await self.async_request_refresh()
            # await self.async_write_ha_state()
        except Exception as ex:
            pass
        # if len(self.client.devices) == 0:
        #     self.client.devices = self.client.getDeviceForUserV2()
        # for device in self.client.devices:
        #     if device["idDevice"] == self.client.device.id:
        #         self.client.device.mode = device["mode"]
        #         self.client.device.heating_temp = device["heating_temp"]
        #         self.client.device.cooling_temp = device["cooling_temp"]
        #         self.client.device.current_temp = device["current_temp"]
        #         self.client.device.fan = device["fan"]
        #         self.client.device.fan_auto = device["fan_auto"]
        #         self.client.device.night = device["night"]
        #         self.client.device.on = device["on"]
        # except DeviceNotBoundError as error:
        #     raise UpdateFailed(f"Device {self.name} is unavailable") from error
        # except DeviceTimeoutError as error:
        #     self._error_count += 1

        # # Under normal conditions GREE units timeout every once in a while
        # if self.last_update_success and self._error_count >= MAX_ERRORS:
        #     _LOGGER.warning(
        #         "Device is unavailable: %s (%s)",
        #         self.name,
        #         self.device.device_info,
        #     )
        #     raise UpdateFailed(f"Device {self.name} is unavailable") from error

    async def push_state_update(self):
        """Send state updates to the physical device."""
        await self.client.devcmdDevice(self.device, self.hass)
        # try:
        #     return await self.device.push_state_update()
        # except DeviceTimeoutError:
        #     _LOGGER.warning(
        #         "Timeout send state update to: %s (%s)",
        #         self.name,
        #         self.device.device_info,
        #     )


# class DiscoveryService(Listener):
#     """Discovery event handler for gree devices."""

#     def __init__(self, hass: HomeAssistant) -> None:
#         """Initialize discovery service."""
#         super().__init__()
#         self.hass = hass

#         self.discovery = Discovery(DISCOVERY_TIMEOUT)
#         self.discovery.add_listener(self)

#         hass.data[DOMAIN].setdefault(COORDINATORS, [])

#     async def device_found(self, device_info: DeviceInfo) -> None:
#         """Handle new device found on the network."""

#         device = Device(device_info)
#         try:
#             await device.bind()
#         except DeviceNotBoundError:
#             _LOGGER.error("Unable to bind to gree device: %s", device_info)
#         except DeviceTimeoutError:
#             _LOGGER.error("Timeout trying to bind to gree device: %s", device_info)

#         _LOGGER.info(
#             "Adding Gree device %s at %s:%i",
#             device.device_info.name,
#             device.device_info.ip,
#             device.device_info.port,
#         )
#         coordo = DeviceDataUpdateCoordinator(self.hass, device)
#         self.hass.data[DOMAIN][COORDINATORS].append(coordo)
#         await coordo.async_refresh()

#         async_dispatcher_send(self.hass, DISPATCH_DEVICE_DISCOVERED, coordo)

#     async def device_update(self, device_info: DeviceInfo) -> None:
#         """Handle updates in device information, update if ip has changed."""
#         for coordinator in self.hass.data[DOMAIN][COORDINATORS]:
#             if coordinator.device.device_info.mac == device_info.mac:
#                 coordinator.device.device_info.ip = device_info.ip
#                 await coordinator.async_refresh()
