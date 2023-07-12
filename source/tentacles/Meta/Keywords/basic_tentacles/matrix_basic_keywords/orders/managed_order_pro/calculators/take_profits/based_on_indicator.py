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

import decimal
import octobot_trading.enums as trading_enums

# import tentacles.Meta.Keywords.pro_tentacles.standalone_data_source.standalone_data_sources as standalone_data_sources
import tentacles.Meta.Keywords.scripting_library.orders.order_types as order_types
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.stop_losses.stop_loss_utilities as stop_loss_utilities


def calculate_take_profit_based_on_indicator(
    order_block,
    take_profit_settings,
    entry_side: str,
    current_price: decimal.Decimal,
    entry_price: decimal.Decimal,
    stop_loss_price: decimal.Decimal,
    entry_fee: decimal.Decimal,
    market_fee: decimal.Decimal,
):
    tp_indicator_value = order_block.get_indicator_value(take_profit_settings)

    if entry_side in (
        trading_enums.TradeOrderSide.BUY.value,
        trading_enums.PositionSide.LONG.value,
    ):
        _, tp_price = stop_loss_utilities.trim_sl_short_price(
            tp_indicator_value,
            current_price,
            take_profit_settings.tp_max_p,
            take_profit_settings.tp_min_p,
        )

    elif entry_side in (
        trading_enums.TradeOrderSide.SELL.value,
        trading_enums.PositionSide.SHORT.value,
    ):
        _, tp_price = stop_loss_utilities.trim_sl_long_price(
            tp_indicator_value,
            current_price,
            take_profit_settings.tp_max_p,
            take_profit_settings.tp_min_p,
        )
    else:
        raise RuntimeError('Side needs to be "long" or "short" for your managed order')
    return tp_price


async def place_take_profit_based_on_indicator(
    created_orders, ctx, take_profit_data, entry_quantity: float
) -> None:
    await order_types.limit(
        ctx,
        side=take_profit_data.side,
        amount=entry_quantity,
        target_position=take_profit_data.target_position,
        offset=take_profit_data.offset,
        group=take_profit_data.group,
        tag=take_profit_data.tag,
        reduce_only=True,
        wait_for=created_orders,
    )
