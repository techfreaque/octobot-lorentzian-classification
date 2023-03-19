import time
import typing

import octobot_commons.logging.logging_util as logging_util
import octobot_commons.symbols.symbol_util as symbol_util


def start_measure_time(message=None):
    if message:
        print(message + " started")
    return time.time()


def end_measure_time(m_time, message, min_duration=None):
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


def cut_data_to_same_len(data_set: typing.Union[tuple, list], get_list: bool = False):
    # data tuple in and out
    min_len = None
    cutted_data: list = []

    for data in data_set:
        if data is not None:
            _len = len(data)
            if not min_len or _len < min_len:
                min_len = _len
    for data in data_set:
        if data is not None:
            cutted_data.append(data[len(data) - min_len :])
        else:
            cutted_data.append(None)
    if get_list:
        return cutted_data
    return tuple(cutted_data)


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
