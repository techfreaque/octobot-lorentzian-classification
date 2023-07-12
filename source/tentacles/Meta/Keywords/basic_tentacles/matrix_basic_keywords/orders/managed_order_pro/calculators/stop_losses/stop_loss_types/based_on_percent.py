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


def get_stop_loss_based_on_entry_percent(
    maker,
    stop_loss_settings,
    trading_side: str,
    entry_price: decimal.Decimal,
):
    if trading_side in (
        trading_enums.PositionSide.LONG.value,
        trading_enums.TradeOrderSide.BUY.value,
    ):
        sl_in_p = decimal.Decimal(str(stop_loss_settings.sl_in_p_value))
        sl_price = entry_price * (1 - (sl_in_p / 100))
    elif trading_side in (
        trading_enums.PositionSide.SHORT.value,
        trading_enums.TradeOrderSide.SELL.value,
    ):
        sl_in_p = decimal.Decimal(str(stop_loss_settings.sl_in_p_value))
        sl_price = entry_price * (1 + (sl_in_p / 100))
    else:
        raise RuntimeError('Side needs to be "long" or "short" for your managed order')
    return sl_in_p, sl_price


def get_stop_loss_based_on_current_price_percent(
    maker,
    stop_loss_settings,
    trading_side: str,
    current_price: decimal.Decimal,
):
    if trading_side in (
        trading_enums.PositionSide.LONG.value,
        trading_enums.TradeOrderSide.BUY.value,
    ):
        sl_in_p = decimal.Decimal(str(stop_loss_settings.sl_in_p_value))
        sl_price = current_price * (1 - (sl_in_p / 100))
    elif trading_side in (
        trading_enums.PositionSide.SHORT.value,
        trading_enums.TradeOrderSide.SELL.value,
    ):
        sl_in_p = decimal.Decimal(str(stop_loss_settings.sl_in_p_value))
        sl_price = current_price * (1 + (sl_in_p / 100))
    else:
        raise RuntimeError('Side needs to be "long" or "short" for your managed order')
    return sl_in_p, sl_price
