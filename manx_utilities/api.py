"""API client for Manx Utilities."""
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Literal
import aiohttp
from collections import deque

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
        self._last_valid_reading = None
        # Store readings with timestamps for historical tracking
        self._historical_values = {
            "cost": deque(maxlen=2880),  # 30 days of 30-minute readings
            "energy": deque(maxlen=2880)  # 30 days of 30-minute readings
        }

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

    def _get_time_range(self) -> Tuple[str, str]:
        """Get the appropriate time range for the current 30-minute period."""
        # Account for the 1-hour delay by looking back an hour
        now = datetime.utcnow() - timedelta(hours=1)
        
        # Determine which 30-minute period we're in
        if now.minute >= 30:
            # For the second half of the hour (30-59 minutes)
            from_time = now.replace(minute=30, second=0, microsecond=0)
            to_time = from_time + timedelta(minutes=29)
        else:
            # For the first half of the hour (0-29 minutes)
            from_time = now.replace(minute=0, second=0, microsecond=0)
            to_time = from_time + timedelta(minutes=29)
        
        # Format times as strings
        from_str = from_time.strftime("%Y-%m-%dT%H:%M:%S")
        to_str = to_time.strftime("%Y-%m-%dT%H:%M:%S")
        
        return from_str, to_str

    def get_historical_totals(self, reading_type: Literal["cost", "energy"]) -> dict:
        """Get historical totals for different time periods."""
        current_time = datetime.now()
        totals = {
            "total_today": 0.0,
            "total_7d": 0.0,
            "total_month": 0.0,
            "today_date": current_time.strftime("%d %B %Y"),
            "current_week": "",
            "current_month": current_time.strftime("%B %Y")
        }

        if not self._historical_values[reading_type]:
            return totals

        # Calculate today's total (midnight to now)
        today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate week start (Monday)
        week_start = current_time - timedelta(days=current_time.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=6)
        totals["current_week"] = f"{week_start.strftime('%d %b')} - {week_end.strftime('%d %b %Y')}"

        # Calculate month start
        month_start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Calculate totals
        for timestamp, value in self._historical_values[reading_type]:
            reading_time = datetime.fromtimestamp(timestamp)
            
            if reading_time >= today_start:
                totals["total_today"] += value
            
            if reading_time >= week_start:
                totals["total_7d"] += value
                
            if reading_time >= month_start:
                totals["total_month"] += value

        # Round totals
        totals["total_today"] = round(totals["total_today"], 3)
        totals["total_7d"] = round(totals["total_7d"], 3)
        totals["total_month"] = round(totals["total_month"], 3)

        return totals

    async def get_reading(self, reading_type: Literal["cost", "energy"]) -> Optional[Tuple[int, float]]:
        """Get the latest reading from the API for specified type."""
        if self._token is None:
            _LOGGER.debug("No token found, authenticating first")
            await self.authenticate()

        # Get the appropriate time range
        from_time, to_time = self._get_time_range()
        
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
            "period": "PT30M",
            "function": "sum"
        }

        _LOGGER.debug(
            "Requesting %s readings for period from %s to %s using resource_id: %s", 
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
                    if value > 0:  # Only store valid readings
                        self._historical_values[reading_type].append((timestamp, float(value)))
                        _LOGGER.debug("%s reading - Time: %s, Value: %s", 
                                    reading_type.capitalize(),
                                    datetime.fromtimestamp(timestamp), 
                                    value)
                        return timestamp, float(value)
                
                _LOGGER.warning("No valid readings found in response")
                return None

        except aiohttp.ClientError as err:
            _LOGGER.error("Network error while getting %s readings: %s", reading_type, str(err))
            raise

    async def close(self) -> None:
        """Close the API client."""
        if self._session:
            await self._session.close()
            self._session = None