"""Shared coordination logic for Sharp Cocoro Air integration."""

import asyncio
import logging
from typing import Any, Callable, Dict

from sharp_cocoro import Cocoro, Device

from . import SharpCocoroData

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)


async def execute_and_refresh(
    device: Device,
    cocoro: Cocoro,
    cocoro_data: SharpCocoroData,
    debounced_refresh: Callable,
    async_write_ha_state: Callable,
    entity_name: str = "Sharp Cocoro"
) -> None:
    """Execute queued updates and refresh device state.
    
    Args:
        device: The device to update
        cocoro: Cocoro API client
        cocoro_data: Shared data container
        debounced_refresh: Debounced refresh function
        async_write_ha_state: Function to update HA state
        entity_name: Name for logging purposes
    """
    _LOGGER.info(
        "Executing updates for %s: %s",
        entity_name,
        device.property_updates,
    )

    try:
        result = await cocoro.execute_queued_updates(device)
        
        # Extract control IDs from the response
        control_ids = []
        if 'controlList' in result:
            for control in result['controlList']:
                if 'id' in control:
                    control_ids.append(control['id'])
            _LOGGER.debug("Control IDs to monitor: %s", control_ids)

        # Immediately update Home Assistant state with optimistic values
        async_write_ha_state()
        _LOGGER.debug("Home Assistant state updated with optimistic values")

        # Wait for the cloud to confirm, but do it in the background.
        #
        # Awaiting this inside the service call is what "the AC hangs when taking a
        # command" was: six timed calls on 2026-08-19 blocked between 9.0 s and
        # 11.7 s each, because execute, confirm and refresh all happened before
        # Home Assistant answered the service. The optimistic state was already
        # written above, so the card reacts at once and the confirmation catches up.
        if control_ids:

            async def _confirm_and_refresh() -> None:
                try:
                    _LOGGER.debug("Waiting for control completion...")
                    # 30 s, not 5: the unit answers through Sharp's cloud and the
                    # confirmation regularly needs longer than five seconds.
                    completion_result = await cocoro.wait_for_control_completion(
                        device,
                        control_ids,
                        timeout=30.0,
                        poll_interval=1.0,
                    )
                    _LOGGER.debug("Controls completed successfully: %s", completion_result)
                    _LOGGER.debug("Refreshing device state after control completion")
                    await cocoro_data.async_refresh_data()
                except TimeoutError:
                    _LOGGER.warning(
                        "Control completion timed out, falling back to debounced refresh"
                    )
                    await debounced_refresh()
                except Exception as err:
                    # A 401 here used to be terminal: the re-login below covered
                    # execute_queued_updates only, so a token expiring between the
                    # command and its confirmation left the command unconfirmed --
                    # which is what "it did not take" looks like from the outside.
                    if "401" in str(err) or "unauthorized" in str(err).lower():
                        _LOGGER.info(
                            "Auth error while waiting for completion, re-logging in"
                        )
                        try:
                            await cocoro_data.async_login()
                            await cocoro_data.async_refresh_data()
                            return
                        except Exception as retry_error:
                            _LOGGER.error("Re-login after 401 failed: %s", retry_error)
                    else:
                        _LOGGER.error("Error waiting for control completion: %s", err)
                    await debounced_refresh()

            cocoro_data.hass.async_create_task(_confirm_and_refresh())
        else:
            # No control IDs, use debounced refresh as before
            await debounced_refresh()

    except Exception as e:
        _LOGGER.error("Failed to execute updates: %s", e)

        # Try to re-authenticate on authentication errors
        if (
            "401" in str(e)
            or "unauthorized" in str(e).lower()
            or "authentication" in str(e).lower()
        ):
            _LOGGER.info(
                "Authentication error during execute, attempting to re-login"
            )
            try:
                await cocoro_data.async_login()
                # Retry the operation after re-authentication
                await cocoro.execute_queued_updates(device)
                await debounced_refresh()
                _LOGGER.info(
                    "Successfully executed updates after re-authentication"
                )

            except Exception as retry_error:
                _LOGGER.error(
                    "Failed to execute updates after re-authentication: %s",
                    retry_error,
                )
                # Clear the queued updates to prevent them from piling up
                device.property_updates.clear()
        else:
            # For non-authentication errors, clear the queue to prevent issues
            _LOGGER.error(
                "Non-authentication error during execute, clearing update queue"
            )
            device.property_updates.clear()