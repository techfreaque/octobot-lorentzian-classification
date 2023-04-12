import enum


class SpotMasterOrderTypes(enum.Enum):
    MARKET = "Market Orders"
    LIMIT = "Limit Orders"
    MANAGED_ORDER = "Order Manager Pro"
