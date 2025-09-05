"""Money and number formatting utilities."""

from typing import Union, Optional


def fmt_money(amount: Union[int, float, str, None]) -> str:
    """
    Format a monetary amount in Mexican Pesos (MXN).
    
    Args:
        amount: The amount to format (can be int, float, str, or None)
        
    Returns:
        Formatted string like "$1,234,567 MXN" or "$0 MXN" if invalid
        
    Examples:
        >>> fmt_money(1234567)
        '$1,234,567 MXN'
        >>> fmt_money("1234567.89")
        '$1,234,568 MXN'
        >>> fmt_money(None)
        '$0 MXN'
    """
    try:
        if amount is None:
            return "$0 MXN"
        
        # Convert to float first, then to int (rounds down)
        num_amount = int(float(str(amount).replace(',', '')))
        
        # Format with thousands separators
        formatted = f"{num_amount:,}"
        
        return f"${formatted} MXN"
    except (ValueError, TypeError):
        return "$0 MXN"


def maybe_num(value: Union[str, int, float, None]) -> Optional[float]:
    """
    Safely convert a value to a number (float).
    
    Args:
        value: The value to convert
        
    Returns:
        Float value if conversion is successful, None otherwise
        
    Examples:
        >>> maybe_num("123.45")
        123.45
        >>> maybe_num("not a number")
        None
        >>> maybe_num(None)
        None
    """
    if value is None:
        return None
    
    try:
        # Remove commas and convert to float
        return float(str(value).replace(',', ''))
    except (ValueError, TypeError):
        return None


def plural(count: int, singular: str, plural_form: str = None) -> str:
    """
    Return singular or plural form based on count.
    
    Args:
        count: The count to check
        singular: Singular form of the word
        plural_form: Plural form (if None, adds 's' to singular)
        
    Returns:
        Appropriate form based on count
        
    Examples:
        >>> plural(1, "recámara")
        'recámara'
        >>> plural(2, "recámara", "recámaras")
        'recámaras'
        >>> plural(0, "baño", "baños")
        'baños'
    """
    if count == 1:
        return singular
    
    if plural_form is None:
        return f"{singular}s"
    
    return plural_form


def m2(area: Union[int, float, str, None]) -> str:
    """
    Format area in square meters.
    
    Args:
        area: Area value to format
        
    Returns:
        Formatted string like "150 m²" or "0 m²" if invalid
        
    Examples:
        >>> m2(150.5)
        '151 m²'
        >>> m2("200")
        '200 m²'
        >>> m2(None)
        '0 m²'
    """
    try:
        if area is None:
            return "0 m²"
        
        # Convert to int (rounds down)
        area_int = int(float(str(area).replace(',', '')))
        
        return f"{area_int} m²"
    except (ValueError, TypeError):
        return "0 m²"
