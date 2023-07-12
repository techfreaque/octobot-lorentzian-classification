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
import tulipy as tulipy
import octobot_trading.enums as trading_enums
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.stop_losses.stop_loss_utilities as stop_loss_utilities
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_public_data as exchange_public_data
import tentacles.Meta.Keywords.scripting_library.settings.script_settings as script_settings


async def get_stop_loss_based_on_atr(
    maker,
    stop_loss_settings,
    trading_side: str,
    entry_price: decimal.Decimal,
):
    script_settings.set_minimum_candles(maker.ctx, stop_loss_settings.atr_period)
    if trading_side in (
        trading_enums.PositionSide.LONG.value,
        trading_enums.TradeOrderSide.BUY.value,
    ):
        sl_price = entry_price - decimal.Decimal(
            str(
                tulipy.atr(
                    await exchange_public_data.High(maker.ctx),
                    await exchange_public_data.Low(maker.ctx),
                    await exchange_public_data.Close(maker.ctx),
                    int(stop_loss_settings.atr_period),
                )[-1]
            )
        )
        sl_in_p, sl_price = stop_loss_utilities.trim_sl_long_price(
            sl_price,
            entry_price,
            decimal.Decimal(str(stop_loss_settings.sl_max_p)),
            decimal.Decimal(str(stop_loss_settings.sl_min_p)),
        )

    elif trading_side in (
        trading_enums.PositionSide.SHORT.value,
        trading_enums.TradeOrderSide.SELL.value,
    ):
        sl_price = entry_price + decimal.Decimal(
            str(
                tulipy.atr(
                    await exchange_public_data.High(maker.ctx),
                    await exchange_public_data.Low(maker.ctx),
                    await exchange_public_data.Close(maker.ctx),
                    int(stop_loss_settings.atr_period),
                )[-1]
            )
        )
        sl_in_p, sl_price = stop_loss_utilities.trim_sl_short_price(
            sl_price,
            entry_price,
            decimal.Decimal(str(stop_loss_settings.sl_max_p)),
            decimal.Decimal(str(stop_loss_settings.sl_min_p)),
        )
    else:
        raise RuntimeError('Side needs to be "long" or "short" for your managed order')
    return sl_in_p, sl_price
