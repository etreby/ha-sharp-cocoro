"""Switch platform for Sharp Cocoro Air: the ion / air-purifying mode.

`CF` is 空気清浄モード設定 on this unit -- 41 on, 42 off -- and unlike eco it is honoured
in both directions. Verified on 2026-08-20 by writing both values and watching the
unit's blue indicator go out and come back, so this is a real switch rather than a
hopeful one.

The entity is only created when the device actually reports CF. Half the properties this
unit advertises as settable read null and ignore writes, so presence of a value is the
only trustworthy test.
"""

import logging

from sharp_cocoro import Cocoro
from sharp_cocoro.properties import SinglePropertyStatus

from . import SharpCocoroData
from .const import DOMAIN
from .coordinator import execute_and_refresh as shared_execute_and_refresh

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

STATUS_CODE_ION = "CF"
ION_ON = "41"
ION_OFF = "42"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the ion switch for every device that reports the property."""
    cocoro_data = entry.runtime_data
    assert isinstance(cocoro_data, SharpCocoroData)

    entities = []
    for index, device in enumerate(cocoro_data.devices):
        if device.get_property_status(STATUS_CODE_ION) is not None:
            entities.append(SharpCocoroIonSwitch(cocoro_data, index))
        else:
            _LOGGER.info("Device %s reports no CF, so no ion switch", device.device_id)
    async_add_entities(entities)


class SharpCocoroIonSwitch(SwitchEntity):
    """The unit's ion / air-purifying mode."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:air-purifier"

    def __init__(self, cocoro_data: SharpCocoroData, device_index: int) -> None:
        """Initialize the switch."""
        self._cocoro_data = cocoro_data
        self._device_index = device_index
        self._attr_unique_id = f"{self._device.device_id}_ion"
        # has_entity_name is True, so Home Assistant prefixes the device name
        # itself. Passing it again is what produced "Living Room AC Living
        # room Ion" on first install.
        self._attr_name = "Ion"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(self._device.device_id))},
            name=self._device.name,
            manufacturer=self._device.maker,
            model=self._device.model,
            serial_number=self._device.serial_number,
        )

    @property
    def _device(self):
        return self._cocoro_data.devices[self._device_index]

    @property
    def _cocoro(self) -> Cocoro:
        return self._cocoro_data.cocoro

    async def async_added_to_hass(self) -> None:
        """Follow the coordinator's refreshes."""
        await super().async_added_to_hass()
        self._remove_listener = self.hass.bus.async_listen(
            "sharp_cocoro.device_updated", self._handle_device_update
        )

    async def _handle_device_update(self, event) -> None:
        if event.data.get("device_id") == self._device.device_id:
            self.async_write_ha_state()

    def _code(self) -> str | None:
        status = self._device.get_property_status(STATUS_CODE_ION)
        if isinstance(status, SinglePropertyStatus):
            return status.valueSingle.get("code")
        return None

    @property
    def available(self) -> bool:
        """Unavailable rather than wrong when the unit stops reporting the property."""
        return self._code() is not None

    @property
    def is_on(self) -> bool | None:
        """True while the ion mode is running."""
        code = self._code()
        return None if code is None else code == ION_ON

    async def _write(self, code: str) -> None:
        self._device.queue_property_status_update(
            SinglePropertyStatus(STATUS_CODE_ION, {"code": code})
        )
        await shared_execute_and_refresh(
            device=self._device,
            cocoro=self._cocoro,
            cocoro_data=self._cocoro_data,
            debounced_refresh=self._cocoro_data.async_refresh_data,
            async_write_ha_state=self.async_write_ha_state,
            entity_name="Sharp Cocoro Air Ion",
        )

    async def async_turn_on(self, **kwargs) -> None:
        """Start the ion mode."""
        await self._write(ION_ON)

    async def async_turn_off(self, **kwargs) -> None:
        """Stop the ion mode."""
        await self._write(ION_OFF)
