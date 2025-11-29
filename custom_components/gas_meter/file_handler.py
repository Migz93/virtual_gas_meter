"""File handler for gas meter data persistence using Home Assistant Store."""
import logging
from pathlib import Path
from datetime import datetime
from homeassistant.helpers.storage import Store
from .datetime_handler import string_to_datetime
from .gas_consume import GasConsume

_LOGGER = logging.getLogger(__name__)

# Storage configuration
STORAGE_VERSION = 1
STORAGE_KEY = "gas_meter_data"

# Legacy pickle file path (for migration)
def _get_legacy_pickle_path(hass):
    """Returns the path to the legacy pickle file."""
    return Path(hass.config.path("custom_components/gas_meter/gas_actualdata.pkl"))


def _datetime_to_iso(dt) -> str:
    """Convert datetime to ISO format string for JSON storage."""
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def _iso_to_datetime(iso_str: str) -> datetime:
    """Convert ISO format string back to datetime."""
    if isinstance(iso_str, datetime):
        return iso_str
    try:
        return datetime.fromisoformat(iso_str)
    except (ValueError, TypeError):
        # Fallback to string_to_datetime for other formats
        return string_to_datetime(iso_str)


def _serialize_records(gas_consume: GasConsume) -> list:
    """Convert GasConsume records to JSON-serializable format."""
    serialized = []
    for record in gas_consume:
        serialized_record = {}
        for key, value in record.items():
            if key == "datetime":
                serialized_record[key] = _datetime_to_iso(value)
            else:
                serialized_record[key] = value
        serialized.append(serialized_record)
    return serialized


def _deserialize_records(records: list) -> GasConsume:
    """Convert JSON records back to GasConsume object."""
    gas_consume = GasConsume()
    for record in records:
        deserialized_record = {}
        for key, value in record.items():
            if key == "datetime":
                deserialized_record[key] = _iso_to_datetime(value)
            else:
                deserialized_record[key] = value
        gas_consume.data.append(deserialized_record)
    return gas_consume


async def _migrate_from_pickle(hass) -> GasConsume | None:
    """Migrate data from legacy pickle file to JSON Store."""
    import pickle
    import aiofiles

    pickle_path = _get_legacy_pickle_path(hass)

    if not pickle_path.exists():
        return None

    try:
        _LOGGER.info("Found legacy pickle file, migrating to JSON storage...")

        # Read pickle data
        async with aiofiles.open(pickle_path, "rb") as file:
            data = await file.read()
            gas_consume = pickle.loads(data)

        # Backup the pickle file
        backup_path = pickle_path.with_suffix(".pkl.bak")
        pickle_path.rename(backup_path)
        _LOGGER.info(f"Legacy pickle file backed up to {backup_path}")

        _LOGGER.info(f"Successfully migrated {len(gas_consume)} records from pickle to JSON")
        return gas_consume

    except Exception as e:
        _LOGGER.error(f"Error migrating from pickle: {e}")
        return None


def _get_store(hass) -> Store:
    """Get or create the Store instance."""
    return Store(hass, STORAGE_VERSION, STORAGE_KEY)


async def save_gas_actualdata(gas_consume: GasConsume, hass):
    """Save gas consumption data using Home Assistant Store."""
    store = _get_store(hass)

    data = {
        "version": STORAGE_VERSION,
        "records": _serialize_records(gas_consume),
    }

    await store.async_save(data)
    _LOGGER.debug(f"Saved {len(gas_consume)} gas records to storage")


async def load_gas_actualdata(hass) -> GasConsume:
    """
    Load gas consumption data from Home Assistant Store.
    Automatically migrates from pickle if legacy file exists.
    """
    store = _get_store(hass)

    # Try to load from JSON Store
    data = await store.async_load()

    if data is not None:
        # Data exists in JSON Store
        records = data.get("records", [])
        gas_consume = _deserialize_records(records)
        _LOGGER.debug(f"Loaded {len(gas_consume)} gas records from storage")
        return gas_consume

    # No JSON data - check for legacy pickle file to migrate
    migrated_data = await _migrate_from_pickle(hass)
    if migrated_data is not None:
        # Save migrated data to new JSON Store
        await save_gas_actualdata(migrated_data, hass)
        return migrated_data

    # No data found anywhere - return empty GasConsume
    _LOGGER.debug("No existing gas data found, starting fresh")
    return GasConsume()
