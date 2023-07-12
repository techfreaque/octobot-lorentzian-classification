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

import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.trade_analysis as trade_analysis


async def handle_trade_analysis_for_current_candle(ctx, parent_input: str):
    await trade_analysis.plot_orders_if_enabled(ctx, parent_input)
    await trade_analysis.plot_current_position(ctx, parent_input)
    await trade_analysis.plot_average_entry(ctx, parent_input)
    await trade_analysis.plot_balances(ctx, parent_input)


async def handle_trade_analysis_for_backtesting_first_candle(ctx, maker):
    all_winrates = {}
    for tp_target in maker.trade_analysis_mode_settings["requested_long_tp"]:
        long_win_rates, short_win_rates = await trade_analysis.stop_loss_analysis(
            maker,
            ctx,
            requested_long_sl=maker.trade_analysis_mode_settings["requested_long_sl"],
            requested_short_sl=maker.trade_analysis_mode_settings["requested_short_sl"],
            take_profit_in_p=tp_target,
        )
        all_winrates[tp_target] = {
            "long_win_rates": long_win_rates,
            "short_win_rates": short_win_rates,
        }
    return all_winrates
