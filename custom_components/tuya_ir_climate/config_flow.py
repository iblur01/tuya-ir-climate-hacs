"""Config flow for Tuya IR Climate."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import Platform
from homeassistant.helpers import selector

from .api import TuyaIRClimateAPI, TuyaIRClimateAuthError, TuyaIRClimateError
from .const import (
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_DELTA,
    CONF_DEVICE_NAME,
    CONF_FAN_AUTO,
    CONF_FAN_HIGH,
    CONF_FAN_LOW,
    CONF_INFRARED_ID,
    CONF_MIN_CYCLE,
    CONF_MODE_COOL,
    CONF_MODE_DRY,
    CONF_REGION,
    CONF_REMOTE_ID,
    CONF_SCAN_INTERVAL,
    CONF_TEMP_SENSOR,
    DEFAULT_DELTA,
    DEFAULT_INFRARED_ID,
    DEFAULT_MIN_CYCLE,
    DEFAULT_NAME,
    DEFAULT_REGION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_DELTA,
    MAX_MIN_CYCLE,
    MAX_SCAN_INTERVAL,
    MIN_DELTA,
    MIN_MIN_CYCLE,
    MIN_SCAN_INTERVAL,
    REGION_OPTIONS,
    TUYA_FAN_AUTO,
    TUYA_FAN_HIGH,
    TUYA_FAN_LOW,
    TUYA_MODE_COOL,
    TUYA_MODE_DRY,
)


class TuyaIRClimateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Tuya IR Climate setup through the UI."""

    VERSION = 1

    def __init__(self) -> None:
        self._base_data: dict[str, Any] = {}
        self._remotes: list[dict[str, Any]] = []

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return the options flow handler."""
        return TuyaIRClimateOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure Tuya Cloud credentials and discover IR remotes."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api = TuyaIRClimateAPI(
                user_input[CONF_API_KEY],
                user_input[CONF_API_SECRET],
                user_input[CONF_REGION],
                user_input[CONF_INFRARED_ID],
                "",
            )
            try:
                remotes = await self.hass.async_add_executor_job(api.get_remotes)
            except TuyaIRClimateAuthError:
                errors["base"] = "invalid_auth"
            except TuyaIRClimateError:
                errors["base"] = "cannot_connect"
            else:
                self._base_data = user_input
                self._remotes = remotes
                return await self.async_step_remote()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_NAME, default=DEFAULT_NAME): str,
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_API_SECRET): str,
                    vol.Required(CONF_REGION, default=DEFAULT_REGION): vol.In(
                        REGION_OPTIONS
                    ),
                    vol.Required(CONF_INFRARED_ID, default=DEFAULT_INFRARED_ID): str,
                }
            ),
            errors=errors,
        )

    async def async_step_remote(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Select the AC remote and configure Tuya value mapping."""
        if not self._base_data:
            return await self.async_step_user()

        errors: dict[str, str] = {}
        remote_options = {
            str(remote.get("remote_id")): (
                f"{remote.get('remote_name') or remote.get('remote_id')} "
                f"(category {remote.get('category_id')})"
            )
            for remote in self._remotes
            if remote.get("remote_id")
        }

        if not remote_options:
            errors["base"] = "no_remotes"

        if user_input is not None:
            data = {**self._base_data, **user_input}
            api = TuyaIRClimateAPI(
                data[CONF_API_KEY],
                data[CONF_API_SECRET],
                data[CONF_REGION],
                data[CONF_INFRARED_ID],
                data[CONF_REMOTE_ID],
            )
            try:
                await self.hass.async_add_executor_job(api.test_connection)
            except TuyaIRClimateError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{DOMAIN}_{data[CONF_REMOTE_ID]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=data[CONF_DEVICE_NAME],
                    data=data,
                    options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL.seconds},
                )

        default_remote_id = next(iter(remote_options), "")
        for remote in self._remotes:
            if str(remote.get("remote_name", "")).lower() == "air":
                default_remote_id = str(remote.get("remote_id"))
                break

        return self.async_show_form(
            step_id="remote",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REMOTE_ID, default=default_remote_id): vol.In(
                        remote_options
                    ),
                    vol.Required(CONF_TEMP_SENSOR): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=Platform.SENSOR,
                            device_class="temperature",
                        )
                    ),
                    vol.Required(CONF_MODE_COOL, default=TUYA_MODE_COOL): vol.Coerce(
                        int
                    ),
                    vol.Required(CONF_MODE_DRY, default=TUYA_MODE_DRY): vol.Coerce(int),
                    vol.Required(CONF_FAN_AUTO, default=TUYA_FAN_AUTO): vol.Coerce(int),
                    vol.Required(CONF_FAN_LOW, default=TUYA_FAN_LOW): vol.Coerce(int),
                    vol.Required(CONF_FAN_HIGH, default=TUYA_FAN_HIGH): vol.Coerce(int),
                }
            ),
            errors=errors,
        )


class TuyaIRClimateOptionsFlow(config_entries.OptionsFlow):
    """Handle Tuya IR Climate options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Configure polling options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self._config_entry.options
        current_interval = options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.seconds
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                    vol.Required(
                        CONF_DELTA,
                        default=options.get(CONF_DELTA, DEFAULT_DELTA),
                    ): vol.All(
                        vol.Coerce(float),
                        vol.Range(min=MIN_DELTA, max=MAX_DELTA),
                    ),
                    vol.Required(
                        CONF_MIN_CYCLE,
                        default=options.get(CONF_MIN_CYCLE, DEFAULT_MIN_CYCLE),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_MIN_CYCLE, max=MAX_MIN_CYCLE),
                    ),
                }
            ),
        )
