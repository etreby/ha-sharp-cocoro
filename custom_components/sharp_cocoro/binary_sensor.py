"""Binary sensor platform for Sharp Cocoro Air: eco, read-only on purpose.

`8F` is 節電動作設定, the unit's own power-saving mode -- 41 節電動作中, 42 通常動作中.

This is a sensor and not a switch because the cloud will not engage it. Writing 42 applies
and is offered as a button; writing 41 comes back HTTP 200 with a control id and a null
errorCode and is then ignored -- tried five times on 2026-08-20, including with the fan on
auto and through the FA state blob, and the unit stayed at 42 every time. The app has no
eco control either, so engaging it is a job for the infrared remote. A switch here would
silently fail to turn on, which is worse than an honest read-out.
"""

import logging

from sharp_cocoro.properties import SinglePropertyStatus

from . import SharpCocoroData
from .const import DOMAIN

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

STATUS_CODE_ECO = "8F"
ECO_ON = "41"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the eco sensor for every device that reports the property."""
    cocoro_data = entry.runtime_data
    assert isinstance(cocoro_data, SharpCocoroData)

    entities = [
        SharpCocoroEcoSensor(cocoro_data, index)
        for index, device in enumerate(cocoro_data.devices)
        if device.get_property_status(STATUS_CODE_ECO) is not None
    ]
    async_add_entities(entities)


class SharpCocoroEcoSensor(BinarySensorEntity):
    """Whether the unit is in its power-saving mode."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:leaf"

    def __init__(self, cocoro_data: SharpCocoroData, device_index: int) -> None:
        """Initialize the sensor."""
        self._cocoro_data = cocoro_data
        self._device_index = device_index
        self._attr_unique_id = f"{self._device.device_id}_eco"
        self._attr_name = "Eco"
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
        status = self._device.get_property_status(STATUS_CODE_ECO)
        if isinstance(status, SinglePropertyStatus):
            return status.valueSingle.get("code")
        return None

    @property
    def available(self) -> bool:
        """Unavailable rather than wrong when the unit stops reporting the property."""
        return self._code() is not None

    @property
    def is_on(self) -> bool | None:
        """True while the unit is saving power."""
        code = self._code()
        return None if code is None else code == ECO_ON
