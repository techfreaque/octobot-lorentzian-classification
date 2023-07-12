import time
import typing
import numpy.typing as npt
from octobot_commons import enums

import octobot_commons.logging.logging_util as logging_util
import octobot_commons.symbols.symbol_util as symbol_util
from tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.data import (
    public_exchange_data,
)
from tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.matrix_enums import (
    PriceDataSources,
)


def start_measure_time(message: typing.Optional[str] = None) -> float:
    if message:
        print(message + " started")
    return time.time()


def end_measure_time(
    m_time: typing.Union[int, float],
    message: str,
    min_duration: typing.Optional[typing.Union[int, float]] = None,
) -> None:
    duration = round(time.time() - m_time, 2)
    if not min_duration or min_duration < duration:
        print(f"{message} done {duration}s")


def end_measure_live_time(ctx, m_time, message, min_duration=None):
    duration = round(time.time() - m_time, 2)
    if not min_duration or min_duration < duration:
        ctx.logger.info(f"{message} done {duration}s")


class NanoContext:
    def __init__(self, exchange_manager, symbol):
        self.exchange_manager = exchange_manager
        self.symbol: str = symbol
        self.trader = exchange_manager.trader
        self.enable_trading: bool = True
        self.just_created_orders: list = []
        self.allow_artificial_orders: bool = False
        self.plot_orders: bool = False
        self.logger = logging_util.get_logger("NanoContext")

    def is_trading_signal_emitter(self):
        return False


def get_nano_context(exchange_manager, symbol):
    return NanoContext(exchange_manager=exchange_manager, symbol=symbol)


def get_pre_order_data(exchange_manager, symbol):
    fees_currency_side = None
    if exchange_manager.is_future:
        fees_currency_side = exchange_manager.exchange.get_pair_future_contract(
            symbol
        ).get_fees_currency_side()
    symbol_market = exchange_manager.exchange.get_market_status(
        symbol, with_fixer=False
    )
    return fees_currency_side, symbol_market


def cut_data_to_same_len(
    data_set: typing.Union[tuple, list],
    get_list: bool = False,
    reference_length: typing.Optional[int] = None,
):
    # data tuple in and out
    min_len = reference_length
    cutted_data: list = []

    for data in data_set:
        if data is not None:
            _len = len(data)
            if min_len is None or _len < min_len:
                min_len = _len
    for data in data_set:
        if data is not None:
            cutted_data.append(data[len(data) - min_len :])
        else:
            cutted_data.append(None)
    if get_list:
        return cutted_data
    return tuple(cutted_data)


def shift_data(data_source: typing.Union[list, npt.NDArray[any]], shift_by: int = 1):
    cutted_data = data_source[shift_by:]
    shifted_data = data_source[:-shift_by]
    return cutted_data, shifted_data


def get_similar_symbol(
    symbol: str, this_exchange_manager, other_exchange_manager
) -> str:
    # allows mixing BTC/USDT and BTC/USDT:USDT pairs
    if not other_exchange_manager.symbol_exists(symbol):
        # try other pairs for different exchange types
        parsed_symbol = symbol_util.parse_symbol(symbol)
        if this_exchange_manager.is_future:
            # try a spot pair
            parsed_symbol.settlement_asset = None
        else:
            # try a futures pair instead
            # TODO handle inverse pairs
            parsed_symbol.settlement_asset = parsed_symbol.quote
        symbol = parsed_symbol.merged_str_symbol()
        if not other_exchange_manager.symbol_exists(symbol):
            raise RuntimeError(
                f"Not able to find a suitable pair for {symbol} "
                f"on {other_exchange_manager.exchange_name}"
            )
    return symbol


async def normalize_any_time_frame_to_this_time_frame(
    maker,
    data,
    source_time_frame: str,
    target_time_frame: str,
):
    if source_time_frame == target_time_frame:
        return data
    # different time frame as trigger timeframe
    target_time_frame_timestamps: list = await public_exchange_data.get_candles_(
        maker, PriceDataSources.TIME.value, time_frame=target_time_frame
    )
    source_time_frame_timestamps: list = await public_exchange_data.get_candles_(
        maker, PriceDataSources.TIME.value, time_frame=source_time_frame
    )

    data_time_frame_minutes = enums.TimeFramesMinutes[
        enums.TimeFrames(source_time_frame)
    ]
    target_time_frame_minutes = enums.TimeFramesMinutes[
        enums.TimeFrames(target_time_frame)
    ]
    candles_to_add = data_time_frame_minutes / target_time_frame_minutes
    try:
        if candles_to_add > 1:
            return _normalize_to_smaller_time_frame(
                candles_to_add,
                target_time_frame_timestamps,
                source_time_frame_timestamps,
                data,
            )
        return normalize_to_bigger_time_frame(
            target_time_frame_timestamps,
            source_time_frame_timestamps,
            data,
        )
    except Exception as error:
        raise RuntimeError(
            f"Failed to adapt indicator from {source_time_frame} to {target_time_frame}"
        ) from error


def _normalize_to_smaller_time_frame(
    candles_to_add, target_time_frame_timestamps, source_time_frame_timestamps, data
):
    first_full_index = 1
    unified_data = []
    # target timeframe is smaller
    # adds last candle and finds second last index
    for index in range(1, len(target_time_frame_timestamps)):
        if source_time_frame_timestamps[-1] == target_time_frame_timestamps[-index]:
            break
        unified_data.insert(0, data[-1])
        first_full_index += 1

    origin_data_len = len(data)
    target_data_len = len(target_time_frame_timestamps)
    data_index = 2
    # normalize all other data
    while first_full_index <= target_data_len and origin_data_len >= data_index:
        virtual_candle_index = 1
        while (
            (virtual_candle_index <= candles_to_add)
            and first_full_index <= target_data_len
            and origin_data_len >= data_index
        ):
            virtual_candle_index += 1
            unified_data.insert(0, data[-data_index])
            first_full_index += 1
        data_index += 1
    return unified_data


def normalize_to_bigger_time_frame(
    target_time_frame_timestamps, source_time_frame_timestamps, data
):
    # target timeframe is bigger
    # adds last few candle and finds next index
    target_index_start_index = 1
    unified_data = []
    cut_source_time_frame_timestamps, cut_data = cut_data_to_same_len(
        (source_time_frame_timestamps, data)
    )
    for source_index in range(1, len(cut_source_time_frame_timestamps)):
        for target_index in range(
            target_index_start_index, len(target_time_frame_timestamps)
        ):
            if (
                target_time_frame_timestamps[-target_index]
                == cut_source_time_frame_timestamps[-source_index]
            ):
                target_index_start_index = target_index
                unified_data.insert(0, cut_data[-source_index])
                break

    return unified_data
