import enum


class LivePlottingModes(enum.Enum):
    DISABLE_PLOTTING = "disable live plotting"
    PLOT_RECORDING_MODE = "plot recording mode"
    REPLOT_VISIBLE_HISTORY = "replot visible history"


class BacktestPlottingModes(enum.Enum):
    DISABLE_PLOTTING = "disable backtest indicator plotting"
    ENABLE_PLOTTING = "enable backtest indicator plotting"


CURRENT_TIME_FRAME = "current time frame"


class TradingModeCommands:
    EXECUTE = "execute"
    ACTIVATE_REALTIME_STRATEGY = "activate_realtime_strategy"
    DISABLE_REALTIME_STRATEGY = "disable_realtime_strategy"
    SAVE = "save"
    INIT_CALL = "init_call"
    OHLC_CALLBACK = "ohlc_callback"
    KLINE_CALLBACK = "kline_callback"


class TradingSideKeys:
    LONG = "l"
    LONG_EXIT = "el"
    SHORT = "s"
    SHORT_EXIT = "es"


class TradingSidesNames:
    LONG_TITLE = "Long"
    LONG_EXIT_TITLE = "Long Exit"
    SHORT_TITLE = "Short"
    SHORT_EXIT_TITLE = "Short Exit"
    LONG = LONG_TITLE.lower()
    LONG_EXIT = LONG_EXIT_TITLE.lower()
    SHORT = SHORT_TITLE.lower()
    SHORT_EXIT = SHORT_EXIT_TITLE.lower()


class UserInputOtherSchemaValuesTypes(enum.Enum):
    DISPLAY_AS_TAB = "display_as_tab"  # used by octo ui2


class PriceDataSources(enum.Enum):
    """
    Default candle price str
    """

    TIME = "Time"
    CLOSE = "Close"
    OPEN = "Open"
    HIGH = "High"
    LOW = "Low"
    VOLUME = "Volume"
    LIVE = "Live"
    HL2 = "HL2"
    HLC3 = "HLC3"
    OHLC4 = "OHLC4"
    HEIKIN_ASHI_CLOSE = "Heikin Ashi close"
    HEIKIN_ASHI_OPEN = "Heikin Ashi open"
    HEIKIN_ASHI_HIGH = "Heikin Ashi high"
    HEIKIN_ASHI_LOW = "Heikin Ashi low"