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

import octobot_commons.symbols.symbol_util as symbol_util
import octobot_services.api as services_api
import octobot_services.enums as services_enum
from tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.position_sizing import (
    get_current_open_risk,
)
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.entry_types as entry_types
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.position_size_settings as size_settings
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.sl_settings as sl_settings
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.tp_settings as tp_settings


async def send_managed_order_notification(ctx, managed_order_data):
    if (
        ctx.exchange_manager.is_backtesting is not True
        and managed_order_data.managed_orders_settings.enable_alerts
    ):
        alert_title = f"opened a new {managed_order_data.trading_side} trade"
        entry_part = ""
        if (
            managed_order_data.managed_orders_settings.entry_type
            == entry_types.ManagedOrderSettingsEntryTypes.SINGLE_MARKET_IN_DESCRIPTION
        ):
            entry_part = (
                f"entry price: {managed_order_data.entry_price} \n"
                f"entry type: {managed_order_data.entry_type} \n"
            )

        stop_loss_part = ""
        if (
            managed_order_data.managed_orders_settings.sl_type
            != sl_settings.ManagedOrderSettingsSLTypes.NO_SL_DESCRIPTION
        ):
            stop_loss_part = (
                f"stop loss in %: {managed_order_data.sl_in_p} \n"
                f"stop loss @: {managed_order_data.sl_price}\n"
            )
        take_profit_part = ""
        if (
            managed_order_data.managed_orders_settings.tp_type
            == tp_settings.ManagedOrderSettingsTPTypes.SINGLE_RISK_REWARD_DESCRIPTION
        ):
            take_profit_part = (
                f"take profit risk reward: {managed_order_data.managed_orders_settings.tp_rr} \n"
                f"take profit in %: {managed_order_data.profit_in_p} \n"
                f"take profit @: {managed_order_data.profit_in_d} \n"
            )
        elif (
            managed_order_data.managed_orders_settings.tp_type
            == tp_settings.ManagedOrderSettingsTPTypes.SINGLE_PERCENT_DESCRIPTION
        ):
            take_profit_part = (
                f"take profit in %: {managed_order_data.profit_in_p} \n"
                f"take profit @: {managed_order_data.profit_in_d} \n"
            )
        position_size_part = ""
        if (
            managed_order_data.managed_orders_settings.position_size_type
            == size_settings.ManagedOrderSettingsPositionSizeTypes.PERCENT_RISK_OF_ACCOUNT_DESCRIPTION
        ):
            # get up-to-date open risk
            managed_order_data.entry_price = (
                managed_order_data.entry_price
                or managed_order_data.expected_entry_price
            )
            old_open_risk = round(
                managed_order_data.current_open_risk * managed_order_data.entry_price, 3
            )
            new_open_risk = round(
                await get_current_open_risk(ctx, managed_order_data.market_fee)
                * managed_order_data.entry_price,
                3,
            )
            ref_market = symbol_util.parse_symbol(ctx.symbol).quote
            position_size_part = (
                f"position size: {managed_order_data.exit_amount} \n"
                f"position size {ref_market}:"
                f" {round(managed_order_data.exit_amount * managed_order_data.entry_price, 3)} \n"
                f"\n"
                f"risk details before trade opened: \n"
                f" open risk: {ref_market} {old_open_risk} \n"
                f" max position size: {managed_order_data.max_position_size} \n"
                f" available exchange balance: {managed_order_data.max_buying_power} \n"
                f"\n"
                f"risk details after trade opened: \n"
                f" open risk: {ref_market} {new_open_risk}"
            )

        alert_content = (
            entry_part + stop_loss_part + take_profit_part + position_size_part
        )
        await services_api.send_notification(
            services_api.create_notification(
                alert_content,
                title=alert_title,
                markdown_text=alert_content,
                category=services_enum.NotificationCategory.TRADING_SCRIPT_ALERTS,
            )
        )
