"""Small Tuya Cloud API wrapper for infrared air conditioners."""

from __future__ import annotations

import logging
from typing import Any

import tinytuya

_LOGGER = logging.getLogger(__name__)


class TuyaIRClimateError(Exception):
    """Base Tuya IR Climate error."""


class TuyaIRClimateAuthError(TuyaIRClimateError):
    """Tuya Cloud authentication failed."""


class TuyaIRClimateAPI:
    """Tuya Cloud client for a universal IR hub and AC remote."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        region: str,
        infrared_id: str,
        remote_id: str,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.region = region
        self.infrared_id = infrared_id
        self.remote_id = remote_id
        self._cloud: tinytuya.Cloud | None = None

    def _client(self) -> tinytuya.Cloud:
        if self._cloud is None:
            self._cloud = tinytuya.Cloud(
                apiRegion=self.region,
                apiKey=self.api_key,
                apiSecret=self.api_secret,
                apiDeviceID=self.infrared_id,
            )
            if getattr(self._cloud, "error", None):
                raise TuyaIRClimateAuthError(str(self._cloud.error))
        return self._cloud

    def _request(
        self,
        url: str,
        *,
        action: str | None = None,
        post: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self._client().cloudrequest(url, action=action, post=post, query=query)
        if not isinstance(result, dict):
            raise TuyaIRClimateError(f"Unexpected Tuya response: {result!r}")
        if not result.get("success", False):
            code = result.get("code")
            msg = result.get("msg") or result.get("Error") or "unknown error"
            raise TuyaIRClimateError(f"Tuya request failed: {code} {msg}")
        return result

    def get_status(self) -> dict[str, int]:
        """Read Tuya cloud shadow status for the AC remote."""
        payload = self._request(f"/v1.0/devices/{self.remote_id}/status")
        status: dict[str, int] = {}
        for item in payload.get("result", []):
            try:
                status[str(item["code"])] = int(item["value"])
            except (KeyError, TypeError, ValueError):
                _LOGGER.debug("Ignoring unexpected Tuya status item: %s", item)
        return status

    def get_remotes(self) -> list[dict[str, Any]]:
        """Return remotes bound to the IR hub."""
        payload = self._request(f"/v2.0/infrareds/{self.infrared_id}/remotes")
        return list(payload.get("result", []))

    def test_connection(self) -> None:
        """Validate credentials, hub, remote, and status endpoint."""
        remotes = self.get_remotes()
        if not any(remote.get("remote_id") == self.remote_id for remote in remotes):
            raise TuyaIRClimateError("Remote ID is not bound to this infrared hub")
        status = self.get_status()
        if not {"power", "mode", "temp", "wind"}.issubset(status):
            raise TuyaIRClimateError("Remote status does not look like an AC")

    def send_command(self, code: str, value: int) -> None:
        """Send a single IR AC command."""
        self._request(
            f"/v2.0/infrareds/{self.infrared_id}/air-conditioners/{self.remote_id}/command",
            action="POST",
            post={"code": code, "value": value},
        )
