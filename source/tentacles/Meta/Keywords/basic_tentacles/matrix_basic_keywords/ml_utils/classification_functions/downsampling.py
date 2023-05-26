
import typing

def no_down_sampler(candles_back: int, only_train_on_every_x_bars: int) -> bool:
    return candles_back % 4


def skip_every_x_down_sampler(
    candles_back: int, only_train_on_every_x_bars: int
) -> bool:
    return candles_back % only_train_on_every_x_bars


def use_every_x_down_sampler(
    candles_back: int, only_train_on_every_x_bars: int
) -> bool:
    return not (candles_back % only_train_on_every_x_bars)


class DownSamplers:
    SKIP_EVERY_X_DOWN_SAMPLER: str = (
        "Skip every x candles down sampler (TradingView downsampler)"
    )
    USE_EVERY_X_DOWN_SAMPLER: str = "Use every x candles down sampler"
    NO_DOWN_SAMPLER: str = "No down sampler"
    DEFAULT_DOWN_SAMPLER: str = USE_EVERY_X_DOWN_SAMPLER
    AVAILABLE_DOWN_SAMPLERS: list = [
        USE_EVERY_X_DOWN_SAMPLER,
        SKIP_EVERY_X_DOWN_SAMPLER,
        NO_DOWN_SAMPLER,
    ]
    DOWN_SAMPLERS_BY_TITLES: typing.Dict[str, typing.Callable[[int, int], bool]] = {
        SKIP_EVERY_X_DOWN_SAMPLER: skip_every_x_down_sampler,
        NO_DOWN_SAMPLER: no_down_sampler,
        USE_EVERY_X_DOWN_SAMPLER: use_every_x_down_sampler,
    }
