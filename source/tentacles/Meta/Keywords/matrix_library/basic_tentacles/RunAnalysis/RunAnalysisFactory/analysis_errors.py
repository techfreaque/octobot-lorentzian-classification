class CandlesLoadingError(Exception):
    """
    raised when unable to load candles
    """


class LiveMetaDataNotInitializedError(Exception):
    """
    raised when the live metadata isnt initialized yet
    """
