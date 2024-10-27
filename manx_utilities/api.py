"""API client for Manx Utilities."""
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Literal
import aiohttp

from .const import API_ENDPOINT, APPLICATION_ID

_LOGGER = logging.getLogger(__name__)

class ManxUtilitiesAPI:
    """API client for Manx Utilities."""

    def __init__(self, username: str, password: str, cost_resource_id: str, energy_resource_id: str):
        """Initialize the API client."""
        self._username = username
        self._password = password
        self._cost_resource_id = cost_resource_id
        self._energy_resource_id = energy_resource_id
        self._token = None
        self._session = None

    async def authenticate(self) -> None:
        """Authenticate with the API."""
        if self._session is None:
            self._session = aiohttp.ClientSession()

        auth_url = f"{API_ENDPOINT}/auth"
        headers = {
            "applicationid": APPLICATION_ID,
            "content-type": "application/json"
        }
        data = {
            "username": self._username,
            "password": self._password
        }

        _LOGGER.debug("Attempting authentication to Manx Utilities API")
        try:
            async with self._session.post(auth_url, headers=headers, json=data) as response:
                _LOGGER.debug("Auth response status: %s", response.status)
                if response.status != 200:
                    response_text = await response.text()
                    _LOGGER.error(
                        "Authentication failed. Status: %s, Response: %s",
                        response.status,
                        response_text
                    )
                    raise Exception(f"Authentication failed: {response_text}")
                result = await response.json()
                self._token = result.get("token")
                _LOGGER.debug("Successfully authenticated with Manx Utilities API")
        except aiohttp.ClientError as err:
            _LOGGER.error("Network error during authentication: %s", str(err))
            raise

    async def get_latest_reading(self) -> Optional[Tuple[int, float]]:
        """Get the latest cost reading from the API (legacy method)."""
        _LOGGER.debug("Using get_latest_reading() to fetch cost data")
        return await self.get_reading("cost")

    async def get_reading(self, reading_type: Literal["cost", "energy"]) -> Optional[Tuple[int, float]]:
        """Get the latest reading from the API for specified type."""
        if self._token is None:
            _LOGGER.debug("No token found, authenticating first")
            await self.authenticate()

        # Get the current time and round down to the last hour
        now = datetime.utcnow()
        end_time = now.replace(minute=0, second=0, microsecond=0)
        
        # If we're at the start of an hour, get the previous hour
        if now.minute == 0 and now.second < 30:
            end_time = end_time - timedelta(hours=1)
        
        # For both cost and energy, we want the exact hour period
        from_time = end_time.strftime("%Y-%m-%dT%H:00:00")
        to_time = end_time.strftime("%Y-%m-%dT%H:59:59")

        resource_id = self._cost_resource_id if reading_type == "cost" else self._energy_resource_id
        
        readings_url = f"{API_ENDPOINT}/resource/{resource_id}/readings"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "applicationid": APPLICATION_ID,
            "content-type": "application/json"
        }
        
        params = {
            "from": from_time,
            "to": to_time,
            "period": "PT1H",  # Use PT1H for both cost and energy
            "offset": -60,
            "function": "sum"
        }

        _LOGGER.debug(
            "Requesting %s readings for hour from %s to %s using resource_id: %s", 
            reading_type,
            from_time,
            to_time,
            resource_id
        )

        try:
            async with self._session.get(readings_url, headers=headers, params=params) as response:
                _LOGGER.debug("Readings response status: %s", response.status)
                if response.status == 401:
                    _LOGGER.debug("Token expired, reauthenticating")
                    await self.authenticate()
                    # Retry the request with new token
                    headers["Authorization"] = f"Bearer {self._token}"
                    async with self._session.get(readings_url, headers=headers, params=params) as retry_response:
                        if retry_response.status != 200:
                            response_text = await retry_response.text()
                            _LOGGER.error(
                                "Failed to get readings after token refresh. Status: %s, Response: %s",
                                retry_response.status,
                                response_text
                            )
                            raise Exception(f"Failed to get readings: {response_text}")
                        data = await retry_response.json()
                elif response.status != 200:
                    response_text = await response.text()
                    _LOGGER.error(
                        "Failed to get readings. Status: %s, Response: %s",
                        response.status,
                        response_text
                    )
                    raise Exception(f"Failed to get readings: {response_text}")
                else:
                    data = await response.json()

                _LOGGER.debug("Received readings data: %s", data)
                
                if data.get("data") and len(data["data"]) > 0:
                    # Take just the timestamp and value, ignore any additional values
                    timestamp, value = data["data"][0][:2]
                    _LOGGER.debug("%s reading - Time: %s, Value: %s", 
                                reading_type.capitalize(),
                                datetime.fromtimestamp(timestamp), 
                                value)
                    return timestamp, value
                
                _LOGGER.warning("No readings found in response")
                return None

        except aiohttp.ClientError as err:
            _LOGGER.error("Network error while getting %s readings: %s", reading_type, str(err))
            raise

    async def close(self) -> None:
        """Close the API client."""
        if self._session:
            await self._session.close()
            self._session = None