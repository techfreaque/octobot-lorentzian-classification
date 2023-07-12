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
import tentacles.Meta.Keywords.scripting_library.orders.order_types as order_types
import octobot_trading.enums as trading_enums


async def place_take_profit_based_on_risk_reward(
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


def calculate_take_profit_based_on_risk_reward(
    maker,
    take_profit_settings,
    entry_side: str,
    current_price: decimal.Decimal,
    entry_price: decimal.Decimal,
    stop_loss_price: decimal.Decimal,
    entry_fee: decimal.Decimal,
    market_fee: decimal.Decimal,
) -> decimal.Decimal:
    stop_loss_in_percent = (entry_price - stop_loss_price) / (entry_price / 100)
    if stop_loss_in_percent < 0:
        stop_loss_in_percent *= -1
    if entry_side == trading_enums.TradeOrderSide.BUY.value:
        profit_in_p = take_profit_settings.tp_rr * (
            stop_loss_in_percent + market_fee + entry_fee
        )
        take_profit_price = entry_price * (1 + (profit_in_p / 100))
    else:
        profit_in_p = take_profit_settings.tp_rr * (
            stop_loss_in_percent + market_fee + entry_fee
        )
        take_profit_price = entry_price * (1 - (profit_in_p / 100))
    return take_profit_price
