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

import decimal as decimal
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_public_data as exchange_public_data
import octobot_trading.enums as trading_enums
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.stop_losses.stop_loss_utilities as stop_loss_utilities
# import tentacles.Meta.Keywords.pro_tentacles.standalone_data_source.standalone_data_sources as standalone_data_sources


async def trail_to_indicator(maker, order_group_settings, orders_settings):
    sl_price, _, _ = await get_managed_trailing_stop_from_indicator(
        maker, orders_settings, order_group_settings
    )
    return sl_price


async def get_managed_trailing_stop_from_indicator(
    maker, managed_orders_settings, order_group_settings
):
    current_price_val = await exchange_public_data.current_live_price(maker.ctx)
    sl_in_p = None
    sl_indicator_value = decimal.Decimal(
        str(
            standalone_data_sources.get_standalone_data_source(
                order_group_settings.stop_loss.trailing_indicator_id, maker
            )
        )
    )

    if managed_orders_settings.trading_side in (
        trading_enums.PositionSide.LONG.value,
        trading_enums.TradeOrderSide.BUY.value,
    ):
        sl_in_p, sl_indicator_value = stop_loss_utilities.trim_sl_long_price(
            sl_indicator_value,
            current_price_val,
            order_group_settings.stop_loss.sl_trailing_max_p,
            order_group_settings.stop_loss.sl_trailing_min_p,
        )
    elif managed_orders_settings.trading_side in (
        trading_enums.PositionSide.SHORT.value,
        trading_enums.TradeOrderSide.SELL.value,
    ):
        sl_in_p, sl_indicator_value = stop_loss_utilities.trim_sl_short_price(
            sl_indicator_value,
            current_price_val,
            order_group_settings.stop_loss.sl_trailing_max_p,
            order_group_settings.stop_loss.sl_trailing_min_p,
        )
    else:
        raise RuntimeError('Side needs to be "long" or "short" for your managed order')
    return sl_indicator_value, sl_in_p, current_price_val
