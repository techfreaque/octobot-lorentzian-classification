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

import statistics as statistics
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.data.public_exchange_data as public_exchange_data
from tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.matrix_enums import (
    PriceDataSources,
)
import tentacles.Meta.Keywords.scripting_library.data.writing.plotting as plotting


async def stop_loss_analysis(
    maker, ctx, requested_long_sl, requested_short_sl, take_profit_in_p
):
    required_long_stops = []
    required_short_stops = []
    final_long_whitelist = []
    final_short_whitelist = []

    lows = None
    highs = None
    opens = None
    times = None
    data_len = None

    long_win_rates = {}
    short_win_rates = {}
    cache_key = str(take_profit_in_p)
    if maker.strategy_cache:
        for timestamp in maker.strategy_cache:
            for strategy_id in maker.strategy_cache[timestamp]:
                strategy_trading_side = (
                    maker.strategies[strategy_id].trading_side_key
                    if timestamp in maker.strategy_cache[strategy_id]
                    else None
                )
                if strategy_trading_side == "l":
                    final_long_whitelist.append(timestamp)
                else:
                    final_short_whitelist.append(timestamp)
        if final_long_whitelist:
            lows = await public_exchange_data.get_candles_(
                maker, PriceDataSources.LOW.value
            )
            highs = await public_exchange_data.get_candles_(
                maker, PriceDataSources.HIGH.value
            )
            opens = await public_exchange_data.get_candles_(
                maker, PriceDataSources.OPEN.value
            )
            times = await public_exchange_data.get_candles_(
                maker, PriceDataSources.TIME.value
            )
            data_len = len(times)
            tmp_long_whitelist = final_long_whitelist
            tmp_long_whitelist.sort()
            for candle_id in range(1, data_len + 1):
                try:
                    candle_time = times[candle_id]
                    if candle_time == tmp_long_whitelist[0]:
                        tmp_long_whitelist = tmp_long_whitelist[1:]
                        entry_price = opens[candle_id]

                        take_profit_target = entry_price * (
                            1 + (take_profit_in_p / 100)
                        )
                        for in_trade_candle_id in range(candle_id, data_len + 1):
                            try:
                                if highs[in_trade_candle_id] > take_profit_target:
                                    stop_loss_value = (
                                        (
                                            min(
                                                lows[candle_id : in_trade_candle_id + 1]
                                            )
                                            / entry_price
                                        )
                                        - 1
                                    ) * 100
                                    check_and_add_wins(
                                        long_win_rates,
                                        stop_loss_value,
                                        requested_long_sl,
                                    )
                                    required_long_stops.append(stop_loss_value)
                                    break
                            except IndexError:
                                stop_loss_value = (
                                    (min(lows[candle_id:]) / entry_price) - 1
                                ) * 100
                                check_and_add_wins(
                                    long_win_rates, stop_loss_value, requested_long_sl
                                )
                                required_long_stops.append(stop_loss_value)
                                break
                except IndexError:
                    break
            await ctx.set_cached_values(
                required_long_stops,
                value_key="l-sl" + cache_key,
                cache_keys=final_long_whitelist,
            )
            median_sl = [statistics.median(required_long_stops)] * data_len
            await ctx.set_cached_values(
                median_sl, value_key="ml-sl" + cache_key, cache_keys=times
            )

        if final_short_whitelist:
            lows = lows or await public_exchange_data.get_candles_(
                maker, PriceDataSources.LOW.value
            )
            highs = highs or await public_exchange_data.get_candles_(
                maker, PriceDataSources.HIGH.value
            )
            opens = opens or await public_exchange_data.get_candles_(
                maker, PriceDataSources.OPEN.value
            )
            times = times or await public_exchange_data.get_candles_(
                maker, PriceDataSources.TIME.value
            )
            data_len = data_len or len(times)

            tmp_short_whitelist = final_short_whitelist
            tmp_short_whitelist.sort()

            for candle_id in range(1, data_len + 1):
                try:
                    candle_time = times[candle_id]
                    if candle_time == tmp_short_whitelist[0]:
                        tmp_short_whitelist = tmp_short_whitelist[1:]
                        entry_price = opens[candle_id]
                        take_profit_target = entry_price * (
                            1 - (take_profit_in_p / 100)
                        )

                        for in_trade_candle_id in range(candle_id, data_len + 1):
                            try:
                                if lows[in_trade_candle_id] < take_profit_target:
                                    stop_loss_value = (
                                        (
                                            max(
                                                highs[
                                                    candle_id : in_trade_candle_id + 1
                                                ]
                                            )
                                            / entry_price
                                        )
                                        + 1
                                    ) * 100
                                    check_and_add_wins(
                                        short_win_rates,
                                        stop_loss_value,
                                        requested_short_sl,
                                        long=False,
                                    )
                                    required_short_stops.append(stop_loss_value)
                                    required_short_stops.append(stop_loss_value)
                                    break
                            except IndexError:
                                stop_loss_value = (
                                    (max(highs[candle_id:]) / entry_price) + 1
                                ) * 100
                                check_and_add_wins(
                                    short_win_rates,
                                    stop_loss_value,
                                    requested_short_sl,
                                    long=False,
                                )
                                required_short_stops.append(stop_loss_value)
                                break
                except IndexError:
                    break

            await ctx.set_cached_values(
                required_short_stops,
                value_key="s-sl" + cache_key,
                cache_keys=final_short_whitelist,
            )
            median_sl = [statistics.median(required_short_stops)] * data_len
            await ctx.set_cached_values(
                median_sl, value_key="ms-sl" + cache_key, cache_keys=times
            )

    compute_winrates(required_short_stops, short_win_rates)
    compute_winrates(required_long_stops, long_win_rates)

    await plotting.plot(
        ctx,
        "required short SL in percent",
        cache_value="s-sl" + cache_key,
        chart="sub-chart",
        mode="markers",
    )
    await plotting.plot(
        ctx,
        "required long SL in percent",
        cache_value="l-sl" + cache_key,
        chart="sub-chart",
        mode="markers",
    )
    await plotting.plot(
        ctx,
        "median long SL in percent",
        cache_value="ml-sl" + cache_key,
        chart="sub-chart",
    )
    await plotting.plot(
        ctx,
        "median short SL in percent",
        cache_value="ms-sl" + cache_key,
        chart="sub-chart",
    )

    return long_win_rates, short_win_rates


def check_and_add_wins(win_rates, stop_loss_value, requested_sl, long=True):
    for sl_percent in requested_sl:
        current_wins = win_rates.get(sl_percent, 0)
        if long:
            win_rates[sl_percent] = (
                current_wins + 1
                if sl_percent >= (stop_loss_value * -1)
                else current_wins
            )
        else:
            win_rates[sl_percent] = (
                current_wins + 1
                if (sl_percent <= (stop_loss_value * -1))
                else current_wins
            )


def compute_winrates(required_stops, win_rates):
    for target_percent in win_rates:
        win_rates[target_percent] = win_rates[target_percent] / (
            len(required_stops) / 100
        )


# async def take_profit_analysis(ctx, final_long_whitelist, final_short_whitelist):
#     if not statistics:
#         return
#     calc_req_stop_size = await user_inputs.user_input(ctx, "enable take profit analysis", "boolean", def_val=False)
#
#     if calc_req_stop_size:
#         stop_loss_in_p = await user_inputs.user_input(ctx, "stop loss target in % (to calculate required TP %)",
#                                                       "float", def_val=1, min_val=0)
#         required_long_tps = []
#         required_short_tps = []
#
#         lows = None
#         highs = None
#         opens = None
#         times = None
#         data_len = None
#
#         if final_short_whitelist:
#             lows = await exchange_public_data.Low(ctx, max_history=True)
#             highs = await exchange_public_data.High(ctx, max_history=True)
#             opens = await exchange_public_data.Open(ctx, max_history=True)
#             times = await exchange_public_data.Time(ctx, max_history=True)
#             data_len = len(times)
#             tmp_short_whitelist = final_short_whitelist
#             tmp_short_whitelist.sort()
#             for candle_id in range(1, data_len + 1):
#                 try:
#                     candle_time = times[candle_id]
#                     if candle_time == tmp_short_whitelist[0]:
#                         tmp_short_whitelist = tmp_short_whitelist[1:]
#                         entry_price = opens[candle_id]
#
#                         stop_loss_target = entry_price * (1 + (stop_loss_in_p / 100))
#                         for in_trade_candle_id in range(candle_id, data_len + 1):
#                             try:
#                                 if highs[in_trade_candle_id] > stop_loss_target:
#                                     required_short_tps.append(
#                                         ((min(lows[candle_id:in_trade_candle_id + 1]) / entry_price) + 1) * 100)
#                                     break
#                             except IndexError:
#                                 required_short_tps.append(((min(lows[candle_id:]) / entry_price) + 1) * 100)
#                                 break
#                 except IndexError:
#                     break
#             # try:
#             await ctx.set_cached_values(required_short_tps, value_key="s-tp", cache_keys=final_short_whitelist)
#             # except RuntimeError as e:  # todo
#             #     print(f"set cache error. {e}")
#             median_tp = [statistics.median(required_short_tps)] * data_len
#             # try:
#             await ctx.set_cached_values(median_tp, value_key="ms-tp", cache_keys=times)
#             # except RuntimeError as e:  # todo
#             #     print(f"set cache error. {e}")
#         if final_long_whitelist:
#             lows = lows or await exchange_public_data.Low(ctx, max_history=True)
#             highs = highs or await exchange_public_data.High(ctx, max_history=True)
#             opens = opens or await exchange_public_data.Open(ctx, max_history=True)
#             times = times or await exchange_public_data.Time(ctx, max_history=True)
#             data_len = data_len or len(times)
#
#             tmp_long_whitelist = final_long_whitelist
#             tmp_long_whitelist.sort()
#
#             for candle_id in range(1, data_len + 1):
#                 try:
#                     candle_time = times[candle_id]
#                     if candle_time == tmp_long_whitelist[0]:
#                         tmp_long_whitelist = tmp_long_whitelist[1:]
#                         entry_price = opens[candle_id]
#                         stop_loss_target = entry_price * (1 - (stop_loss_in_p / 100))
#
#                         for in_trade_candle_id in range(candle_id, data_len + 1):
#                             try:
#                                 if lows[in_trade_candle_id] <= stop_loss_target:
#                                     required_long_tps.append(
#                                         ((max(highs[candle_id:in_trade_candle_id + 1]) / entry_price) - 1) * 100)
#                                     break
#                             except IndexError:
#                                 required_long_tps.append(((max(highs[candle_id:]) / entry_price) - 1) * 100)
#                                 break
#                 except IndexError:
#                     break
#
#             await ctx.set_cached_values(required_long_tps, value_key="l-tp", cache_keys=final_long_whitelist)
#             median_tp = [statistics.median(required_long_tps)] * data_len
#             await ctx.set_cached_values(median_tp, value_key="ml-tp", cache_keys=times)
#         try:
#             await plotting.plot(ctx, "required short TP in percent", cache_value="s-tp", chart="sub-chart",
#                                 mode="markers")
#             await plotting.plot(ctx, "required long TP in percent", cache_value="l-tp", chart="sub-chart",
#                                 mode="markers")
#             await plotting.plot(ctx, "median long TP in percent", cache_value="ml-tp", chart="sub-chart")
#             await plotting.plot(ctx, "median short TP in percent", cache_value="ms-tp", chart="sub-chart")
#         except RuntimeError:
#             pass  # no cache available
