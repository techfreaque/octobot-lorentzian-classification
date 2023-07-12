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
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.stop_loss as stop_loss
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_public_data as exchange_public_data
import tentacles.Meta.Keywords.scripting_library.orders.editing as editing
import tentacles.Meta.Keywords.scripting_library.orders.waiting as waiting


def trim_sl_long_price(sl_price, current_price, sl_max_p, sl_min_p):
    sl_in_p = (current_price - sl_price) / current_price * 100
    if sl_in_p > sl_max_p:
        return sl_max_p, (1 - (sl_max_p / 100)) * current_price
    elif sl_in_p < sl_min_p:
        return sl_min_p, (1 - (sl_min_p / 100)) * current_price
    return sl_in_p, sl_price


def trim_sl_short_price(sl_price, current_price, sl_max_p, sl_min_p):
    sl_in_p = (current_price - sl_price) / current_price * 100
    sl_max_p *= -1
    sl_min_p *= -1
    if sl_in_p < sl_max_p:
        return sl_max_p, (1 + (-sl_max_p / 100)) * current_price
    elif sl_in_p > sl_min_p:
        return sl_min_p, (1 + (-sl_min_p / 100)) * current_price
    return sl_in_p, sl_price


async def adjust_managed_stop_loss(maker, managed_orders_settings, managed_order_data):
    # edit stop loss to accurate values in real trading

    # wait for market order to be filled
    await waiting.wait_for_orders_close(
        maker.ctx, managed_order_data.created_orders, timeout=60
    )

    # get up-to-date entry filled price and size
    managed_order_data.entry_price = float(
        managed_order_data.created_orders[0].filled_price
    )
    managed_order_data.exit_amount = float(
        managed_order_data.created_orders[0].filled_quantity
    )

    # # wait for initial stop loss to be placed
    init_stop_order = await waiting.wait_for_stop_loss_open(
        maker.ctx,
        managed_order_data.exit_order_tag,
        managed_order_data.order_group,
        timeout=45,
    )

    (
        new_sl_price,
        managed_order_data.sl_in_p,
    ) = await stop_loss.get_manged_order_stop_loss(
        maker.ctx,
        managed_orders_settings,
        managed_order_data.trading_side,
        entry_price=managed_order_data.entry_price,
        sl_indicator_value=managed_order_data.sl_indicator_value,
    )
    # # update stop loss on exchange
    new_sl_price = exchange_public_data.get_digits_adapted_price(
        maker.ctx, decimal.Decimal(new_sl_price)
    )
    if init_stop_order:
        if init_stop_order.origin_price != new_sl_price:
            try:
                await editing.edit_order(
                    maker.ctx, order=init_stop_order, edited_stop_price=new_sl_price
                )
                managed_order_data.sl_in_d = float(new_sl_price)
            except (
                Exception
            ) as error:  # fails if we try to set an SL above the current price
                # retry one more time before giving up editing the order
                try:
                    await editing.edit_order(
                        maker.ctx, order=init_stop_order, edited_stop_price=new_sl_price
                    )
                    managed_order_data.sl_in_d = float(new_sl_price)
                except (
                    Exception
                ) as error:  # catch all errors to continue placing take profits
                    maker.ctx.logger.exception(
                        error,
                        True,
                        "Managed order: adjusting stop loss failed. This happened probably"
                        f" because the adjusted stop loss would have been trigger instantly error: {e}",
                    )

    else:
        maker.ctx.logger.error(
            "Managed Order: failed to get stop loss from exchange. "
            "Could not adjust stop loss based on filled price"
        )
        managed_order_data.enabled_order_group = False
    return managed_order_data
