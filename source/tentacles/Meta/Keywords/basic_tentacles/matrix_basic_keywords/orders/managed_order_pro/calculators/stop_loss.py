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
import typing
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.stop_losses.stop_loss_types as stop_loss_types
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.sl_settings as sl_settings
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_public_data as exchange_public_data


async def get_manged_order_stop_loss(
    maker,
    order_block,
    stop_loss_settings,
    trading_side,
    entry_price: decimal.Decimal,
    current_price: decimal.Decimal,
    get_from_current_price: bool = False,
) -> typing.Tuple[float, float]:
    sl_price: float = None
    sl_in_p: float = None
    current_price = current_price or float(
        await exchange_public_data.current_live_price(maker.ctx)
    )
    entry_price = entry_price or current_price
    if trading_side == "buy":
        entry_price = entry_price if entry_price < current_price else current_price
    else:
        entry_price = entry_price if entry_price > current_price else current_price
    if (
        stop_loss_settings.sl_type
        != sl_settings.ManagedOrderSettingsSLTypes.NO_SL_DESCRIPTION
    ):
        # SL based on low/high
        if (
            stop_loss_settings.sl_type
            == sl_settings.ManagedOrderSettingsSLTypes.AT_LOW_HIGH_DESCRIPTION
        ):
            sl_in_p, sl_price = await stop_loss_types.get_stop_loss_based_on_low_high(
                maker=maker,
                stop_loss_settings=stop_loss_settings,
                trading_side=trading_side,
                entry_price=current_price if get_from_current_price else entry_price,
            )
        # SL based on percent from entry price
        elif (
            stop_loss_settings.sl_type
            == sl_settings.ManagedOrderSettingsSLTypes.BASED_ON_PERCENT_ENTRY_DESCRIPTION
        ):
            sl_in_p, sl_price = stop_loss_types.get_stop_loss_based_on_entry_percent(
                maker=maker,
                stop_loss_settings=stop_loss_settings,
                trading_side=trading_side,
                entry_price=current_price if get_from_current_price else entry_price,
            )
        # SL based on percent of current price
        elif (
            stop_loss_settings.sl_type
            == sl_settings.ManagedOrderSettingsSLTypes.BASED_ON_PERCENT_PRICE_DESCRIPTION
        ):
            (
                sl_in_p,
                sl_price,
            ) = stop_loss_types.get_stop_loss_based_on_current_price_percent(
                maker=maker,
                stop_loss_settings=stop_loss_settings,
                trading_side=trading_side,
                current_price=current_price,
            )
        # SL based on indicator
        elif (
            stop_loss_settings.sl_type
            == sl_settings.ManagedOrderSettingsSLTypes.BASED_ON_INDICATOR_DESCRIPTION
        ):
            sl_in_p, sl_price = await stop_loss_types.get_stop_loss_based_on_indicator(
                order_block=order_block,
                stop_loss_settings=stop_loss_settings,
                trading_side=trading_side,
                entry_price=current_price if get_from_current_price else entry_price,
            )
        # SL based on static price
        elif (
            stop_loss_settings.sl_type
            == sl_settings.ManagedOrderSettingsSLTypes.BASED_ON_STATIC_PRICE_DESCRIPTION
        ):
            sl_in_p, sl_price = stop_loss_types.get_stop_loss_based_on_static_price(
                maker=maker,
                stop_loss_settings=stop_loss_settings,
                trading_side=trading_side,
                entry_price=current_price if get_from_current_price else entry_price,
            )

        # SL based on ATR
        elif (
            stop_loss_settings.sl_type
            == sl_settings.ManagedOrderSettingsSLTypes.BASED_ON_ATR_DESCRIPTION
        ):
            sl_in_p, sl_price = await stop_loss_types.get_stop_loss_based_on_atr(
                maker=maker,
                stop_loss_settings=stop_loss_settings,
                trading_side=trading_side,
                entry_price=current_price if get_from_current_price else entry_price,
            )
        return (
            exchange_public_data.get_digits_adapted_price(maker.ctx, sl_price),
            sl_in_p,
        )
        # no SL
    return None, None
