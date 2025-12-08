"""Unit conversion utilities for the Virtual Gas Meter integration."""
from .const import (
    UNIT_SYSTEM_METRIC,
    UNIT_SYSTEM_IMPERIAL,
    UNIT_CUBIC_METERS,
    UNIT_CCF,
    CCF_TO_M3,
    M3_TO_CCF,
)


def get_unit_label(unit_system: str) -> str:
    """Get the display unit label for a unit system."""
    if unit_system == UNIT_SYSTEM_IMPERIAL:
        return UNIT_CCF
    return UNIT_CUBIC_METERS


def to_display_unit(value: float, unit_system: str) -> float:
    """
    Convert a value from canonical storage (m³) to display unit.

    Args:
        value: Value in cubic meters (m³)
        unit_system: Target unit system (metric or imperial)

    Returns:
        Value converted to display unit (m³ or CCF)
    """
    if value is None:
        return 0.0

    if unit_system == UNIT_SYSTEM_IMPERIAL:
        # Convert m³ to CCF
        return value * M3_TO_CCF

    # Metric - no conversion needed
    return value


def to_canonical_unit(value: float, unit_system: str) -> float:
    """
    Convert a value from display unit to canonical storage (m³).

    Args:
        value: Value in display unit (m³ or CCF)
        unit_system: Source unit system (metric or imperial)

    Returns:
        Value converted to cubic meters (m³)
    """
    if value is None:
        return 0.0

    if unit_system == UNIT_SYSTEM_IMPERIAL:
        # Convert CCF to m³
        return value * CCF_TO_M3

    # Metric - no conversion needed
    return value


def get_default_precision(unit_system: str) -> int:
    """
    Get the default decimal precision for a unit system.

    Args:
        unit_system: The unit system (metric or imperial)

    Returns:
        Default precision: 3 for metric (m³), 2 for imperial (CCF)
    """
    if unit_system == UNIT_SYSTEM_IMPERIAL:
        return 2
    return 3


def format_gas_value(value: float, unit_system: str, precision: int = None) -> str:
    """
    Format a gas value with appropriate unit label.

    Args:
        value: Value in canonical unit (m³)
        unit_system: Display unit system
        precision: Decimal places (default: 3 for m³, 2 for CCF)

    Returns:
        Formatted string like "35.31 CCF" or "1.000 m³"
    """
    if precision is None:
        precision = get_default_precision(unit_system)
    display_value = to_display_unit(value, unit_system)
    unit_label = get_unit_label(unit_system)
    return f"{display_value:.{precision}f} {unit_label}"
