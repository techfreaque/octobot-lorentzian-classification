import typing
import numpy
import numpy.typing as npt

import octobot_commons.enums as enums
import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords
import octobot_trading.modes.script_keywords.context_management as context_management
import tentacles.Meta.Keywords.scripting_library.orders.order_types.market_order as market_order
import tentacles.Meta.Keywords.scripting_library.backtesting.backtesting_settings as backtesting_settings
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.tools.utilities as basic_utilities
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.ml_utils.utils as utils
import tentacles.Meta.Keywords.RunAnalysis.AnalysisKeywords.analysis_enums as analysis_enums
import tentacles.Trading.Mode.lorentzian_classification.settings as lorentzian_settings

try:
    import tentacles.Meta.Keywords.pro_tentacles.pro_keywords.orders.managed_order_pro.activate_managed_order as activate_managed_order
except (ImportError, ModuleNotFoundError):
    activate_managed_order = None


class LorentzianTradeExecution:
    trading_mode = None
    start_long_trades_cache: dict = {}
    start_short_trades_cache: dict = {}
    exit_long_trades_cache: dict = None
    exit_short_trades_cache: dict = None

    managend_orders_long_settings = None
    managend_orders_short_settings = None

    async def trade_live_candle(
        self,
        ctx: context_management.Context,
        order_settings: utils.LorentzianOrderSettings,
        symbol: str,
        start_short_trades: typing.List[bool],
        start_long_trades: typing.List[bool],
        exit_short_trades: typing.List[bool],
        exit_long_trades: typing.List[bool],
    ) -> None:
        s_time = basic_utilities.start_measure_time()
        if start_short_trades[-1]:
            await enter_short_trade(
                mode_producer=self,
                order_settings=order_settings,
                ctx=ctx,
                managend_orders_short_settings=self.managend_orders_short_settings,
            )
        if start_long_trades[-1]:
            await enter_long_trade(
                mode_producer=self,
                order_settings=order_settings,
                ctx=ctx,
                managend_orders_long_settings=self.managend_orders_long_settings,
            )
        has_exit_signals = len(exit_short_trades) and len(exit_long_trades)
        if has_exit_signals:
            if exit_short_trades[-1]:
                await exit_short_trade(ctx=ctx)
            if exit_long_trades[-1]:
                await exit_long_trade(ctx=ctx)
        basic_utilities.end_measure_time(
            s_time,
            f" Lorentzian Classification {symbol} - " "trading eventual singals",
        )

    async def _trade_cached_backtesting_candles_if_available(
        self, ctx: context_management.Context
    ) -> bool:
        if ctx.exchange_manager.is_backtesting:
            if ctx.time_frame in self.start_long_trades_cache:
                trigger_cache_timestamp = int(ctx.trigger_cache_timestamp)
                try:
                    if self.start_short_trades_cache[ctx.time_frame][
                        trigger_cache_timestamp
                    ]:
                        await enter_short_trade(
                            mode_producer=self,
                            ctx=ctx,
                            order_settings=self.trading_mode.order_settings,
                            managend_orders_short_settings=self.managend_orders_short_settings,
                        )
                    elif self.start_long_trades_cache[ctx.time_frame][
                        trigger_cache_timestamp
                    ]:
                        await enter_long_trade(
                            mode_producer=self,
                            ctx=ctx,
                            order_settings=self.trading_mode.order_settings,
                            managend_orders_long_settings=self.managend_orders_long_settings,
                        )
                    if (
                        self.exit_short_trades_cache
                        and self.exit_short_trades_cache[trigger_cache_timestamp]
                    ):
                        await exit_short_trade(ctx)
                    elif (
                        self.exit_long_trades_cache
                        and self.exit_long_trades_cache[trigger_cache_timestamp]
                    ):
                        await exit_long_trade(ctx)
                    return True
                except KeyError as error:
                    ctx.logger.debug(
                        f"No cached strategy signal for this candle - error: {error}"
                    )
                    return True
        return False

    def _cache_backtesting_signals(
        self,
        symbol: str,
        ctx: context_management.Context,
        s_time: float,
        candle_times: npt.NDArray[numpy.float64],
        start_short_trades: list,
        start_long_trades: list,
        exit_short_trades: list,
        exit_long_trades: list,
    ) -> None:
        # cache signals for backtesting
        has_exit_signals: bool = len(exit_short_trades) and len(exit_long_trades)
        if has_exit_signals:
            (
                candle_times,
                start_short_trades,
                start_long_trades,
                exit_long_trades,
                exit_short_trades,
            ) = basic_utilities.cut_data_to_same_len(
                (
                    candle_times,
                    start_short_trades,
                    start_long_trades,
                    exit_long_trades,
                    exit_short_trades,
                )
            )
        else:
            (
                candle_times,
                start_short_trades,
                start_long_trades,
            ) = basic_utilities.cut_data_to_same_len(
                (
                    candle_times,
                    start_short_trades,
                    start_long_trades,
                )
            )
        candle_times_to_whitelist: list = []
        self.start_short_trades_cache[ctx.time_frame] = {}
        self.start_long_trades_cache[ctx.time_frame] = {}
        if has_exit_signals:
            self.exit_long_trades_cache: dict = {}
            self.exit_short_trades_cache: dict = {}
        trades_count: int = 0
        for index, candle_time in enumerate(candle_times):
            candle_time: int = int(candle_time)
            self.start_short_trades_cache[ctx.time_frame][
                candle_time
            ] = start_short_trades[index]
            self.start_long_trades_cache[ctx.time_frame][
                candle_time
            ] = start_long_trades[index]
            if has_exit_signals:
                self.exit_long_trades_cache[candle_time] = exit_long_trades[index]
                self.exit_short_trades_cache[candle_time] = exit_short_trades[index]
                if exit_long_trades[index] or exit_short_trades[index]:
                    candle_times_to_whitelist.append(candle_time)
            if start_long_trades[index] or start_short_trades[index]:
                if start_long_trades[index]:
                    trades_count += 1
                if start_short_trades[index]:
                    trades_count += 1
                open_time: int = int(
                    candle_time
                    - (enums.TimeFramesMinutes[enums.TimeFrames(ctx.time_frame)] * 60)
                )
                candle_times_to_whitelist.append(candle_time)
                candle_times_to_whitelist.append(open_time)
        # if len(self.time_frame_filter) <= 1:
        backtesting_settings.register_backtesting_timestamp_whitelist(
            ctx, list(set(candle_times_to_whitelist))
        )
        basic_utilities.end_measure_time(
            s_time,
            f" Lorentzian Classification {symbol} - "
            "building strategy for "
            f"{ctx.time_frame} {trades_count} trades",
        )

    async def init_order_settings(self, ctx: context_management.Context, leverage: int):
        if self.trading_mode.order_settings.uses_managed_order:
            if self.trading_mode.order_settings.enable_long_orders:
                long_settings_name = "long_order_settings"
                await basic_keywords.user_input(
                    ctx,
                    long_settings_name,
                    "object",
                    None,
                    title="Long Trade Settings",
                    editor_options={
                        enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
                        analysis_enums.UserInputEditorOptionsTypes.ANT_ICON.value: "RiseOutlined",
                        enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                        enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                    },
                    # other_schema_values={
                    #     # analysis_enums.UserInputOtherSchemaValuesTypes.DISPLAY_AS_TAB.value: True
                    # },
                    parent_input_name=lorentzian_settings.ORDER_SETTINGS_NAME,
                )
                self.managend_orders_long_settings = (
                    await activate_managed_order.activate_managed_orders(
                        self,
                        parent_input_name=long_settings_name,
                        name_prefix="long",
                    )
                )
            if self.trading_mode.order_settings.enable_short_orders:
                short_settings_name = "short_order_settings"
                await basic_keywords.user_input(
                    ctx,
                    short_settings_name,
                    "object",
                    None,
                    title="Short Trade Settings",
                    editor_options={
                        enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
                        analysis_enums.UserInputEditorOptionsTypes.ANT_ICON.value: "FallOutlined",
                        enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                        enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                    },
                    other_schema_values={
                        # analysis_enums.UserInputOtherSchemaValuesTypes.DISPLAY_AS_TAB.value: True
                    },
                    parent_input_name=lorentzian_settings.ORDER_SETTINGS_NAME,
                )
                self.managend_orders_short_settings = (
                    await activate_managed_order.activate_managed_orders(
                        self,
                        parent_input_name=short_settings_name,
                        name_prefix="short",
                    )
                )
        else:
            await basic_keywords.set_leverage(ctx, leverage)


async def enter_short_trade(
    mode_producer,
    ctx: context_management.Context,
    order_settings: utils.LorentzianOrderSettings,
    managend_orders_short_settings,
):
    symbol_settings: utils.SymbolSettings = (
        mode_producer.trading_mode.data_source_settings.symbol_settings_by_symbols[
            ctx.symbol
        ]
    )
    if symbol_settings.enable_short_orders:
        if symbol_settings.inverse_signals:
            trading_side = "long"
            target_position = f"{order_settings.short_order_volume}"
        else:
            trading_side = "short"
            target_position = f"-{order_settings.short_order_volume}"
        if order_settings.uses_managed_order:
            await activate_managed_order.managed_order(
                mode_producer,
                trading_side=trading_side,
                orders_settings=managend_orders_short_settings,
            )
        else:
            await market_order.market(
                ctx,
                target_position=target_position,
            )
    elif symbol_settings.enable_long_orders:
        if symbol_settings.inverse_signals:
            await exit_short_trade(ctx=ctx)
        else:
            await exit_long_trade(ctx=ctx)


async def enter_long_trade(
    mode_producer,
    ctx: context_management.Context,
    order_settings: utils.LorentzianOrderSettings,
    managend_orders_long_settings,
):
    symbol_settings: utils.SymbolSettings = (
        mode_producer.trading_mode.data_source_settings.symbol_settings_by_symbols[
            ctx.symbol
        ]
    )

    if symbol_settings.enable_long_orders:
        if symbol_settings.inverse_signals:
            trading_side = "short"
            target_position = f"-{order_settings.long_order_volume}"
        else:
            trading_side = "long"
            target_position = f"{order_settings.long_order_volume}"
        if order_settings.uses_managed_order:
            await activate_managed_order.managed_order(
                mode_producer,
                trading_side=trading_side,
                orders_settings=managend_orders_long_settings,
            )
        else:
            await market_order.market(
                ctx,
                target_position=target_position,
            )
    elif symbol_settings.enable_short_orders:
        if symbol_settings.inverse_signals:
            await exit_long_trade(ctx=ctx)
        else:
            await exit_short_trade(ctx=ctx)


async def exit_short_trade(ctx: context_management.Context):
    await market_order.market(ctx, target_position=0, reduce_only=True)


async def exit_long_trade(ctx: context_management.Context):
    await market_order.market(ctx, target_position=0, reduce_only=True)
