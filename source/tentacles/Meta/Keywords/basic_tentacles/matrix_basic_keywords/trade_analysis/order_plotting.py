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

from octobot_trading.enums import TradeOrderSide
import octobot_trading.modes.script_keywords.basic_keywords.account_balance as account_balance
import octobot_trading.modes.script_keywords.basic_keywords.user_inputs as user_inputs
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.data.exchange_private_data as exchange_private_data
import tentacles.Meta.Keywords.scripting_library.data.writing.plotting as plotting


async def plot_orders_if_enabled(ctx, parent_input):
    # plot orders
    activate_plot_orders = await user_inputs.user_input(
        ctx,
        "Plot orders",
        "boolean",
        def_val=True,
        parent_input_name=parent_input,
        show_in_summary=False,
        show_in_optimizer=False,
    )
    if activate_plot_orders:
        plot_orders(ctx)


async def plot_orders(ctx):
    # plot orders
    _open_orders = (
        ctx.exchange_manager.exchange_personal_data.orders_manager.get_open_orders(
            symbol=ctx.symbol
        )
    )
    long_tp_list = []
    long_sl_list = []
    long_limit_list = []
    # long_entry_list = []
    short_tp_list = []
    short_sl_list = []
    short_limit_list = []
    # short_entry_list = []
    for order in _open_orders:
        if order.exchange_order_type.name == "STOP_LOSS":
            if order.side == TradeOrderSide.BUY:
                short_sl_list.append(float(order.origin_price))
            else:
                long_sl_list.append(float(order.origin_price))

            # todo change based on trades
            # entry_list.append(float(order.created_last_price))
        elif order.reduce_only is True:
            if order.side == TradeOrderSide.BUY:
                short_tp_list.append(float(order.origin_price))
            else:
                long_tp_list.append(float(order.origin_price))

        elif order.exchange_order_type.name == "LIMIT":
            if order.side == TradeOrderSide.BUY:
                long_limit_list.append(float(order.origin_price))
            else:
                if ctx.exchange_manager.is_spot_only:
                    long_tp_list.append(float(order.origin_price))
                else:
                    short_limit_list.append(float(order.origin_price))

        # elif order.exchange_order_type.name == "MARKET":
        #     if order.side == TradeOrderSide.BUY:
        #         long_entry_list.append(float(order.origin_price))
        #     else:
        #         short_entry_list.append(float(order.origin_price))

    # if ctx.exchange_manager.is_backtesting:
    value_key_prefix = "b" if ctx.exchange_manager.is_backtesting else "l"
    if long_tp_list:
        await ctx.set_cached_value(value=long_tp_list, value_key=f"{value_key_prefix}ltp")
    if long_sl_list:
        await ctx.set_cached_value(value=long_sl_list, value_key=f"{value_key_prefix}lsl")
    if long_limit_list:
        await ctx.set_cached_value(value=long_limit_list, value_key=f"{value_key_prefix}llmt")
    if short_tp_list:
        await ctx.set_cached_value(value=short_tp_list, value_key=f"{value_key_prefix}stp")
    if short_sl_list:
        await ctx.set_cached_value(value=short_sl_list, value_key=f"{value_key_prefix}ssl")
    if short_limit_list:
        await ctx.set_cached_value(value=short_limit_list, value_key=f"{value_key_prefix}slmt")
    try:
        await plotting.plot(
            ctx,
            "Short stop losses",
            cache_value=f"{value_key_prefix}ssl",
            mode="markers",
            chart="main-chart",
            color="yellow",
            shift_to_open_candle_time=False,
        )
        await plotting.plot(
            ctx,
            "Long stop losses",
            cache_value=f"{value_key_prefix}lsl",
            mode="markers",
            chart="main-chart",
            color="yellow",
            shift_to_open_candle_time=False,
        )
        await plotting.plot(
            ctx,
            "Short take profits",
            cache_value=f"{value_key_prefix}stp",
            mode="markers",
            chart="main-chart",
            color="green",
            shift_to_open_candle_time=False,
        )
        await plotting.plot(
            ctx,
            "Long take profits",
            cache_value=f"{value_key_prefix}ltp",
            mode="markers",
            chart="main-chart",
            color="magenta",
            shift_to_open_candle_time=False,
        )
        await plotting.plot(
            ctx,
            "Short entry limit orders",
            cache_value=f"{value_key_prefix}slmt",
            mode="markers",
            chart="main-chart",
            color="red",
            shift_to_open_candle_time=False,
        )
        await plotting.plot(
            ctx,
            "Long entry limit orders",
            cache_value=f"{value_key_prefix}llmt",
            mode="markers",
            chart="main-chart",
            color="blue",
            shift_to_open_candle_time=False,
        )
    except RuntimeError:
        pass  # no cache
    # else:
    #     candle_time = await exchange_public_data.current_candle_time(ctx)
    #     if long_tp_list:
    #         await plotting.plot(
    #             ctx,
    #             "Long take profits",
    #             y=[long_tp_list],
    #             x=[candle_time],
    #             mode="markers",
    #             chart="main-chart",
    #             color="magenta",
    #             shift_to_open_candle_time=False,
    #         )
    #     if short_tp_list:
    #         await plotting.plot(
    #             ctx,
    #             "Short take profits",
    #             y=[short_tp_list],
    #             x=[candle_time],
    #             mode="markers",
    #             chart="main-chart",
    #             color="green",
    #             shift_to_open_candle_time=False,
    #         )
    #     if long_sl_list:
    #         await plotting.plot(
    #             ctx,
    #             "Long stop losses",
    #             y=[long_sl_list],
    #             x=[candle_time],
    #             mode="markers",
    #             chart="main-chart",
    #             color="yellow",
    #             shift_to_open_candle_time=False,
    #         )
    #     if short_sl_list:
    #         await plotting.plot(
    #             ctx,
    #             "Short stop losses",
    #             y=[short_sl_list],
    #             x=[candle_time],
    #             mode="markers",
    #             chart="main-chart",
    #             color="yellow",
    #             shift_to_open_candle_time=False,
    #         )
    #     if long_limit_list:
    #         await plotting.plot(
    #             ctx,
    #             "Long entry limit orders",
    #             y=[long_limit_list],
    #             x=[candle_time],
    #             mode="markers",
    #             chart="main-chart",
    #             color="blue",
    #             shift_to_open_candle_time=False,
    #         )
    #     if short_limit_list:
    #         await plotting.plot(
    #             ctx,
    #             "Short entry limit orders",
    #             y=[short_limit_list],
    #             x=[candle_time],
    #             mode="markers",
    #             chart="main-chart",
    #             color="red",
    #             shift_to_open_candle_time=False,
    #         )


async def plot_current_position(ctx, parent_input):
    enable_plot_position = await user_inputs.user_input(
        ctx,
        "Plot open position",
        "boolean",
        def_val=True,
        parent_input_name=parent_input,
        show_in_summary=False,
        show_in_optimizer=False,
    )
    if enable_plot_position:
        try:
            current_pos = exchange_private_data.get_position_size(ctx)
        except AttributeError:
            print("Plot position error")
            current_pos = 0
        if ctx.exchange_manager.is_backtesting:
            try:
                await ctx.set_cached_value(value=float(current_pos), value_key="op")
            except:
                pass
            await plotting.plot(
                ctx,
                "current position",
                cache_value="op",
                chart="sub-chart",
                color="blue",
                shift_to_open_candle_time=False,
                mode="markers",
                own_yaxis=True,
            )
        else:
            try:
                await ctx.set_cached_value(value=float(current_pos), value_key="l-op")
            except:
                pass

            await plotting.plot(
                ctx,
                "current position",
                cache_value="l-op",
                chart="sub-chart",
                color="blue",
                shift_to_open_candle_time=False,
                mode="markers",
                own_yaxis=True,
            )


async def plot_average_entry(ctx, parent_input):
    enable_plot_entry = await user_inputs.user_input(
        ctx,
        "Plot average entry",
        "boolean",
        def_val=True,
        parent_input_name=parent_input,
        show_in_summary=False,
        show_in_optimizer=False,
    )
    if enable_plot_entry and ctx.exchange_manager.is_future:
        try:
            current_entry = (
                ctx.exchange_manager.exchange_personal_data.positions_manager.positions[
                    ctx.symbol
                ].entry_price
            )
        except (AttributeError, KeyError):
            return
        key = "b-" if ctx.exchange_manager.is_backtesting else "l-"
        if current_entry:
            await ctx.set_cached_value(value=float(current_entry), value_key=key + "ae")
        await plotting.plot(
            ctx,
            "current average entry",
            cache_value=key + "ae",
            chart="main-chart",
            color="blue",
            shift_to_open_candle_time=False,
            mode="markers",
        )


async def plot_balances(ctx, parent_input):
    enable_plot_balances = await user_inputs.user_input(
        ctx,
        "Plot balances",
        "boolean",
        def_val=True,
        show_in_summary=False,
        show_in_optimizer=False,
        parent_input_name=parent_input,
    )
    if enable_plot_balances:
        key = "b-" if ctx.exchange_manager.is_backtesting else "l-"
        current_total_balance = (
            ctx.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value
        )

        await ctx.set_cached_value(
            value=float(current_total_balance), value_key=key + "cb"
        )
        await plotting.plot(
            ctx,
            "current balance",
            cache_value=key + "cb",
            chart="sub-chart",
            color="blue",
            shift_to_open_candle_time=False,
            mode="markers",
        )
        current_available_balance = await account_balance.available_account_balance(ctx)
        await ctx.set_cached_value(
            value=float(current_available_balance), value_key=key + "cab"
        )
        await plotting.plot(
            ctx,
            "current available balance",
            cache_value=key + "cab",
            chart="sub-chart",
            color="blue",
            shift_to_open_candle_time=False,
            mode="markers",
        )
