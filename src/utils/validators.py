import re


def validate_phone(phone: str) -> bool:
    """Validate Belarus phone number (+375, 375, or local 0)"""
    # Remove spaces and dashes
    phone_clean = phone.replace(' ', '').replace('-', '')

    # Belarus format: +375XXXXXXXXX or 375XXXXXXXXX or 0XXXXXXXXX (local)
    belarus_with_plus = r'^\+375\d{9}$'
    belarus_without_plus = r'^375\d{9}$'
    local_pattern = r'^0\d{9}$'

    return bool(re.match(belarus_with_plus, phone_clean) or
                re.match(belarus_without_plus, phone_clean) or
                re.match(local_pattern, phone_clean))


def normalize_phone(phone: str) -> str:
    """Convert phone to standard Belarus format +375XXXXXXXXX"""
    phone_clean = phone.replace(' ', '').replace('-', '')

    if phone_clean.startswith('+375'):
        return phone_clean
    elif phone_clean.startswith('375'):
        return '+' + phone_clean
    elif phone_clean.startswith('0'):
        return '+375' + phone_clean[1:]

    return phone_clean


def validate_name(name: str) -> bool:
    """Validate full name (min 2 chars, letters and spaces)"""
    name_clean = name.strip()
    return len(name_clean) >= 2 and all(c.isalpha() or c.isspace() for c in name_clean)
