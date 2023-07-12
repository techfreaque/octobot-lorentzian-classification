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
import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords
import octobot_trading.enums as trading_enums
import octobot_commons.enums as commons_enums
from octobot_trading.modes.script_keywords.context_management import Context
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.data.public_exchange_data as public_exchange_data
from tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.matrix_enums import (
    PriceDataSources,
)
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.position_sizing as position_sizing
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.stop_loss as stop_loss
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.take_profit as take_profit
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.daemons.ping_pong.ping_pong_storage.storage as storage
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.all_settings as all_settings
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.entry_types as entry_types
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.sl_settings as sl_settings
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.utilities as matrix_utilities
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_public_data as exchange_public_data
import tentacles.Meta.Keywords.scripting_library.data.writing.plotting as plotting
import tentacles.Meta.Keywords.scripting_library.orders.grouping as grouping
import tentacles.Meta.Keywords.scripting_library.orders.order_types as order_types
import tentacles.Meta.Keywords.scripting_library.orders.waiting as waiting
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.scaled_orders as scaled_orders


class ManagedOrderPlacement:
    stop_loss_tag: str = None
    take_profit_tag: str = None

    entry_type: str = None

    average_stop_loss_price: decimal.Decimal = None
    average_take_profit_price: decimal.Decimal = None
    average_entry_price: decimal.Decimal = None
    entry_quantity: decimal.Decimal = None

    managed_orders_settings: all_settings.ManagedOrdersSettings = None
    group_orders_settings: all_settings.ManagedOrdersSettings = None

    market_fee: decimal.Decimal = None
    limit_fee: decimal.Decimal = None
    entry_fees: decimal.Decimal = None

    position_size: decimal.Decimal = None
    max_position_size: decimal.Decimal = None
    current_open_risk: decimal.Decimal = None
    max_buying_power: decimal.Decimal = None
    place_entries: bool = None
    entry_side: str = None
    exit_side: str = None
    exit_order_tag: str = None
    entry_order_tag: str = None
    order_tag_id: int = None

    current_price_val: decimal.Decimal = None
    trading_side: str = None

    created_orders: list = None
    calculated_entries: list = None
    stop_loss_prices: list
    take_profit_prices: list
    order_amounts: list
    tentacle = None

    async def place_managed_entry_and_exits(
        self,
        maker,
        order_block,
        trading_side,
        managed_orders_settings,
        group_orders_settings,
        forced_amount: decimal.Decimal,
        order_preview_mode: bool,
    ):
        self.created_orders = []
        self.created_orders = []
        self.calculated_entries = []
        self.stop_loss_prices = []
        self.take_profit_prices = []
        self.order_amounts = []
        self.trading_side = trading_side
        self.managed_orders_settings = managed_orders_settings
        self.group_orders_settings = group_orders_settings

        self.entry_side, self.exit_side = matrix_utilities.get_trading_sides(
            trading_side
        )

        # ensure leverage is up to date
        # if not maker.ctx.exchange_manager.is_backtesting:
        await basic_keywords.set_leverage(maker.ctx, managed_orders_settings.leverage)
        try:
            await basic_keywords.set_partial_take_profit_stop_loss(maker.ctx)
        except NotImplementedError:
            pass
        self.current_price_val = await exchange_public_data.current_live_price(
            maker.ctx
        )

        # if (
        #     self.managed_orders_settings.entry_type
        #     == entry_types.ManagedOrderSettingsEntryTypes.SINGLE_TRY_LIMIT_IN_DESCRIPTION
        # ):
        #     # entry try limit in
        #     # todo + handle on backtesting (maybe use always 1m to check if it got filled)
        #     # entry_type = "limit"
        #     # created_orders = await order_types.trailing_limit(ctx, amount=position_size_limit, side=entry_side,
        #     #                                                   min_offset=0, max_offset=0,
        #     #                                                   slippage_limit=self.managed_orders_settings.slippage_limit,
        #     #                                                   tag=entry_order_tag, stop_loss_offset=sl_offset,
        #     #                                                   stop_loss_tag=sl_tag)
        #     # # wait for limit to get filled
        #     # if tag_triggered.tagged_order_unfilled(entry_order_tag):
        #     #     unfilled_amount = tag_triggered.tagged_order_unfilled_amount(entry_order_tag)
        #     #     if unfilled_amount != position_size_limit:
        #     #         position_size_market = 50  # todo calc smaller size cause of fees
        #     #     created_orders = await order_types.market(ctx, side=entry_side, amount=position_size_market,
        #     #                                               tag=entry_order_tag, stop_loss_offset=sl_offset,
        #     #                                               stop_loss_tag=sl_tag)
        #     raise NotImplementedError("managed order: try limit in not implemented yet")

        # entry market in only
        if (
            self.group_orders_settings.entry.entry_type
            == entry_types.ManagedOrderSettingsEntryTypes.SINGLE_MARKET_IN_DESCRIPTION
        ):
            self.set_entry_type(entry_type="market")
            (
                self.position_size,
                self.max_position_size,
                self.current_open_risk,
                self.max_buying_power,
                bundled_sl_offset,
                bundled_sl_tag,
                bundled_sl_group,
                bundled_tp_offset,
                bundled_tp_tag,
                bundled_tp_group,
                self.place_entries,
                self.entry_order_tag,
                order_tag_id,
                stop_loss_price,
                take_profit_price,
            ) = await self.get_single_order_data(
                maker,
                order_block=order_block,
                group_orders_settings=group_orders_settings,
                entry_price=self.current_price_val,
                entry_side=self.entry_side,
                forced_amount=forced_amount,
            )
            if self.place_entries:
                self.calculated_entries = [self.current_price_val]
                if stop_loss_price:
                    self.stop_loss_prices = [stop_loss_price]
                if take_profit_price:
                    self.take_profit_prices = [take_profit_price]
                self.order_amounts = [self.position_size]
                if not order_preview_mode:
                    self.created_orders = await order_types.market(
                        maker.ctx,
                        side=self.entry_side,
                        amount=self.position_size,
                        tag=self.entry_order_tag,
                        stop_loss_offset=bundled_sl_offset,
                        stop_loss_tag=bundled_sl_tag,
                        stop_loss_group=bundled_sl_group,
                        take_profit_offset=bundled_tp_offset,
                        take_profit_tag=bundled_tp_tag,
                        take_profit_group=bundled_tp_group,
                    )
                    self.add_to_ping_pong_storage_if_enabled(
                        maker,
                        order_tag_id,
                        self.created_orders,
                        self.calculated_entries,
                    )
                    if bundled_tp_group:
                        await grouping.enable_group(bundled_tp_group, True)

        # entry limit in only
        elif (
            self.group_orders_settings.entry.entry_type
            == entry_types.ManagedOrderSettingsEntryTypes.SINGLE_LIMIT_IN_DESCRIPTION
        ):
            self.set_entry_type(entry_type="limit")

            if self.entry_side == "buy":
                self.average_entry_price = self.current_price_val * (
                    1 - (self.group_orders_settings.entry.limit_offset / 100)
                )
            else:
                self.average_entry_price = self.current_price_val * (
                    1 + (self.group_orders_settings.entry.limit_offset / 100)
                )
            (
                self.position_size,
                self.max_position_size,
                self.current_open_risk,
                self.max_buying_power,
                bundled_sl_offset,
                bundled_sl_tag,
                bundled_sl_group,
                bundled_tp_offset,
                bundled_tp_tag,
                bundled_tp_group,
                self.place_entries,
                self.entry_order_tag,
                self.order_tag_id,
                stop_loss_price,
                take_profit_price,
            ) = await self.get_single_order_data(
                maker,
                order_block=order_block,
                group_orders_settings=group_orders_settings,
                entry_price=self.average_entry_price,
                entry_side=self.entry_side,
                forced_amount=forced_amount,
            )
            if self.place_entries:
                self.calculated_entries = [self.average_entry_price]
                if stop_loss_price:
                    self.stop_loss_prices = [stop_loss_price]
                if take_profit_price:
                    self.take_profit_prices = [take_profit_price]
                self.order_amounts = [self.position_size]
                if not order_preview_mode:
                    self.created_orders = await order_types.limit(
                        maker.ctx,
                        side=self.entry_side,
                        amount=self.position_size,
                        offset=f"@{self.average_entry_price}",
                        tag=self.entry_order_tag,
                        stop_loss_offset=bundled_sl_offset,
                        stop_loss_tag=bundled_sl_tag,
                        stop_loss_group=bundled_sl_group,
                        take_profit_offset=bundled_tp_offset,
                        take_profit_tag=bundled_tp_tag,
                        take_profit_group=bundled_tp_group,
                    )
                    self.add_to_ping_pong_storage_if_enabled(
                        maker,
                        order_tag_id,
                        self.created_orders,
                        self.calculated_entries,
                    )
                    if bundled_tp_group:
                        await grouping.enable_group(bundled_tp_group, True)
        # entry grid limits
        elif (
            self.group_orders_settings.entry.entry_type
            == entry_types.ManagedOrderSettingsEntryTypes.SCALED_STATIC_DESCRIPTION
            or self.group_orders_settings.entry.entry_type
            == entry_types.ManagedOrderSettingsEntryTypes.SCALED_DYNAMIC_DESCRIPTION
        ):
            self.set_entry_type(entry_type="limit")
            self.place_entries = False
            for grid in self.group_orders_settings.entry.entry_grids.values():
                if (
                    self.group_orders_settings.entry.entry_type
                    == entry_types.ManagedOrderSettingsEntryTypes.SCALED_DYNAMIC_DESCRIPTION
                ):
                    if self.entry_side == trading_enums.TradeOrderSide.BUY.value:
                        scale_from = f"{grid.from_level*-1}%"
                        scale_to = f"{grid.to_level*-1}%"
                    else:
                        scale_from = f"{grid.from_level}%"
                        scale_to = f"{grid.to_level}%"
                else:
                    scale_from = f"@{grid.from_level}"
                    scale_to = f"@{grid.to_level}"
                (
                    created_orders,
                    place_entries,
                    calculated_entries,
                    stop_loss_prices,
                    take_profit_prices,
                    order_amounts,
                    order_tag_id,
                ) = await scaled_orders.scaled_order(
                    maker,
                    order_block=order_block,
                    current_price=self.current_price_val,
                    side=self.entry_side,
                    scale_from=scale_from,
                    scale_to=scale_to,
                    order_count=grid.order_count,
                    group_orders_settings=self.group_orders_settings,
                    forced_amount=forced_amount,
                    value_distribution_type=grid.value_distribution_type,
                    value_growth_factor=grid.value_growth_factor,
                    price_distribution_type=grid.price_distribution_type,
                    price_growth_factor=grid.price_growth_factor,
                    order_preview_mode=order_preview_mode,
                )
                if place_entries:
                    self.place_entries = self.place_entries or place_entries
                    self.created_orders += created_orders
                    self.calculated_entries += calculated_entries
                    self.stop_loss_prices += stop_loss_prices
                    self.take_profit_prices += take_profit_prices
                    self.order_amounts += order_amounts
                    if not order_preview_mode:
                        self.add_to_ping_pong_storage_if_enabled(
                            maker,
                            order_tag_id,
                            created_orders,
                            calculated_entries,
                        )

        # # entry time grid orders
        # elif (
        #     self.group_orders_settings.entry.entry_type
        #     == entry_types.ManagedOrderSettingsEntryTypes.SCALED_OVER_TIME_DESCRIPTION
        # ):
        #     raise NotImplementedError("time grid orders not implemented yet")
        # else:
        #     raise NotImplementedError("Unknown entry order type")
        if order_preview_mode:
            await self.plot_order_preview(maker)

        # if (
        #     not maker.ctx.exchange_manager.is_backtesting
        #     and self.entry_type == "market"
        # ):
        #     pass
        #     # TODO wait for filled market price and actual quantity for all orders
        #     # TODO wait for updated entry price

        # if len(self.created_orders) > 1:
        #     quantity = decimal.Decimal("0")
        #     total_position_cost = decimal.Decimal("0")
        #     for order in self.created_orders:
        #         if isinstance(order, dict):
        #             quantity += decimal.Decimal(str(order["order_amount"]))
        #             total_position_cost += decimal.Decimal(
        #                 str(order["order_amount"])
        #             ) * decimal.Decimal(str(order["entry_price"]))
        #         else:
        #             quantity += order.origin_quantity
        #             total_position_cost += order.origin_quantity * order.origin_price
        #     self.entry_quantity = float(str(quantity))
        #     self.average_entry_price = (
        #         float(str(total_position_cost)) / self.entry_quantity
        #     )
        # else:
        #     self.entry_quantity = float(str(self.created_orders[0].origin_quantity))
        #     self.average_entry_price = float(str(self.created_orders[0].origin_price))

    async def plot_order_preview(self, maker):
        if self.calculated_entries:
            times = await public_exchange_data.get_candles_(
                maker, PriceDataSources.TIME.value
            )
            additional_values_by_key = {}
            history_size = 200
            if self.stop_loss_prices:
                stop_loss_prices = list_decimal_to_float(self.stop_loss_prices)
                additional_values_by_key["stp_pr"] = [
                    stop_loss_prices for i in range(history_size)
                ]
            if self.take_profit_prices:
                take_profit_prices = list_decimal_to_float(self.take_profit_prices)
                additional_values_by_key["tp_pr"] = [
                    take_profit_prices for i in range(history_size)
                ]
            calculated_entries = list_decimal_to_float(self.calculated_entries)
            order_amounts = list_decimal_to_float(self.order_amounts)
            additional_values_by_key["amt_pr"] = [
                order_amounts for i in range(history_size)
            ]
            total_value = 0
            for index, price in enumerate(calculated_entries):
                total_value += price * order_amounts[index]
            additional_values_by_key["avrg_pr"] = [
                total_value / sum(order_amounts) for i in range(history_size)
            ]
            ctx: Context = maker.ctx

            await ctx.reset_cached_values(
                ["ntry_pr", "stp_pr", "tp_pr", "amt_pr", "avrg_pr"]
            )
            await ctx.set_cached_values(
                values=[calculated_entries for i in range(history_size)],
                cache_keys=times[-history_size:],
                value_key="ntry_pr",
                additional_values_by_key=additional_values_by_key,
                # tentacle_name="OrderManagerPro",
                flush_if_necessary=True,
            )
            await plotting.plot(
                maker.ctx,
                title="Entry Preview",
                cache_value="ntry_pr",
                mode="markers",
                line_shape=None,
                chart=commons_enums.PlotCharts.MAIN_CHART.value,
            )
            await plotting.plot(
                maker.ctx,
                title="Average Entry Price Preview",
                cache_value="avrg_pr",
                mode="markers",
                line_shape=None,
                chart=commons_enums.PlotCharts.MAIN_CHART.value,
            )
            await plotting.plot(
                maker.ctx,
                title="Stop Loss Preview",
                cache_value="stp_pr",
                mode="markers",
                line_shape=None,
                chart=commons_enums.PlotCharts.MAIN_CHART.value,
            )
            await plotting.plot(
                maker.ctx,
                title="Take Profit Preview",
                cache_value="tp_pr",
                mode="markers",
                line_shape=None,
                chart=commons_enums.PlotCharts.MAIN_CHART.value,
            )
            await plotting.plot(
                maker.ctx,
                title="Amount Preview",
                cache_value="amt_pr",
                mode="markers",
                line_shape=None,
                chart=commons_enums.PlotCharts.SUB_CHART.value,
            )

    def add_to_ping_pong_storage_if_enabled(
        self,
        maker,
        order_tag_id,
        created_orders,
        calculated_entries,
    ):
        if (
            not self.group_orders_settings.ping_pong.ping_pong_mode_enabled
            or not self.created_orders
            or (self.created_orders[0] is None and len(self.created_orders) == 1)
        ):
            return
        ping_pong_storage: storage.PingPongStorage = storage.get_ping_pong_storage(
            maker.exchange_manager
        )
        ping_pong_storage.set_ping_pong_data(
            group_key=f"{self.group_orders_settings.order_manager_group_id}",
            order_group_id=order_tag_id,
            created_orders=created_orders,
            calculated_entries=calculated_entries,
        )

    async def get_single_order_data(
        self,
        maker,
        order_block,
        group_orders_settings,
        entry_price,
        entry_side,
        forced_amount: decimal.Decimal = None,
    ):
        stop_loss_price, stop_loss_percent = await stop_loss.get_manged_order_stop_loss(
            maker,
            order_block=order_block,
            stop_loss_settings=group_orders_settings.stop_loss,
            trading_side=self.trading_side,
            entry_price=entry_price,
            current_price=self.current_price_val,
        )
        (
            position_size,
            max_position_size,
            current_open_risk,
            max_buying_power,
            place_entries,
            entry_order_tag,
            tp_order_tag,
            sl_order_tag,
            order_tag_id,
        ) = await position_sizing.get_manged_order_position_size(
            maker=maker,
            position_size_settings=group_orders_settings.position_size,
            trading_side=self.trading_side,
            entry_side=entry_side,
            entry_price=entry_price,
            entry_order_type=self.entry_type,
            stop_loss_percent=stop_loss_percent,
            order_tag_prefix=group_orders_settings.order_tag_prefix,
            forced_amount=forced_amount,
            recreate_exits=False,
        )
        if place_entries:
            exit_group = await group_orders_settings.create_managed_order_group(
                maker.ctx
            )
            (
                bundled_sl_offset,
                bundled_sl_tag,
                bundled_sl_group,
            ) = get_bundled_parameters(
                price=stop_loss_price,
                tag=sl_order_tag,
                group=exit_group,
                is_bundled=True,
            )
            self.average_take_profit_price = take_profit.get_manged_order_take_profits(
                maker,
                order_block=order_block,
                take_profit_settings=group_orders_settings.take_profit,
                entry_side=entry_side,
                current_price=self.current_price_val,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                entry_fee=self.entry_fees,
                market_fee=self.managed_orders_settings.market_fee,
            )
            (
                bundled_tp_offset,
                bundled_tp_tag,
                bundled_tp_group,
            ) = get_bundled_parameters(
                price=self.average_take_profit_price,
                tag=tp_order_tag,
                group=exit_group,
                is_bundled=True,
            )
            (
                entry_order_tag,
                bundled_sl_tag,
                bundled_tp_tag,
            ) = matrix_utilities.add_order_counter_to_tags(
                order_id=0,
                entry_order_tag=entry_order_tag,
                bundled_sl_tag=bundled_sl_tag,
                bundled_tp_tag=bundled_tp_tag,
            )
            return (
                position_size,
                max_position_size,
                current_open_risk,
                max_buying_power,
                bundled_sl_offset,
                bundled_sl_tag,
                bundled_sl_group,
                bundled_tp_offset,
                bundled_tp_tag,
                bundled_tp_group,
                place_entries,
                entry_order_tag,
                order_tag_id,
                stop_loss_price,
                self.average_take_profit_price,
            )
        return (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )

    async def handle_managed_real_trading_orders(self, ctx):
        if (
            sl_settings.ManagedOrderSettingsSLTypes.NO_SL_DESCRIPTION
            != self.managed_orders_settings.sl_type
        ):
            # todo create task - takes ages and blocks from finishing - but wait for that with the notification
            if self.entry_type == "market":
                pass
                # edit stop loss to accurate values once market is filled
                # await asyncio.sleep(10)
                # try:
                #     await stop_losses.adjust_managed_stop_loss(ctx, self.managed_orders_settings, self)
                # except Exception as e:
                #     ctx.logger.error(f"Managed Order: adapting stop loss based on filled price failed. (error: {e})")
                #     self.enabled_order_group = False
                #     # in case it fails continue anyway creating take profits
            else:  # limit orders
                # for limit orders we wait for the stop loss to be placed
                await waiting.wait_for_stop_loss_open(
                    ctx, self.created_orders, timeout=60
                )

    def get_name(self):
        return "OrderManagerPro"

    def set_entry_type(self, entry_type):
        self.entry_type = entry_type
        self.entry_fees = (
            self.managed_orders_settings.limit_fee
            if entry_type == "limit"
            else self.managed_orders_settings.market_fee
        )


def get_bundled_tp_offset(bundled_tp_calculator, entry_price, stop_loss_price):
    if bundled_tp_calculator:
        take_profit_price = bundled_tp_calculator(
            decimal.Decimal(str(entry_price)), decimal.Decimal(str(stop_loss_price))
        )
        return f"@{take_profit_price}"
    return None


def get_bundled_sl_offset(stop_loss_price: float, is_bundled: bool) -> None or float:
    if is_bundled:
        return f"@{stop_loss_price}"
    return None


def get_bundled_parameters(
    price: decimal.Decimal, tag: str, group, is_bundled: bool
) -> tuple:
    if price and is_bundled:
        return f"@{price}", tag, group
    return None, None, None


def list_decimal_to_float(decimal_list):
    return [float(str(value)) for value in decimal_list]
