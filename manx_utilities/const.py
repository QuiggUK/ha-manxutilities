"""Constants for the Manx Utilities integration."""
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

DOMAIN = "manx_utilities"

# Configuration constants
CONF_COST_RESOURCE_ID = "cost_resource_id"
CONF_ENERGY_RESOURCE_ID = "energy_resource_id"

# API Constants
API_ENDPOINT = "https://api.manxutilities.im/api/v0-1"
APPLICATION_ID = "8f56d0c3-351b-43aa-bf86-b49dbacd18dc"

# Other Constants
DEFAULT_SCAN_INTERVAL = 30
ATTR_LAST_READING_TIME = "last_reading_time"
ATTR_PERIOD = "period"