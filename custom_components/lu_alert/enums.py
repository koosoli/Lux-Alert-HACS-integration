from enum import Enum

class Status(Enum):
    ACTUAL = "Actual"
    SYSTEM = "System"
    TEST = "Test"
    EXERCISE = "Exercise"

class MsgType(Enum):
    ACK = "Ack"
    ERROR = "Error"
    ALERT = "Alert"
    UPDATE = "Update"
    CANCEL = "Cancel"
    PAUSE = "Pause"
    RESUME = "Resume"

class Scope(Enum):
    PUBLIC = "Public"
    RESTRICTED = "Restricted"
    PRIVATE = "Private"

class Code(Enum):
    IN_ZONE = "In-zone"
    AREA_ENTRY = "Area-entry"
    AREA_LEAVE = "Area-leave"
    FOLLOW_UP = "Follow-up"
    ABROAD = "Abroad"
    SUBSCRIBER_BASE = "Subscriber-base"
    PAST_LOCATION = "Past Location"

class Category(Enum):
    GEO = "Geo"
    MET = "Met"
    SAFETY = "Safety"
    SECURITY = "Security"
    RESCUE = "Rescue"
    FIRE = "Fire"
    HEALTH = "Health"
    ENV = "Env"
    TRANSPORT = "Transport"
    INFRA = "Infra"
    CBRNE = "CBRNE"
    OTHER = "Other"

class Urgency(Enum):
    IMMEDIATE = "Immediate"
    EXPECTED = "Expected"
    FUTURE = "Future"
    PAST = "Past"
    UNKNOWN = "Unknown"

class Severity(Enum):
    EXTREME = "Extreme"
    SEVERE = "Severe"
    MODERATE = "Moderate"
    MINOR = "Minor"
    INFORMATION = "Information"
    TEST = "Test"
    UNKNOWN = "Unknown"

class Certainty(Enum):
    OBSERVED = "Observed"
    LIKELY = "Likely"
    POSSIBLE = "Possible"
    UNLIKELY = "Unlikely"
    UNKNOWN = "Unknown"

class Canal(Enum):
    SMS = "Sms"
    CELL_BROADCAST = "Cell-Broadcast"
    LED_SIGNS = "LED-signs"
    SIREN = "Siren"
    MOBILE_APP = "Mobile-App"
    TWITTER = "Twitter"
    FACEBOOK = "Facebook"
    WEBSITE_CHANNEL = "Website channel"
    EMAIL = "Email"

class RoamerSelection(Enum):
    INBOUND_ROAMERS = "INBOUND_ROAMERS"
    SUBSCRIBERS = "SUBSCRIBERS"
    INBOUND_ROAMERS_SUBSCRIBERS = "INBOUND ROAMERS SUBSCRIBERS"

class SirenSignalType(Enum):
    START = "0"
    END = "1"
