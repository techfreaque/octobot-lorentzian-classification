import time
import octobot_trading.util as util
import octobot_commons.enums as commons_enums
import octobot_trading.enums as trading_enums
import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords
import octobot_trading.modes.script_keywords.context_management as context_management
import octobot_trading.modes.script_keywords.basic_keywords.user_inputs as user_inputs
import tentacles.Meta.Keywords.matrix_library.matrix_basic_keywords.matrix_enums as matrix_enums
from tentacles.Meta.Keywords.matrix_library.matrix_basic_keywords.mode.mode_base.abstract_mode_base import (
    AbstractBaseModeProducer,
)
import tentacles.Meta.Keywords.matrix_library.matrix_basic_keywords.tools.utilities as utilities
import tentacles.Meta.Keywords.matrix_library.matrix_basic_keywords.user_inputs2.select_time_frame as select_time_frame
import tentacles.Meta.Keywords.scripting_library.data.writing.plotting as plotting


class MatrixModeProducer(AbstractBaseModeProducer):

    action = None
    # TODO remove - find solution
    INDICATOR_CLASS = None

    consumable_indicator_cache: dict = {}
    standalone_indicators: dict = {}
    initialized_managed_order_settings: dict = {}

    any_ping_pong_mode_active: bool = False

    plot_settings_name = "plot_settings"
    default_live_plotting_mode: str = (
        matrix_enums.LivePlottingModes.PLOT_RECORDING_MODE.value
    )
    default_backtest_plotting_mode: str = (
        matrix_enums.BacktestPlottingModes.DISABLE_PLOTTING.value
    )
    live_plotting_modes: list = [
        matrix_enums.LivePlottingModes.DISABLE_PLOTTING.value,
        matrix_enums.LivePlottingModes.REPLOT_VISIBLE_HISTORY.value,
        matrix_enums.LivePlottingModes.PLOT_RECORDING_MODE.value,
    ]
    backtest_plotting_modes: list = [
        matrix_enums.BacktestPlottingModes.ENABLE_PLOTTING.value,
        matrix_enums.BacktestPlottingModes.DISABLE_PLOTTING.value,
    ]

    backtest_plotting_mode: str = None
    live_plotting_mode: str = matrix_enums.LivePlottingModes.PLOT_RECORDING_MODE.value

    enable_plot: bool = True
    plot_signals: bool = False
    enable_ping_pong: bool = None

    # todo remove
    live_recording_mode: bool = None
    trigger_time_frames: list = None

    def __init__(self, channel, config, trading_mode, exchange_manager):
        super().__init__(channel, config, trading_mode, exchange_manager)
        self.candles_manager: dict = {}
        self.ctx: context_management.Context = None
        self.candles: dict = {}

    async def _register_and_apply_required_user_inputs(self, context):
        if self.trading_mode.ALLOW_CUSTOM_TRIGGER_SOURCE:
            # register activating topics user input
            activation_topic_values = [
                commons_enums.ActivationTopics.FULL_CANDLES.value,
                commons_enums.ActivationTopics.IN_CONSTRUCTION_CANDLES.value,
            ]
            await user_inputs.get_activation_topics(
                context,
                commons_enums.ActivationTopics.FULL_CANDLES.value,
                activation_topic_values,
            )
        if context.exchange_manager.is_future:
            await util.wait_for_topic_init(
                self.exchange_manager,
                self.CONFIG_INIT_TIMEOUT,
                commons_enums.InitializationEventExchangeTopics.CONTRACTS.value,
            )

    async def handle_trigger_time_frame(self):
        self.trigger_time_frames = await select_time_frame.set_trigger_time_frames(
            self.ctx
        )
        self.cancel_non_trigger_time_frames()

    def cancel_non_trigger_time_frames(self):
        select_time_frame.cancel_non_trigger_time_frames(
            self.ctx, self.trigger_time_frames
        )

    def disable_trading_if_just_started(self):
        if not self.exchange_manager.is_backtesting:
            running_seconds = time.time() - interfaces.get_bot_api().get_start_time()
            if running_seconds < 25:
                self.ctx.enable_trading = False

    def allow_trading_only_on_execution(self, ctx, allow_trading_without_action=True):
        if not self.exchange_manager.is_backtesting:
            if self.action in (
                matrix_enums.TradingModeCommands.EXECUTE,
                matrix_enums.TradingModeCommands.OHLC_CALLBACK,
                matrix_enums.TradingModeCommands.KLINE_CALLBACK,
            ):
                ctx.enable_trading = True
            elif self.action in (matrix_enums.TradingModeCommands.OHLC_CALLBACK,):
                ctx.enable_trading = True
                self.disable_trading_if_just_started()
            else:
                if allow_trading_without_action:
                    ctx.enable_trading = True
                else:
                    ctx.enable_trading = False

    async def set_position_mode_to_one_way(self):
        if self.exchange_manager.is_future:
            try:
                await self.exchange_manager.trader.set_position_mode(
                    self.ctx.symbol, trading_enums.PositionMode.ONE_WAY
                )
            except Exception as e:
                # not important
                pass

    async def build_and_trade_strategies_live(self):
        m_time = utilities.start_measure_time()

        utilities.end_measure_live_time(self.ctx, m_time, " matrix mode - live trading")

    async def build_strategies_backtesting_cache(self):
        s_time = utilities.start_measure_time(
            " matrix mode - building backtesting cache"
        )

        utilities.end_measure_time(
            s_time,
            f" matrix mode - building strategy for "
            f"{self.ctx.time_frame} {len(self.any_trading_timestamps)} trades",
        )

    async def trade_strategies_backtesting(self):
        m_time = utilities.start_measure_time()

        utilities.end_measure_time(
            m_time,
            " matrix mode - warning backtesting candle took longer than expected",
            min_duration=1,
        )

    async def init_plot_settings(self):
        await basic_keywords.user_input(
            self.ctx,
            self.plot_settings_name,
            commons_enums.UserInputTypes.OBJECT,
            def_val=None,
            title="Plot settings",
            show_in_summary=False,
            show_in_optimizer=False,
            other_schema_values={
                "grid_columns": 12,
                "description": "Use those options wisely as it will slow "
                "down the backtesting speed by quit a lot",
            },
        )
        await self.init_plotting_modes(self.plot_settings_name, self.plot_settings_name)

    async def init_plotting_modes(self, live_parent_input, backtesting_parent_input):
        self.backtest_plotting_mode = await basic_keywords.user_input(
            self.ctx,
            "backtest_plotting_mode",
            commons_enums.UserInputTypes.OPTIONS,
            title="Backtest plotting mode",
            def_val=self.default_backtest_plotting_mode,
            options=self.backtest_plotting_modes,
            show_in_summary=False,
            show_in_optimizer=False,
            parent_input_name=backtesting_parent_input,
        )
        self.plot_signals = await basic_keywords.user_input(
            self.ctx,
            "plot_signals",
            commons_enums.UserInputTypes.BOOLEAN,
            title="Plot signals",
            def_val=False,
            show_in_summary=False,
            show_in_optimizer=False,
            parent_input_name=backtesting_parent_input,
        )
        if self.exchange_manager.is_backtesting:
            if (
                self.backtest_plotting_mode
                == matrix_enums.BacktestPlottingModes.DISABLE_PLOTTING.value
            ):
                self.enable_plot = False
            elif (
                self.backtest_plotting_mode
                == matrix_enums.BacktestPlottingModes.ENABLE_PLOTTING.value
            ):
                self.enable_plot = True
        else:
            self.live_plotting_mode = await basic_keywords.user_input(
                self.ctx,
                "live_plotting_mode",
                commons_enums.UserInputTypes.OPTIONS,
                title="Live plotting mode",
                def_val=self.default_live_plotting_mode,
                options=self.live_plotting_modes,
                show_in_summary=False,
                show_in_optimizer=False,
                parent_input_name=live_parent_input,
            )
            if (
                self.live_plotting_mode
                == matrix_enums.LivePlottingModes.PLOT_RECORDING_MODE.value
            ):
                self.live_recording_mode = True
                self.enable_plot = True
            elif (
                self.live_plotting_mode
                == matrix_enums.LivePlottingModes.DISABLE_PLOTTING.value
            ):
                self.enable_plot = False
                self.live_recording_mode = True
                await plotting.disable_candles_plot(self.ctx)
            elif (
                self.live_plotting_mode
                == matrix_enums.LivePlottingModes.REPLOT_VISIBLE_HISTORY.value
            ):
                self.live_recording_mode = False
                self.enable_plot = True
