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


def calculate_take_profit_based_on_static_price(
    maker,
    take_profit_settings,
    entry_side: str,
    current_price: decimal.Decimal,
    entry_price: decimal.Decimal,
    stop_loss_price: decimal.Decimal,
    entry_fee: decimal.Decimal,
    market_fee: decimal.Decimal,
) -> decimal.Decimal:
    return decimal.Decimal(str(take_profit_settings.tp_in_d))


async def place_take_profit_based_on_static_price(
    created_orders, ctx, take_profit_data, entry_quantity: decimal.Decimal
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
