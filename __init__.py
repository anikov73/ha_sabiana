"""The Sabiana Climate integration."""
import asyncio
from datetime import timedelta
from http.client import UNAUTHORIZED
import logging

from homeassistant.components.network import async_get_ipv4_broadcast_addresses
from homeassistant.helpers.dispatcher import async_dispatcher_send
from .bridge import DeviceDataUpdateCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .sabiana.sabiana import Sabiana
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

# from .bridge import DiscoveryService
from .const import COORDINATORS, DISPATCH_DEVICE_DISCOVERED, DISPATCHERS, DOMAIN, CLIENT

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up sabiana from a config entry."""
    session = async_get_clientsession(hass)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}
    hass.data[DOMAIN].setdefault(COORDINATORS, [])
    hass.data[DOMAIN].setdefault(DISPATCHERS, [])
    try:
        client = await hass.async_add_executor_job(
            lambda: Sabiana(
                username=entry.data[CONF_USERNAME],
                password=entry.data[CONF_PASSWORD],
                hass=hass,
            )
        )
        hass.data[DOMAIN][entry.entry_id][CLIENT] = client
    except KeyError as e:
        raise KeyError(f"Sabiana authorizarion failed")

    devices = await hass.async_add_executor_job(lambda: client.getDeviceForUserV2())
    client.devices = devices
    hass.data[DOMAIN][entry.entry_id]["devices"] = [
        DeviceDataUpdateCoordinator(hass, client, client.create_device(device))
        for device in devices
    ]
    _LOGGER.debug(f"Sabiana Devices {devices}")

    for device in hass.data[DOMAIN][entry.entry_id]["devices"]:
        hass.data[DOMAIN][COORDINATORS].append(device)
        async_dispatcher_send(hass, DISPATCH_DEVICE_DISCOVERED, device)

    tasks = [
        device.async_refresh()
        for device in hass.data[DOMAIN][entry.entry_id]["devices"]
    ]
    await asyncio.gather(*tasks)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if hass.data[DOMAIN].get(DISPATCHERS) is not None:
        for cleanup in hass.data[DOMAIN][DISPATCHERS]:
            cleanup()

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        hass.data[DOMAIN].pop(COORDINATORS, None)
        hass.data[DOMAIN].pop(DISPATCHERS, None)

    return unload_ok


# async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     """Set up Gree Climate from a config entry."""
#     hass.data.setdefault(DOMAIN, {})
#     gree_discovery = DiscoveryService(hass)
#     hass.data[DATA_DISCOVERY_SERVICE] = gree_discovery

#     hass.data[DOMAIN].setdefault(DISPATCHERS, [])
#     await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

#     async def _async_scan_update(_=None):
#         bcast_addr = list(await async_get_ipv4_broadcast_addresses(hass))
#         await gree_discovery.discovery.scan(0, bcast_ifaces=bcast_addr)

#     _LOGGER.debug("Scanning network for Gree devices")
#     await _async_scan_update()

#     hass.data[DOMAIN][DATA_DISCOVERY_INTERVAL] = async_track_time_interval(
#         hass, _async_scan_update, timedelta(seconds=DISCOVERY_SCAN_INTERVAL)
#     )

#     return True


# async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     """Unload a config entry."""
#     if hass.data[DOMAIN].get(DISPATCHERS) is not None:
#         for cleanup in hass.data[DOMAIN][DISPATCHERS]:
#             cleanup()

#     if hass.data[DOMAIN].get(DATA_DISCOVERY_INTERVAL) is not None:
#         hass.data[DOMAIN].pop(DATA_DISCOVERY_INTERVAL)()

#     if hass.data.get(DATA_DISCOVERY_SERVICE) is not None:
#         hass.data.pop(DATA_DISCOVERY_SERVICE)

#     unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

#     if unload_ok:
#         hass.data[DOMAIN].pop(COORDINATORS, None)
#         hass.data[DOMAIN].pop(DISPATCHERS, None)

#     return unload_ok
