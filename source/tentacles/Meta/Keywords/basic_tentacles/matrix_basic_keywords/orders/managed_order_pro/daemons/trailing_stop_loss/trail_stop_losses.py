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
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.daemons.trailing_stop_loss.trailing_types as trailing_types
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.sl_settings as sl_settings
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_public_data as exchange_public_data
import tentacles.Meta.Keywords.scripting_library.orders.editing as editing
import tentacles.Meta.Keywords.scripting_library.orders.open_orders as open_orders
import octobot_trading.enums as trading_enums
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.matrix_enums as matrix_enums


async def trail_stop_losses_for_this_candle(
    maker, order_group_settings, order_settings
):
    if (
        not order_group_settings.stop_loss.sl_trail_type
        == sl_settings.ManagedOrderSettingsSLTrailTypes.DONT_TRAIL_DESCRIPTION
    ):
        _open_orders = open_orders.get_open_orders(maker.ctx)
        if _open_orders:
            current_price = decimal.Decimal(
                str(await exchange_public_data.current_candle_price(maker.ctx))
            )
            for order in _open_orders:
                if (
                    order.tag
                    and f"{matrix_enums.TAG_SEPERATOR}{order_group_settings.order_manager_group_id}{matrix_constants.TAG_SEPERATOR}"
                    in order.tag
                ):
                    new_sl_price = None
                    trading_side = (
                        trading_enums.PositionSide.LONG.value
                        if order.side is trading_enums.TradeOrderSide.SELL
                        else trading_enums.PositionSide.SHORT.value
                    )
                    if (
                        order.exchange_order_type
                        is trading_enums.TradeOrderType.STOP_LOSS
                        and order.status.value == trading_enums.OrderStatus.OPEN.value
                    ):
                        if check_if_can_start_trailing(
                            order_group_settings=order_group_settings,
                            av_entry=order.created_last_price,
                            current_price=current_price,
                            trading_side=trading_side,
                        ):
                            if (
                                order_group_settings.stop_loss.sl_trail_type
                                == sl_settings.ManagedOrderSettingsSLTrailTypes.BREAK_EVEN_DESCRIPTION
                            ):
                                new_sl_price = await trailing_types.trail_to_break_even(
                                    maker.ctx,
                                    trading_side=trading_side,
                                    av_entry=order.created_last_price,
                                )
                            elif (
                                order_group_settings.stop_loss.sl_trail_type
                                == sl_settings.ManagedOrderSettingsSLTrailTypes.TRAILING_DESCRIPTION
                            ):
                                new_sl_price = (
                                    await trailing_types.trail_to_stop_loss_settings(
                                        maker,
                                        trading_side,
                                        order_group_settings,
                                        entry_price=order.created_last_price,
                                        current_price=current_price,
                                    )
                                )
                            elif (
                                order_group_settings.stop_loss.sl_trail_type
                                == sl_settings.ManagedOrderSettingsSLTrailTypes.TRAILING_INDICATOR_DESCRIPTION
                            ):
                                new_sl_price = await trailing_types.trail_to_indicator(
                                    maker=maker,
                                    order_group_settings=order_group_settings,
                                    orders_settings=order_settings,
                                )
                            if new_sl_price := adapt_sl_price_and_check_if_can_continue_trailing(
                                sl_trail_start_only_if_above_entry=order_group_settings.stop_loss.sl_trail_start_only_if_above_entry,
                                order=order,
                                new_sl_price=new_sl_price,
                                av_entry=order.created_last_price,
                                trading_side=trading_side,
                            ):
                                try:
                                    await editing.edit_order(
                                        maker.ctx, order, edited_stop_price=new_sl_price
                                    )
                                except Exception as error:
                                    maker.ctx.logger.exception(
                                        error,
                                        True,
                                        f"Error editing trailing stop loss. Error: {error}",
                                    )


def adapt_sl_price_and_check_if_can_continue_trailing(
    sl_trail_start_only_if_above_entry, order, new_sl_price, av_entry, trading_side
):
    if trading_side in (
        trading_enums.PositionSide.LONG.value,
        trading_enums.TradeOrderSide.BUY.value,
    ):
        if order.origin_price < new_sl_price:
            if av_entry < new_sl_price:
                return new_sl_price
            elif sl_trail_start_only_if_above_entry:
                return None
            else:
                return new_sl_price
    else:
        if order.origin_price > new_sl_price:
            if av_entry > new_sl_price:
                return new_sl_price
            elif sl_trail_start_only_if_above_entry:
                return None
            else:
                return new_sl_price
    return None


def check_if_can_start_trailing(
    order_group_settings, trading_side, av_entry, current_price
):
    if not order_group_settings.stop_loss.sl_trail_start_only_in_profit:
        return True
    elif trading_side in (
        trading_enums.PositionSide.LONG.value,
        trading_enums.TradeOrderSide.BUY.value,
    ):
        trail_start_price = (
            1 + (order_group_settings.stop_loss.sl_trail_start / 100)
        ) * av_entry
        if current_price >= trail_start_price:
            return True
    else:
        trail_start_price = (
            1 - (order_group_settings.stop_loss.sl_trail_start / 100)
        ) * av_entry
        if current_price <= trail_start_price:
            return True
