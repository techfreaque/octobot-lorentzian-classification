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

# import tentacles.Meta.Keywords.pro_tentacles.pro_keywords.orders.managed_order_pro.order_notification as order_notification
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.order_placement as order_placement
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.all_settings as all_settings
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.matrix_errors as matrix_errors


class ManagedOrder:
    managed_orders_settings: all_settings.ManagedOrdersSettings = None
    market_fee: decimal.Decimal = None
    limit_fee: decimal.Decimal = None
    trading_side: str = None
    executed_groups: list = []
    symbol: str = None

    async def initialize_and_trade(
        self,
        maker,
        order_block,
        trading_side,
        orders_settings: all_settings.ManagedOrdersSettings,
        forced_amount: decimal.Decimal = None,
        order_preview_mode: bool = False,
    ):
        if not maker.ctx.enable_trading and not order_preview_mode:
            return
        self.managed_orders_settings = orders_settings
        self.executed_groups: list = []
        self.trading_side = trading_side
        success = False
        for group_orders_settings in self.managed_orders_settings.order_groups.values():
            managed_group = order_placement.ManagedOrderPlacement()
            self.executed_groups.append(managed_group)
            # create entry and exit orders orders if possible
            try:
                await managed_group.place_managed_entry_and_exits(
                    maker=maker,
                    order_block=order_block,
                    trading_side=self.trading_side,
                    group_orders_settings=group_orders_settings,
                    managed_orders_settings=self.managed_orders_settings,
                    forced_amount=forced_amount,
                    order_preview_mode=order_preview_mode,
                )
                success = managed_group.created_orders or success
            except matrix_errors.MaximumOpenPositionReachedError:
                # should have logged already
                # maker.ctx.logger.warning(
                #     "Managed order cant open a new position, "
                #     "Make sure the position size is at "
                #     f"least the minimum size required by the exchange for {maker.ctx.symbol}"
                # )
                return self
        # if success:

        #     # send an alert in live mode
        #     await order_notification.send_managed_order_notification(maker.ctx, self)
        return self
