"""Button platform for Sharp Cocoro Air: cancel eco.

The counterpart to the read-only eco sensor. Writing 42 to `8F` puts the unit back into
通常動作中 and does apply; writing 41 does not, which is why this is a one-way button
rather than half of a switch. See binary_sensor.py for the measurements.
"""

import logging

from sharp_cocoro import Cocoro
from sharp_cocoro.properties import SinglePropertyStatus

from . import SharpCocoroData
from .const import DOMAIN
from .coordinator import execute_and_refresh as shared_execute_and_refresh

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

STATUS_CODE_ECO = "8F"
ECO_ON = "41"
ECO_OFF = "42"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the cancel-eco button for every device that reports the property."""
    cocoro_data = entry.runtime_data
    assert isinstance(cocoro_data, SharpCocoroData)

    entities = [
        SharpCocoroCancelEcoButton(cocoro_data, index)
        for index, device in enumerate(cocoro_data.devices)
        if device.get_property_status(STATUS_CODE_ECO) is not None
    ]
    async_add_entities(entities)


class SharpCocoroCancelEcoButton(ButtonEntity):
    """Take the unit out of its power-saving mode."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:leaf-off"

    def __init__(self, cocoro_data: SharpCocoroData, device_index: int) -> None:
        """Initialize the button."""
        self._cocoro_data = cocoro_data
        self._device_index = device_index
        self._attr_unique_id = f"{self._device.device_id}_cancel_eco"
        self._attr_name = "Cancel eco"
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

    def _code(self) -> str | None:
        status = self._device.get_property_status(STATUS_CODE_ECO)
        if isinstance(status, SinglePropertyStatus):
            return status.valueSingle.get("code")
        return None

    async def async_press(self) -> None:
        """Write 42, but only when there is something to cancel."""
        if self._code() != ECO_ON:
            _LOGGER.info("Eco is already off on %s, nothing to cancel", self._device.name)
            return
        self._device.queue_property_status_update(
            SinglePropertyStatus(STATUS_CODE_ECO, {"code": ECO_OFF})
        )
        await shared_execute_and_refresh(
            device=self._device,
            cocoro=self._cocoro,
            cocoro_data=self._cocoro_data,
            debounced_refresh=self._cocoro_data.async_refresh_data,
            async_write_ha_state=lambda: None,
            entity_name="Sharp Cocoro Air Cancel eco",
        )
