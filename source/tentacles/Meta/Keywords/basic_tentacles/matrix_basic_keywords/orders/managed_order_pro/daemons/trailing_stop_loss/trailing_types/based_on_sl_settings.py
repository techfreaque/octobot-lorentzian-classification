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

import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.stop_loss as stop_loss_calculators


async def trail_to_stop_loss_settings(
    maker, trading_side, order_group_settings, entry_price, current_price
):
    sl_price, sl_in_p = await stop_loss_calculators.get_manged_order_stop_loss(
        maker=maker,
        stop_loss_settings=order_group_settings.stop_loss,
        trading_side=trading_side,
        entry_price=entry_price,
        current_price=current_price,
    )
    return sl_price
