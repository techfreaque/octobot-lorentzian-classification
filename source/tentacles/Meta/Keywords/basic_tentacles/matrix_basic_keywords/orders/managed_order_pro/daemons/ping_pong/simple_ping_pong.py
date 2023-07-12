# a42.ch CONFIDENTIAL
# __________________
#
#  [2021] - [∞] a42.ch Incorporated
#  All Rights Reserved.
#
# NOTICE:  All information contained herein is, and remains
# the property of a42.ch Incorporated and its suppliers,
# if any.  The intellectual and technical concepts contained
# herein are proprietary to a42.ch Incorporated
# and its suppliers and may be covered by U.S. and Foreign Patents,
# patents in process, and are protected by trade secret or copyright law.
# Dissemination of this information or reproduction of this material
# is strictly forbidden unless prior written permission is obtained
# from a42.ch Incorporated.
#
# If you want to use any code for commercial purposes,
# or you want your own custom solution,
# please contact me at max@a42.ch

from octobot_services.interfaces.util.util import run_in_bot_main_loop
import octobot_trading.enums as trading_enums
from tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords import matrix_enums
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.daemons.ping_pong.ping_pong_constants as ping_pong_constants
from .ping_pong_storage import storage as storage
from .ping_pong_storage import element as element
import tentacles.Meta.Keywords.scripting_library.orders.order_types as order_types


RETRY_RECREATE_ENTRY_ATTEMPTS_COUNT: int = 5

PING_PONG_TIMEOUT = 200


async def play_ping_pong(
    trading_mode,
    exchange,
    exchange_id,
    cryptocurrency,
    symbol,
    triggered_order,
):
    if is_relevant_take_profit_order(
        trading_mode=trading_mode,
        symbol=symbol,
        triggered_order=triggered_order,
    ):
        run_in_bot_main_loop(
            play_simple_ping_pong(
                trading_mode=trading_mode,
                symbol=symbol,
                triggered_order=triggered_order,
            ),
            blocking=False,
            timeout=PING_PONG_TIMEOUT,
        )


async def play_simple_ping_pong(
    trading_mode,
    symbol,
    triggered_order,
):
    retry_counter = 0
    tag_info = triggered_order["tag"].split(matrix_enums.TAG_SEPERATOR)
    group_key = tag_info[1]
    order_group_id = tag_info[2]
    grid_id = tag_info[3]
    ping_pong_group_data: element.PingPongSingleData = await get_entry_ping_pong_data(
        trading_mode=trading_mode,
        triggered_order=triggered_order,
        group_key=group_key,
        order_group_id=order_group_id,
        grid_id=grid_id,
        retry_counter=retry_counter,
    )
    if ping_pong_group_data:
        retry_counter = 0
        # mode_producer.ctx.enable_trading = True

        await recreate_entry_order(
            trading_mode=trading_mode,
            ping_pong_single_data=ping_pong_group_data,
            symbol=symbol,
            triggered_order=triggered_order,
            retry_counter=retry_counter,
        )
        # mode_producer.ctx.enable_trading = False


def is_relevant_take_profit_order(
    trading_mode,
    symbol,
    triggered_order: dict,
) -> bool:
    return (
        trading_mode.producers[0].any_ping_pong_mode_active
        and triggered_order.get("status") == trading_enums.OrderStatus.FILLED.value
        and triggered_order.get("type") == trading_enums.TradeOrderType.LIMIT.value
        and triggered_order["tag"]
        and triggered_order["tag"].startswith(ping_pong_constants.TAKE_PROFIT)
    )


# def get_grid_and_order_id(exit_order_tag: str) -> typing.Tuple[int, int]:
#     _, order_id = exit_order_tag.split("(id: ")
#     if ") " in order_id:
#         order_id, grid_id = order_id.split(") ")
#         order_id = int(order_id)
#         grid_id, grid_size = grid_id.split("/")
#         grid_id = int(grid_id) - 1
#     else:
#         order_id = int(order_id.replace(")", ""))
#         grid_id = 0
#     return grid_id, order_id


async def get_entry_ping_pong_data(
    trading_mode,
    triggered_order: dict,
    group_key: str,
    order_group_id: str,
    grid_id: str,
    retry_counter: int,
) -> element.PingPongSingleData or None:
    ping_pong_storage: storage.PingPongStorage = storage.get_ping_pong_storage(
        trading_mode.exchange_manager
    )
    return await ping_pong_storage.get_entry_order(
        triggered_order=triggered_order,
        group_key=group_key,
        order_group_id=order_group_id,
        grid_id=grid_id,
        retry_counter=retry_counter,
    )


async def recreate_entry_order(
    trading_mode,
    ping_pong_single_data: element.PingPongSingleData,
    symbol: str,
    triggered_order: dict,
    retry_counter: int,
    next_entry_data: dict = None,
):
    next_entry_data = (
        next_entry_data or ping_pong_single_data.get_to_replace_order_details()
    )

    sl_price = next_entry_data.get(
        ping_pong_constants.PingPongOrderColumns.STOP_LOSS_PRICE.value
    )
    stop_loss_tag = None
    stop_loss_offset = None
    if sl_price:
        stop_loss_offset = f"@{next_entry_data[ping_pong_constants.PingPongOrderColumns.STOP_LOSS_PRICE.value]}"
        stop_loss_tag = (
            next_entry_data[
                ping_pong_constants.PingPongOrderColumns.STOP_LOSS_TAG.value
            ],
        )
    tp_price = next_entry_data[
        ping_pong_constants.PingPongOrderColumns.TAKE_PROFIT_PRICE.value
    ]
    take_profit_offset = f"@{tp_price}"
    take_profit_tag = next_entry_data[
        ping_pong_constants.PingPongOrderColumns.TAKE_PROFIT_TAG.value
    ]
    bundled_exit_group = None
    if sl_price and tp_price:
        bundled_exit_group = None  # TODO
    try:
        trading_mode.producers[0].ctx.enable_trading = True
        created_orders = await order_types.limit(
            trading_mode.producers[0].ctx,
            symbol=symbol,
            side=next_entry_data[ping_pong_constants.PingPongOrderColumns.SIDE.value],
            amount=next_entry_data[
                ping_pong_constants.PingPongOrderColumns.AMOUNT.value
            ],
            offset=f"@{next_entry_data[ping_pong_constants.PingPongOrderColumns.ENTRY_PRICE.value]}",
            tag=next_entry_data[
                ping_pong_constants.PingPongOrderColumns.ENTRY_TAG.value
            ],
            stop_loss_offset=stop_loss_offset,
            stop_loss_tag=stop_loss_tag,
            take_profit_offset=take_profit_offset,
            take_profit_tag=take_profit_tag,
            stop_loss_group=bundled_exit_group,
            take_profit_group=bundled_exit_group,
        )
    except Exception as error:
        retry_counter += 1
        return await retry_recreate_entry_order(
            trading_mode=trading_mode,
            ping_pong_single_data=ping_pong_single_data,
            symbol=symbol,
            triggered_order=triggered_order,
            retry_counter=retry_counter,
            next_entry_data=next_entry_data,
            error=error,
        )
    try:
        recreated_entry_order = created_orders[0]
        if recreated_entry_order and recreated_entry_order.status in (
            trading_enums.OrderStatus.CLOSED,
            trading_enums.OrderStatus.OPEN,
            trading_enums.OrderStatus.FILLED,
            trading_enums.OrderStatus.PARTIALLY_FILLED,
        ):
            ping_pong_single_data.log_replaced_entry_order(
                recreated_entry_order=recreated_entry_order,
            )
            return recreated_entry_order
        raise PingPongRecreatedEntryOrderNotFilledError(
            f"Recreated order status is: {recreated_entry_order.status if recreated_entry_order else ''}"
        )
    except (
        IndexError,
        AttributeError,
        PingPongRecreatedEntryOrderNotFilledError,
    ) as error:
        retry_counter += 1
        return await retry_recreate_entry_order(
            trading_mode=trading_mode,
            symbol=symbol,
            triggered_order=triggered_order,
            retry_counter=retry_counter,
            ping_pong_single_data=ping_pong_single_data,
            next_entry_data=next_entry_data,
            error=error,
        )


async def retry_recreate_entry_order(
    trading_mode,
    symbol,
    triggered_order: dict,
    retry_counter: int,
    ping_pong_single_data: element.PingPongSingleData,
    next_entry_data: dict = None,
    error=None,
):
    if (
        retry_counter < RETRY_RECREATE_ENTRY_ATTEMPTS_COUNT
        and not trading_mode.exchange_manager.is_backtesting
    ):
        return await recreate_entry_order(
            trading_mode=trading_mode,
            symbol=symbol,
            triggered_order=triggered_order,
            retry_counter=retry_counter,
            ping_pong_single_data=ping_pong_single_data,
            next_entry_data=next_entry_data,
        )
    if not not trading_mode.exchange_manager.is_backtesting:
        raise RuntimeError(
            "Failed to recreate entry order, when take profit got filled. "
            f"Recreated entry order: {next_entry_data}"
        ) from error


class PingPongRecreatedEntryOrderNotFilledError(Exception):
    pass
