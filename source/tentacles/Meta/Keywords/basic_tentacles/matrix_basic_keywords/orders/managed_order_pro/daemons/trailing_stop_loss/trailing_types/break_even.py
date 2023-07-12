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
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_public_data as exchange_public_data
import octobot_trading.enums as trading_enums


async def trail_to_break_even(ctx, trading_side, av_entry:decimal.Decimal):
    fees = decimal.Decimal(exchange_public_data.symbol_fees(ctx)["taker"])
    if trading_side == trading_enums.PositionSide.LONG.value:
        break_even_price = (1 + (fees / 100)) * av_entry
    else:
        break_even_price = (1 - (fees) / 100) * av_entry
    return break_even_price
