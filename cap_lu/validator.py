from typing import List
from .models import Alert
from .enums import MsgType, Scope, Canal

def validate_alert(alert: Alert) -> List[str]:
    """
    Validates an Alert object against the CAP-LU specification rules.
    This checks for logical constraints, not XML validity.

    Args:
        alert: An instance of the Alert dataclass to validate.

    Returns:
        A list of string error messages. An empty list indicates the alert is valid.
    """
    errors = []

    # --- Top-level <alert> validation ---
    if not alert.identifier:
        errors.append("Alert 'identifier' is mandatory and cannot be empty.")
    if not alert.sender:
        errors.append("Alert 'sender' is mandatory and cannot be empty.")
    if not alert.sent:
        errors.append("Alert 'sent' is mandatory.")
    if not alert.status:
        errors.append("Alert 'status' is mandatory.")
    if not alert.msgType:
        errors.append("Alert 'msgType' is mandatory.")
    if not alert.scope:
        errors.append("Alert 'scope' is mandatory.")

    # CAP-LU specific rule for 'scope'
    if alert.scope != Scope.PUBLIC:
        errors.append(f"CAP-LU recommends 'scope' to be 'Public', but it is '{alert.scope.value}'.")

    # CAP-LU makes 'code' mandatory
    if not alert.code:
        errors.append("Alert 'code' is mandatory in CAP-LU and cannot be empty.")

    # Conditional rule for 'references'
    if alert.msgType in [MsgType.UPDATE, MsgType.CANCEL, MsgType.ACK, MsgType.ERROR] and not alert.references:
        errors.append(f"Alert 'references' is mandatory when 'msgType' is '{alert.msgType.value}'.")

    # --- <info> block validation ---
    if not alert.info:
        errors.append("Alert must contain at least one <info> block.")

    for i, info in enumerate(alert.info):
        prefix = f"Info block {i+1} ('{info.language}')"

        # Mandatory fields in <info>
        if not info.language:
            errors.append(f"Info block {i+1}: 'language' is mandatory.")
        if not info.category:
            errors.append(f"{prefix}: 'category' is mandatory and cannot be empty.")
        if not info.event:
            errors.append(f"{prefix}: 'event' is mandatory.")
        if not info.urgency:
            errors.append(f"{prefix}: 'urgency' is mandatory.")
        if not info.severity:
            errors.append(f"{prefix}: 'severity' is mandatory.")
        if not info.certainty:
            errors.append(f"{prefix}: 'certainty' is mandatory.")

        # --- <area> block validation ---
        if not info.area:
            errors.append(f"{prefix}: Must contain at least one <area> block.")

        for j, area in enumerate(info.area):
            area_prefix = f"{prefix}, Area {j+1} ('{area.areaDesc}')"
            if not area.areaDesc:
                errors.append(f"{prefix}, Area {j+1}: 'areaDesc' is mandatory.")

        # --- <parameter> validation (examples of conditional logic) ---
        # Check for mandatory parameters based on canal
        canals_in_info = [p.value for p in info.parameters if p.valueName == 'canal']

        if Canal.SMS.value in canals_in_info:
            if not any(p.valueName == 'roamer-selection' for p in info.parameters):
                errors.append(f"{prefix}: 'roamer-selection' parameter is mandatory for the 'Sms' canal.")

        if Canal.SIREN.value in canals_in_info:
            if not any(p.valueName == 'siren-signal-type' for p in info.parameters):
                errors.append(f"{prefix}: 'siren-signal-type' parameter is mandatory for the 'Siren' canal.")

        # Check for mandatory 'canal' and 'canal-id' parameters
        if not any(p.valueName == 'canal' for p in info.parameters):
            errors.append(f"{prefix}: The 'canal' parameter is mandatory in CAP-LU.")
        if not any(p.valueName == 'canal-id' for p in info.parameters):
            errors.append(f"{prefix}: The 'canal-id' parameter is mandatory in CAP-LU.")


    return errors
