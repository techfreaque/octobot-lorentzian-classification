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

# import tentacles.Meta.Keywords.scripting_library.orders.order_types as order_types
# import octobot_trading.enums as trading_enums


# class ManagedOrderTakeProfit:
#     def __init__(
#         self,
#         side,
#         amount,
#         target_position,
#         group,
#         tag,
#         offset_price=None,
#         scale_from=None,
#         scale_to=None,
#         order_count=None,
#     ):
#         self.side = side
#         self.amount = amount
#         self.target_position = target_position
#         self.scale_from = scale_from
#         self.scale_to = scale_to
#         self.order_count = order_count
#         self.group = group
#         self.offset_price = offset_price
#         self.offset = f"@{offset_price}"
#         self.tag = tag


# def calculate_take_profit_scaled_based_on_percent(
#     self, entry_price
# ) -> ManagedOrderTakeProfit:
#     if self.entry_side == trading_enums.TradeOrderSide.BUY.value:
#         scale_from = entry_price * (1 + (self.managed_orders_settings.p_tp_min / 100))
#         scale_from = f"@{scale_from}"
#         scale_to = entry_price * (1 + (self.managed_orders_settings.p_tp_max / 100))
#         scale_to = f"@{scale_to}"
#     else:
#         scale_from = entry_price * (1 + (self.managed_orders_settings.p_tp_max / 100))
#         scale_from = f"@{scale_from}"
#         scale_to = entry_price * (1 + (self.managed_orders_settings.p_tp_min / 100))
#         scale_to = f"@{scale_to}"
#     return ManagedOrderTakeProfit(
#         side=self.exit_side,
#         amount=self.exit_amount,
#         target_position=self.exit_target_position,
#         group=self.order_group,
#         tag=self.exit_order_tag,
#         order_count=self.managed_orders_settings.p_tp_order_count,
#         scale_from=scale_from,
#         scale_to=scale_to,
#     )


# async def place_take_profit_scaled_based_on_percent(
#     created_orders, ctx, take_profit_data, entry_quantity: float
# ) -> None:
#     await order_types.scaled_limit(
#         ctx,
#         side=take_profit_data.side,
#         amount=entry_quantity,
#         target_position=take_profit_data.target_position,
#         scale_from=take_profit_data.scale_from,
#         scale_to=take_profit_data.scale_to,
#         order_count=take_profit_data.order_count,
#         group=take_profit_data.group,
#         tag=take_profit_data.tag,
#         reduce_only=True,
#         wait_for=created_orders,
#     )





# def calculate_take_profit_scaled_based_on_risk_reward(
#     self, entry_price
# ) -> ManagedOrderTakeProfit:
#     self.entry_fees = self.market_fee if self.entry_type == "market" else self.limit_fee
#     if self.entry_side == trading_enums.TradeOrderSide.BUY.value:
#         scale_from = entry_price * (
#             1
#             + (
#                 self.managed_orders_settings.rr_tp_min
#                 * (self.sl_in_p + self.market_fee + self.entry_fees)
#                 / 100
#             )
#         )
#         scale_from = f"@{scale_from}"
#         scale_to = entry_price * (
#             1
#             + (
#                 self.managed_orders_settings.rr_tp_max
#                 * (self.sl_in_p + self.market_fee + self.entry_fees)
#                 / 100
#             )
#         )
#         scale_to = f"@{scale_to}"
#     else:
#         scale_from = entry_price * (
#             1
#             - (
#                 self.managed_orders_settings.rr_tp_max
#                 * (self.sl_in_p + self.market_fee + self.entry_fees)
#                 / 100
#             )
#         )
#         scale_from = f"@{scale_from}"
#         scale_to = entry_price * (
#             1
#             - (
#                 self.managed_orders_settings.rr_tp_min
#                 * (self.sl_in_p + self.market_fee + self.entry_fees)
#                 / 100
#             )
#         )
#         scale_to = f"@{scale_to}"
#     return ManagedOrderTakeProfit(
#         side=self.exit_side,
#         amount=self.exit_amount,
#         target_position=self.exit_target_position,
#         group=self.order_group,
#         tag=self.exit_order_tag,
#         order_count=self.managed_orders_settings.rr_tp_order_count,
#         scale_from=scale_from,
#         scale_to=scale_to,
#     )


# async def place_take_profit_scaled_based_on_risk_reward(
#     created_orders, ctx, take_profit_data, entry_quantity: float
# ) -> None:
#     await order_types.scaled_limit(
#         ctx,
#         side=take_profit_data.side,
#         amount=entry_quantity,
#         target_position=take_profit_data.target_position,
#         scale_from=take_profit_data.scale_from,
#         scale_to=take_profit_data.scale_to,
#         order_count=take_profit_data.managed_orders_settings.order_count,
#         group=take_profit_data.group,
#         tag=take_profit_data.tag,
#         reduce_only=True,
#         wait_for=created_orders,
#     )

