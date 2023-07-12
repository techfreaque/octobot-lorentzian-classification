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

import octobot_backtesting.api as backtesting_api
from tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.close_all_trades import (
    close_all_positions,
)


async def skip_backtesting_runs_if_condition(ctx, skip_runs_balance):
    if skip_runs_balance:
        current_total_balance = (
            ctx.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value
        )
        origin_total_balance = (
            ctx.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_origin_value
        )

        if current_total_balance < origin_total_balance * skip_runs_balance / 100:
            await close_all_positions(ctx)
            register_backtesting_timestamp_whitelist(ctx, [], append_to_whitelist=False)


def register_backtesting_timestamp_whitelist(ctx, timestamps, append_to_whitelist=True):
    def _open_order_and_position_check():
        # by default, avoid skipping timestamps when there are open orders or active positions
        if ctx.exchange_manager.exchange_personal_data.orders_manager.get_open_orders():
            return True
        for (
            position
        ) in (
            ctx.exchange_manager.exchange_personal_data.positions_manager.positions.values()
        ):
            if not position.is_idle():
                return True
        return False

    if backtesting_api.get_backtesting_timestamp_whitelist(
        ctx.exchange_manager.exchange.backtesting
    ) != sorted(set(timestamps)):
        backtesting_api.register_backtesting_timestamp_whitelist(
            ctx.exchange_manager.exchange.backtesting,
            timestamps,
            _open_order_and_position_check,
            append_to_whitelist=append_to_whitelist,
        )
