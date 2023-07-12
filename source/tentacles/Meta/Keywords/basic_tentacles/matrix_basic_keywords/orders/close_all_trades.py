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

import octobot_trading.personal_data as trading_personal_data
import octobot_trading.enums as trading_enums
from octobot_trading.modes.script_keywords import basic_keywords
import decimal


async def close_all_positions(ctx):
    should_buy = None
    if ctx.exchange_manager.is_future:
        try:
            open_positions = (
                ctx.exchange_manager.exchange_personal_data.positions_manager.positions[
                    ctx.symbol
                ].size
            )
            if open_positions:
                should_buy = (
                    ctx.exchange_manager.exchange_personal_data.positions_manager.positions[
                        ctx.symbol
                    ].side
                    == trading_enums.PositionSide.SHORT.value
                )
        except:
            open_positions = None
            should_buy = False
    else:
        asset, _ = ctx.symbol.split("/")
        open_positions = ctx.exchange_manager.exchange_personal_data.portfolio_manager.portfolio.portfolio[
            asset
        ].total

    if open_positions:
        await ctx.trader.cancel_open_orders(ctx.symbol, cancel_loaded_orders=True)
        # fees_currency_side = ctx.exchange_manager.exchange.get_pair_future_contract(ctx.symbol).get_fees_currency_side()
        order = trading_personal_data.create_order_instance(
            trader=ctx.trader,
            order_type=trading_enums.TraderOrderType.BUY_MARKET
            if should_buy
            else trading_enums.TraderOrderType.SELL_MARKET,
            symbol=ctx.symbol,
            current_price=decimal.Decimal(ctx.trigger_value[1]),
            quantity=open_positions,
            price=decimal.Decimal(ctx.trigger_value[1]),
            filled_price=decimal.Decimal(ctx.trigger_value[1]),
            # fees_currency_side=fees_currency_side
        )

        order = await ctx.trader.create_order(order)
        ctx.just_created_orders.append(order)
        await basic_keywords.store_orders(ctx, [order], ctx.exchange_manager)
