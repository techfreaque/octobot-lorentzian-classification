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

import octobot_trading.enums as trading_enums
import random as random

from tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.matrix_enums import TAG_SEPERATOR


def add_order_counter_to_tags(
    order_id,
    entry_order_tag: str,
    bundled_sl_tag: str or None,
    bundled_tp_tag: str or None,
):
    entry_order_tag = _format_tag(entry_order_tag, order_id)
    if bundled_sl_tag:
        bundled_sl_tag = _format_tag(bundled_sl_tag, order_id)
    if bundled_tp_tag:
        bundled_tp_tag = _format_tag(bundled_tp_tag, order_id)
    return entry_order_tag, bundled_sl_tag, bundled_tp_tag


def _format_tag(order_tag, order_id):
    return f"{order_tag}{TAG_SEPERATOR}{order_id}"


# class ManagedOrderUtilities:
#     maker = None
#     trading_side = ""
#     entry_side = ""
#     exit_side = ""
#     exit_target_position = 0
#     exit_amount = 0
#     exit_order_tag = ""
#     entry_order_tag = ""
#     order_group = None
#     enabled_order_group = False
#     created_orders = None
#     managed_orders_settings: all_settings.ManagedOrdersSettings = None
#     position_size_market = 0

#     async def handle_order_recreate_mode(self, ctx):
#         if self.managed_orders_settings.recreate_exits:
#             # todo use edit orders instead
#             await cancelling.cancel_orders(ctx, self.exit_order_tag)

#     # async def set_managed_amount_and_order_tag(self, ctx):
#     #     # either replace existing exits or keep them and add new exits for new entry
#     #     self.exit_amount = None
#     #     self.exit_target_position = None
#     #     if self.managed_orders_settings.recreate_exits:
#     #         self.exit_target_position = 0
#     #         self.exit_order_tag = f"managed_order {self.trading_side} exit:"
#     #         self.entry_order_tag = f"managed_order {self.trading_side} entry:"
#     #         # todo use edit orders instead
#     #         await cancelling.cancel_orders(ctx, self.exit_order_tag)
#     #         await cancelling.cancel_orders(ctx, self.entry_order_tag)
#     #     else:  # keep existing exit orders and only add new exits
#     #         self.exit_amount = self.position_size
#     #         # todo use something unique to avoid canceling eventual other orders in the same candle
#     #         order_tag_id = random.randint(0, 999999999)
#     #         self.exit_order_tag = (
#     #             f"managed_order {self.trading_side} exit (id: {order_tag_id})"
#     #         )
#     #         self.entry_order_tag = (
#     #             f"managed_order {self.trading_side} entry (id: {order_tag_id})"
#     #         )


def get_trading_sides(trading_side):
    if trading_side == trading_enums.PositionSide.LONG.value:
        entry_side = trading_enums.TradeOrderSide.BUY.value
        exit_side = trading_enums.TradeOrderSide.SELL.value

    elif trading_side == trading_enums.PositionSide.SHORT.value:
        entry_side = trading_enums.TradeOrderSide.SELL.value
        exit_side = trading_enums.TradeOrderSide.BUY.value
    else:
        raise RuntimeError(
            f'managed order: trading side must be "short" or "long" but it was {trading_side}'
        )
    return entry_side, exit_side
