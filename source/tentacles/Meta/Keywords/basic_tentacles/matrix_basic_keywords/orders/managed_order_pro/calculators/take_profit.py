import decimal

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

import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.take_profits.based_on_indicator as based_on_indicator
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.take_profits.based_on_percent as based_on_percent
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.take_profits.based_on_risk_reward as based_on_risk_reward
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.take_profits.based_on_static_price as based_on_static_price
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.tp_settings as tp_settings


def get_manged_order_take_profits(
    maker,
    order_block,
    take_profit_settings,
    entry_side: str,
    current_price: decimal.Decimal,
    entry_price: decimal.Decimal,
    stop_loss_price: decimal.Decimal,
    entry_fee: decimal.Decimal,
    market_fee: decimal.Decimal,
) -> None or decimal.Decimal:
    if (
        tp_settings.ManagedOrderSettingsTPTypes.NO_TP_DESCRIPTION
        != take_profit_settings.tp_type
    ):
        # take profit based on risk reward
        if (
            take_profit_settings.tp_type
            == tp_settings.ManagedOrderSettingsTPTypes.SINGLE_RISK_REWARD_DESCRIPTION
        ):
            return based_on_risk_reward.calculate_take_profit_based_on_risk_reward(
                maker=maker,
                take_profit_settings=take_profit_settings,
                entry_side=entry_side,
                current_price=current_price,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                entry_fee=entry_fee,
                market_fee=market_fee,
            )

        # # scaled take profit based on risk reward
        # elif (
        #     take_profit_settings.tp_type
        #     == tp_settings.ManagedOrderSettingsTPTypes.SCALED_RISK_REWARD_DESCRIPTION
        # ):

        #         take_profits.calculate_take_profit_scaled_based_on_risk_reward(
        #             take_profit_settings, entry_price
        #         )

        # take profit based on percent
        elif (
            take_profit_settings.tp_type
            == tp_settings.ManagedOrderSettingsTPTypes.SINGLE_PERCENT_DESCRIPTION
        ):
            return based_on_percent.calculate_take_profit_based_on_percent(
                maker=maker,
                take_profit_settings=take_profit_settings,
                entry_side=entry_side,
                current_price=current_price,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                entry_fee=entry_fee,
                market_fee=market_fee,
            )
        # take profit based on indicator
        elif (
            take_profit_settings.tp_type
            == tp_settings.ManagedOrderSettingsTPTypes.SINGLE_INDICATOR_DESCRIPTION
        ):
            return based_on_indicator.calculate_take_profit_based_on_indicator(
                order_block=order_block,
                take_profit_settings=take_profit_settings,
                entry_side=entry_side,
                current_price=current_price,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                entry_fee=entry_fee,
                market_fee=market_fee,
            )

        # # scaled take profit based on percent
        # elif (
        #     take_profit_settings.tp_type
        #     == tp_settings.ManagedOrderSettingsTPTypes.SCALED_PERCENT_DESCRIPTION
        # ):

        #         take_profits.calculate_take_profit_scaled_based_on_percent(
        #             take_profit_settings, entry_price
        #         )

        # single take profit based on static price
        elif (
            take_profit_settings.tp_type
            == tp_settings.ManagedOrderSettingsTPTypes.SINGLE_STATIC_DESCRIPTION
        ):
            return based_on_static_price.calculate_take_profit_based_on_static_price(
                maker=maker,
                take_profit_settings=take_profit_settings,
                entry_side=entry_side,
                current_price=current_price,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                entry_fee=entry_fee,
                market_fee=market_fee,
            )

    return None
