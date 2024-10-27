"""Platform for sensor integration."""
from datetime import datetime, timedelta
import logging
from collections import deque
import calendar

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    UnitOfEnergy,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    ATTR_LAST_READING_TIME,
    ATTR_PERIOD,
    CONF_COST_RESOURCE_ID,
    CONF_ENERGY_RESOURCE_ID,
)
from .api import ManxUtilitiesAPI

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=30)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Manx Utilities sensors."""
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    cost_resource_id = config_entry.data[CONF_COST_RESOURCE_ID]
    energy_resource_id = config_entry.data[CONF_ENERGY_RESOURCE_ID]

    api = ManxUtilitiesAPI(username, password, cost_resource_id, energy_resource_id)
    
    async_add_entities(
        [
            ManxUtilitiesCostSensor(api, username),
            ManxUtilitiesEnergySensor(api, username),
        ],
        True,
    )

class ManxUtilitiesBaseSensor(SensorEntity):
    """Base class for Manx Utilities sensors."""

    def __init__(self, api: ManxUtilitiesAPI, username: str) -> None:
        """Initialize the base sensor."""
        self._api = api
        self._attr_available = True
        self._last_timestamp = None
        self._historical_values = deque(maxlen=2880)  # Store 30 days of 30-minute readings
        self._attr_extra_state_attributes = {
            ATTR_LAST_READING_TIME: None,
            ATTR_PERIOD: "30 minutes",
            "total_today": 0.0,
            "total_7d": 0.0,
            "total_month": 0.0,
            "today_date": "",
            "current_week": "",
            "current_month": "",
        }

    def _update_historical_values(self, value: float, timestamp: int) -> None:
        """Update historical values and calculate totals for different periods."""
        current_time = datetime.fromtimestamp(timestamp)
        
        # Add new value
        self._historical_values.append((timestamp, value))
        
        # Calculate different period totals
        self._calculate_today_total(current_time)
        self._calculate_week_total(current_time)
        self._calculate_month_total(current_time)

    def _calculate_today_total(self, current_time: datetime) -> None:
        """Calculate total for today (midnight to midnight)."""
        today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        total = sum(
            value for ts, value in self._historical_values
            if datetime.fromtimestamp(ts) >= today_start
        )
        
        self._attr_extra_state_attributes["total_today"] = round(total, 3)
        self._attr_extra_state_attributes["today_date"] = today_start.strftime("%d %B %Y")

    def _calculate_week_total(self, current_time: datetime) -> None:
        """Calculate total for current week (Monday-Sunday)."""
        # Get the start of the current week (Monday)
        week_start = current_time - timedelta(days=current_time.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=6)
        
        total = sum(
            value for ts, value in self._historical_values
            if datetime.fromtimestamp(ts) >= week_start
        )
        
        self._attr_extra_state_attributes["total_7d"] = round(total, 3)
        # Format: "22 Jan - 28 Jan 2024"
        self._attr_extra_state_attributes["current_week"] = f"{week_start.strftime('%d %b')} - {week_end.strftime('%d %b %Y')}"

    def _calculate_month_total(self, current_time: datetime) -> None:
        """Calculate total for current month."""
        # Get the start of the current month
        month_start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        total = sum(
            value for ts, value in self._historical_values
            if datetime.fromtimestamp(ts) >= month_start
        )
        
        self._attr_extra_state_attributes["total_month"] = round(total, 3)
        self._attr_extra_state_attributes["current_month"] = current_time.strftime("%B %Y")

class ManxUtilitiesCostSensor(ManxUtilitiesBaseSensor):
    """Representation of a Manx Utilities cost sensor."""

    _attr_has_entity_name = True
    _attr_name = "Electricity Cost"
    _attr_suggested_display_precision = 2
    _attr_native_unit_of_measurement = "GBP"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:currency-gbp"

    def __init__(self, api: ManxUtilitiesAPI, username: str) -> None:
        """Initialize the sensor."""
        super().__init__(api, username)
        self._attr_unique_id = f"manx_utilities_cost_{username}"

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        try:
            reading_data = await self._api.get_reading("cost")
            if reading_data and len(reading_data) >= 2:
                timestamp, cost_pence = reading_data
                cost_pounds = round(float(cost_pence) / 100, 2)
                self._attr_native_value = cost_pounds
                self._update_historical_values(cost_pounds, timestamp)
                reading_time = datetime.fromtimestamp(timestamp)
                self._attr_extra_state_attributes[ATTR_LAST_READING_TIME] = reading_time.isoformat()
                self._attr_available = True
            else:
                self._attr_available = False
        except Exception as error:
            _LOGGER.error("Error updating cost sensor: %s", error)
            self._attr_available = False

class ManxUtilitiesEnergySensor(ManxUtilitiesBaseSensor):
    """Representation of a Manx Utilities energy sensor."""

    _attr_has_entity_name = True
    _attr_name = "Electricity Usage"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:lightning-bolt"

    def __init__(self, api: ManxUtilitiesAPI, username: str) -> None:
        """Initialize the sensor."""
        super().__init__(api, username)
        self._attr_unique_id = f"manx_utilities_energy_{username}"

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        try:
            reading_data = await self._api.get_reading("energy")
            if reading_data and len(reading_data) >= 2:
                timestamp, energy_kwh = reading_data
                energy_value = round(float(energy_kwh), 3)
                self._attr_native_value = energy_value
                self._update_historical_values(energy_value, timestamp)
                reading_time = datetime.fromtimestamp(timestamp)
                self._attr_extra_state_attributes[ATTR_LAST_READING_TIME] = reading_time.isoformat()
                self._attr_available = True
            else:
                self._attr_available = False
        except Exception as error:
            _LOGGER.error("Error updating energy sensor: %s", error)
            self._attr_available = False