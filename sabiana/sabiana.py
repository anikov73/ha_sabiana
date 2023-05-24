import asyncio
import requests
import time
import logging
import socketio
import engineio

from homeassistant.core import HomeAssistant

logger = logging.getLogger(__name__)


class SabianaDevice(object):
    def __init__(
        self,
        name: str,
        id: str,
        heat_temp: float,
        cool_temp: float,
        on: bool,
        mode: str,
        night: bool,
        current_temp: float,
        fan: float,
    ) -> None:
        self.name = name
        self.id = id
        self.heat_temp = heat_temp
        self.cool_temp = cool_temp
        self.on = on
        self.mode = mode
        self.night = night
        self.current_temp = current_temp
        self.fan = fan


class Sabiana(object):
    """This class provides API calls to interact with the Blueair API."""

    def __init__(
        self,
        username: str,
        password: str,
        hass: HomeAssistant,
        auth_token: str = None,
        start_socketio=True,
    ) -> None:
        self.username = username
        self.password = password
        self.auth_token = auth_token
        self.devices = []
        self.hass = hass
        self.last_call_time = time.time()
        self.listeners = []

        if not self.auth_token:
            self.auth_token = self.get_auth_token()

        sio = socketio.Client(logger=True, engineio_logger=True)

        @sio.event
        def message(data):
            print("Received a message", data)

        @sio.on("MESSAGE")
        def on_message(data):
            print("I received a message!")

        @sio.on("*")
        def catch_all(event, data):
            print(data)
            for device in self.devices:
                if device["idDevice"] == data["device"]:
                    device["lastData"] = data["data"]
            for listener in self.listeners:
                if listener.device.id == data["device"]:
                    asyncio.run_coroutine_threadsafe(
                        listener.async_refresh(), hass.loop
                    )

        sio.connect("https://be-flex.sabianawm.cloud", auth={"token": self.auth_token})
        hass.async_add_executor_job(sio.wait)

    def addListener(self, object):
        self.listeners.append(object)

    def get_auth_token(self) -> str:
        return self.login(self.username, self.password)

    def debugResponse(self, response):
        if response.status_code == 200:
            # Request was successful
            print("request was successful.")
            print("Response:", response.json())
        else:
            # Request failed
            print("request failed.")
            print("Status Code:", response.status_code)

    def checkUser(self):
        url = (
            "https://be-standard.sabianawm.cloud/users/checkUser?email=" + self.username
        )
        response = requests.get(url)
        self.debugResponse(response)

    def login(self, username, password):
        url = "https://be-standard.sabianawm.cloud/users/login"
        payload = {"email": username, "password": password}
        response = requests.post(url, json=payload)
        self.debugResponse(response)

        if response.status_code == 200:
            return response.json()["body"]["user"]["token"]
        else:
            return None

    def checkUserAuth(self):
        url = "https://be-standard.sabianawm.cloud/users/checkUserAuth"
        headers = {"auth": self.auth_token}
        response = requests.get(url, headers=headers)
        self.debugResponse(response)

        if response.status_code == 200:
            return True
        else:
            return False

    def getDeviceForUserV2(self):
        url = "https://be-standard.sabianawm.cloud/devices/getDeviceForUserV2"
        headers = {"auth": self.auth_token}
        response = requests.get(url, headers=headers)
        self.debugResponse(response)

        if response.status_code == 200:
            return response.json()["body"]["devices"]
        else:
            return []

    async def asyncGetDeviceForUserV2(self):
        url = "https://be-standard.sabianawm.cloud/devices/getDeviceForUserV2"
        headers = {"auth": self.auth_token}
        response = requests.get(url, headers=headers)
        self.debugResponse(response)

        if response.status_code == 200:
            return response.json()["body"]["devices"]
        else:
            return None

    async def update_device(self, adevice, device):
        d = self.extractLastData(device["lastData"])
        adevice.mode = d["status"]
        adevice.heating_temp = d["heating_temp"]
        adevice.cooling_temp = d["cooling_temp"]
        adevice.current_temp = d["current_temp"]
        adevice.fan = d["fan"]
        adevice.fan_auto = d["fan_auto"] == 0
        adevice.night = d["night_mode"]
        adevice.on = d["on"]

    def create_device(self, device):
        d = self.extractLastData(device["lastData"])
        adevice = SabianaDevice(
            device["deviceName"],
            device["idDevice"],
            d["heating_temp"],
            d["cooling_temp"],
            d["on"],
            d["status"],
            d["night_mode"],
            d["current_temp"],
            d["fan"],
        )
        return adevice

    async def update_state(self, adevice):
        current_time = time.time()
        elapsed_time = current_time - self.last_call_time
        self.last_call_time = current_time
        if elapsed_time >= 50 or len(self.devices) == 0:
            self.devices = await self.hass.async_add_executor_job(
                self.asyncGetDeviceForUserV2
            )
        for device in self.devices:
            if device["idDevice"] == adevice.id:
                await self.update_device(adevice, device)
                # adevice.mode = device["mode"]
                # adevice.heating_temp = device["heating_temp"]
                # adevice.cooling_temp = device["cooling_temp"]
                # adevice.current_temp = device["current_temp"]
                # adevice.fan = device["fan"]
                # adevice.fan_auto = device["fan_auto"]
                # adevice.night = device["night"]
                # adevice.on = device["on"]

    async def devcmdDevice(self, device, hass):
        temp = 10
        if device.mode == "heating":
            temp = device.heating_temp
        else:
            temp = device.cooling_temp

        # asyncio.run_coroutine_threadsafe(
        #     self.devcmd2(
        #         device.id,
        #         self.packData(device.mode, temp, device.fan, device.night),
        #         hass,
        #     ),
        #     hass.loop,
        # )
        await hass.async_add_executor_job(
            self.devcmd,
            device.id,
            self.packData(device.mode, temp, device.fan, device.night),
        )
        # await self.devcmd2(
        #     device.id, self.packData(device.mode, temp, device.fan, device.night), hass
        # )

    async def devcmd2(self, device, data, hass):
        url = "https://be-standard.sabianawm.cloud/devices/cmd"
        payload = {"deviceID": device, "start": 2304, "data": data, "restart": False}
        headers = {"auth": self.auth_token}
        response = requests.post(url, json=payload, headers=headers)

        # response = await hass.async_add_executor_job(
        #     requests.post, **{"url": url, "json": payload, "headers": headers}
        # )

        # response = asyncio.run_coroutine_threadsafe(
        #     requests.post(url, json=payload, headers=headers), hass.loop
        # ).result()

        self.debugResponse(response)
        if response.status_code == 200:
            return True
        else:
            return False

    def devcmd(self, device, data):
        url = "https://be-standard.sabianawm.cloud/devices/cmd"
        payload = {"deviceID": device, "start": 2304, "data": data, "restart": False}
        headers = {"auth": self.auth_token}
        response = requests.post(url, json=payload, headers=headers)

        self.debugResponse(response)
        if response.status_code == 200:
            return True
        else:
            return False

    def packData(self, mode, temp, fan, night):
        d = {"cooling": "0", "heating": "1", "fan": "3", "auto": "2", "off": "4"}
        ms = d[mode]
        fs = (
            "04"
            if fan == 0
            else hex(int(fan * 10) + 10).replace("0x", "").upper().zfill(2)
        )

        ts = hex(int(temp * 10)).replace("0x", "").upper().zfill(3)

        ns = "2" if night else "0"
        s = fs + "0" + ms + "0" + ts + "FF00FFFF000" + ns
        print(s)
        return s

    def extractLastData(self, data):
        ret = dict()
        if len(data) != 80:
            return ret
        ret["status"] = {"0": "cooling", "1": "heating", "3": "fan"}[data[11]]
        ret["on"] = False if data[15] == "0" else True
        ret["heating_temp"] = int(data[29:32], 16) / 10.0
        ret["cooling_temp"] = int(data[25:28], 16) / 10.0
        ret["fan"] = (int(data[8:10], 16) - 10) / 10.0
        ret["fan_auto"] = False
        if ret["fan"] <= 0:
            ret["fan_auto"] = True
            ret["fan"] = 0
        ret["current_temp"] = int(data[21:24], 16) / 10.0
        ret["night_mode"] = True if int(data[14], 16) >= 10 else False
        print(ret)
        return ret


# checkUser('aleksandar.nikov@gmail.com')
# token = login('aleksandar.nikov@gmail.com', '_Hannson33')
# print(token)

# token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySUQiOiJsYTIyQVNsaURwcHJ4SXdxaW5BMyIsImVtYWlsIjoiYWxla3NhbmRhci5uaWtvdkBnbWFpbC5jb20iLCJhZG1pbiI6ZmFsc2UsImZ3QmV0YSI6ZmFsc2UsImlhdCI6MTY4NDYyOTYzNiwiZXhwIjoxNzAwMTgxNjM2fQ.iq4oZk9H7dgBezcsQypzqbtISpR4bTSSVHHwVBdJskw'
# checkUserAuth(token)

# devcmd('swm-1097BDA4C056', token, packData('off', 29.0, 0, True))
# time.sleep(3)

# devices = getDeviceForUserV2(token)
# for device in devices:
#     if device['idDevice'] == 'swm-1097BDA4C056':
#         print(device['lastData'])
#         print(extractLastData(device['lastData']))
