# ported to python by Max https://github.com/techfreaque

# This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
# this evaluator is based on the trading view indicator from ©jdehorty
# https://www.tradingview.com/script/WhBzgfDu-Machine-Learning-Lorentzian-Classification/


# ====================
# ==== Background ====
# ====================

# When using Machine Learning algorithms like K-Nearest Neighbors, choosing an
# appropriate distance metric is essential. Euclidean Distance is often used as
# the default distance metric, but it may not always be the best choice. This is
# because market data is often significantly impacted by proximity to significant
# world events such as FOMC Meetings and Black Swan events. These major economic
# events can contribute to a warping effect analogous a massive object's
# gravitational warping of Space-Time. In financial markets, this warping effect
# operates on a continuum, which can analogously be referred to as "Price-Time".

# To help to better account for this warping effect, Lorentzian Distance can be
# used as an alternative distance metric to Euclidean Distance. The geometry of
# Lorentzian Space can be difficult to visualize at first, and one of the best
# ways to intuitively understand it is through an example involving 2 feature
# dimensions (z=2). For purposes of this example, let's assume these two features
# are Relative Strength Index (RSI) and the Average Directional Index (ADX). In
# reality, the optimal number of features is in the range of 3-8, but for the sake
# of simplicity, we will use only 2 features in this example.

# Fundamental Assumptions:
# (1) We can calculate RSI and ADX for a given chart.
# (2) For simplicity, values for RSI and ADX are assumed to adhere to a Gaussian
#     distribution in the range of 0 to 100.
# (3) The most recent RSI and ADX value can be considered the origin of a coordinate
#     system with ADX on the x-axis and RSI on the y-axis.

# Distances in Euclidean Space:
# Measuring the Euclidean Distances of historical values with the most recent point
# at the origin will yield a distribution that resembles Figure 1 (below).

#                        [RSI]
#                          |
#                          |
#                          |
#                      ...:::....
#                .:.:::••••••:::•::..
#              .:•:.:•••::::••::••....::.
#             ....:••••:••••••••::••:...:•.
#            ...:.::::::•••:::•••:•••::.:•..
#            ::•:.:•:•••••••:.:•::::::...:..
#  |--------.:•••..•••••••:••:...:::•:•:..:..----------[ADX]
#  0        :•:....:•••••::.:::•••::••:.....
#           ::....:.:••••••••:•••::••::..:.
#            .:...:••:::••••••••::•••....:
#              ::....:.....:•::•••:::::..
#                ..:..::••..::::..:•:..
#                    .::..:::.....:
#                          |
#                          |
#                          |
#                          |
#                         _|_ 0
#
#        Figure 1: Neighborhood in Euclidean Space

# Distances in Lorentzian Space:
# However, the same set of historical values measured using Lorentzian Distance will
# yield a different distribution that resembles Figure 2 (below).

#
#                         [RSI]
#  ::..                     |                    ..:::
#   .....                   |                  ......
#    .••••::.               |               :••••••.
#     .:•••••:.             |            :::••••••.
#       .•••••:...          |         .::.••••••.
#         .::•••••::..      |       :..••••••..
#            .:•••••••::.........::••••••:..
#              ..::::••••.•••••••.•••••••:.
#                ...:•••••••.•••••••••::.
#                  .:..••.••••••.••••..
#  |---------------.:•••••••••••••••••.---------------[ADX]
#  0             .:•:•••.••••••.•••••••.
#              .••••••••••••••••••••••••:.
#            .:••••••••••::..::.::••••••••:.
#          .::••••••::.     |       .::•••:::.
#         .:••••••..        |          :••••••••.
#       .:••••:...          |           ..•••••••:.
#     ..:••::..             |              :.•••••••.
#    .:•....                |               ...::.:••.
#   ...:..                  |                   :...:••.
#  :::.                     |                       ..::
#                          _|_ 0
#
#       Figure 2: Neighborhood in Lorentzian Space


# Observations:
# (1) In Lorentzian Space, the shortest distance between two points is not
#     necessarily a straight line, but rather, a geodesic curve.
# (2) The warping effect of Lorentzian distance reduces the overall influence
#     of outliers and noise.
# (3) Lorentzian Distance becomes increasingly different from Euclidean Distance
#     as the number of nearest neighbors used for comparison increases.


import typing
import numpy
import numpy.typing as npt
import tulipy

import octobot_commons.enums as enums
import octobot_trading.modes.script_keywords.context_management as context_management
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_public_data as exchange_public_data
import tentacles.Meta.Keywords.scripting_library.data.writing.plotting as plotting
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.ml_utils.classification_functions.classification_utils as classification_utils

import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.ml_utils.kernel_functions.kernel as kernel
import tentacles.Trading.Mode.lorentzian_classification.trade_execution as trade_execution
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.ml_utils.utils as utils
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.ml_utils.ml_extensions_2.ml_extensions as ml_extensions

import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.tools.utilities as basic_utilities
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.plottings.plots as matrix_plots
import tentacles.Meta.Keywords.basic_tentacles.basic_modes.mode_base.abstract_producer_base as abstract_producer_base
import tentacles.Meta.Keywords.basic_tentacles.basic_modes.mode_base.producer_base as producer_base

try:
    from tentacles.Evaluator.Util.candles_util import CandlesUtil
except (ModuleNotFoundError, ImportError) as error:
    raise RuntimeError("CandlesUtil tentacle is required to use HLC3") from error


class LorentzianClassificationScript(
    abstract_producer_base.AbstractBaseModeProducer,
    producer_base.MatrixProducerBase,
    trade_execution.LorentzianTradeExecution,
):
    def __init__(self, channel, config, trading_mode, exchange_manager):
        abstract_producer_base.AbstractBaseModeProducer.__init__(
            self, channel, config, trading_mode, exchange_manager
        )
        producer_base.MatrixProducerBase.__init__(
            self, channel, config, trading_mode, exchange_manager
        )
        self.start_long_trades_cache: dict = {}
        self.start_short_trades_cache: dict = {}

    async def evaluate_lorentzian_classification(
        self,
        ctx: context_management.Context,
    ):
        this_symbol_settings: utils.SymbolSettings = (
            self.trading_mode.data_source_settings.symbol_settings_by_symbols[
                self.trading_mode.symbol
            ]
        )
        await self.init_order_settings(
            ctx, leverage=self.trading_mode.order_settings.leverage
        )
        if not this_symbol_settings.trade_on_this_pair:
            return

        if await self._trade_cached_backtesting_candles_if_available(ctx):
            return
        s_time = basic_utilities.start_measure_time(
            f" Lorentzian Classification {self.trading_mode.symbol} -"
        )
        data_source_symbol: str = this_symbol_settings.get_data_source_symbol_name()
        (
            candle_closes,
            candle_highs,
            candle_lows,
            candles_hlc3,
            candles_ohlc4,
            user_selected_candles,
            candle_times,
        ) = await self._get_candle_data(
            ctx,
            candle_source_name=self.trading_mode.data_source_settings.source,
            data_source_symbol=data_source_symbol,
        )
        data_length: int = len(candle_highs)
        _filters: utils.Filter = self._get_all_filters(
            candle_closes,
            data_length,
            candles_ohlc4,
            candle_highs,
            candle_lows,
            user_selected_candles,
        )
        (
            alerts_bullish,
            alerts_bearish,
            is_bullishs,
            is_bearishs,
            is_bearish_changes,
            is_bullish_changes,
            is_bullish_cross_alerts,
            is_bearish_cross_alerts,
            kernel_estimate,
            yhat2,
            is_bearish_rates,
            was_bullish_rates,
            is_bullish_rates,
            was_bearish_rates,
        ) = kernel.get_kernel_data(
            self.trading_mode.kernel_settings, user_selected_candles, data_length
        )

        feature_arrays: utils.FeatureArrays = self._get_feature_arrays(
            candle_closes=candle_closes,
            candle_highs=candle_highs,
            candle_lows=candle_lows,
            candles_hlc3=candles_hlc3,
        )
        y_train_series: npt.NDArray[
            numpy.bool_
        ] = classification_utils.get_y_train_series(
            candle_closes,
            candle_highs,
            candle_lows,
            self.trading_mode.classification_settings.training_data_settings,
        )

        # cut all historical data to same length
        # for numpy and loop indizies being aligned
        (
            y_train_series,
            _filters.filter_all,
            _filters.is_uptrend,
            _filters.is_downtrend,
            candle_closes,
            candle_highs,
            candle_lows,
            candle_times,
            candles_hlc3,
            user_selected_candles,
            alerts_bullish,
            alerts_bearish,
            is_bullishs,
            is_bearishs,
            is_bearish_changes,
            is_bullish_changes,
            is_bullish_cross_alerts,
            is_bearish_cross_alerts,
            kernel_estimate,
            yhat2,
            is_bearish_rates,
            was_bullish_rates,
            is_bullish_rates,
            was_bearish_rates,
        ) = basic_utilities.cut_data_to_same_len(
            (
                y_train_series,
                _filters.filter_all,
                _filters.is_uptrend,
                _filters.is_downtrend,
                candle_closes,
                candle_highs,
                candle_lows,
                candle_times,
                candles_hlc3,
                user_selected_candles,
                alerts_bullish,
                alerts_bearish,
                is_bullishs,
                is_bearishs,
                is_bearish_changes,
                is_bullish_changes,
                is_bullish_cross_alerts,
                is_bearish_cross_alerts,
                kernel_estimate,
                yhat2,
                is_bearish_rates,
                was_bullish_rates,
                is_bullish_rates,
                was_bearish_rates,
            ),
            reference_length=feature_arrays.cut_data_to_same_len(),
        )

        cutted_data_length: int = feature_arrays.cut_data_to_same_len(
            reference_length=len(candle_closes)
        )
        if (
            not self.exchange_manager.is_backtesting
            and self.trading_mode.display_settings.is_plot_recording_mode
        ):
            max_bars_back_index: int = (
                cutted_data_length - 200 if cutted_data_length > 200 else 0
            )
        else:
            max_bars_back_index: int = self._get_max_bars_back_index(cutted_data_length)

        # =================================
        # ==== Next Bar Classification ====
        # =================================

        # This model specializes specifically in predicting the direction of price
        # action over the course of the next classification_settings.only_train_on_every_x_bars.

        previous_signals: list = [utils.SignalDirection.neutral]
        historical_predictions: list = []
        bars_since_red_entry: int = 5  # dont trigger exits on loop start
        bars_since_green_entry: int = 5  # dont trigger exits on loop start

        start_long_trades: list = []
        start_short_trades: list = []
        exit_short_trades: list = []
        exit_long_trades: list = []
        is_buy_signals: list = []
        is_sell_signals: list = []

        basic_utilities.end_measure_time(
            s_time,
            f" Lorentzian Classification {self.trading_mode.symbol} - calculating full history indicators",
        )
        s_time = basic_utilities.start_measure_time(
            f" Lorentzian Classification {self.trading_mode.symbol} - classifying candles"
        )
        for candle_index in range(max_bars_back_index, cutted_data_length):
            (
                bars_since_green_entry,
                bars_since_red_entry,
            ) = classification_utils.classify_current_candle(
                order_settings=self.trading_mode.order_settings,
                classification_settings=self.trading_mode.classification_settings,
                y_train_series=y_train_series,
                current_candle_index=candle_index,
                feature_arrays=feature_arrays,
                historical_predictions=historical_predictions,
                _filters=_filters,
                previous_signals=previous_signals,
                is_bullishs=is_bullishs,
                is_bearishs=is_bearishs,
                # alerts_bullish=alerts_bullish,
                # alerts_bearish=alerts_bearish,
                # is_bearish_changes=is_bearish_changes,
                # is_bullish_changes=is_bullish_changes,
                bars_since_red_entry=bars_since_red_entry,
                bars_since_green_entry=bars_since_green_entry,
                start_long_trades=start_long_trades,
                start_short_trades=start_short_trades,
                exit_short_trades=exit_short_trades,
                exit_long_trades=exit_long_trades,
                is_buy_signals=is_buy_signals,
                is_sell_signals=is_sell_signals,
            )
        if ctx.exchange_manager.is_backtesting:
            self._cache_backtesting_signals(
                symbol=self.trading_mode.symbol,
                ctx=ctx,
                s_time=s_time,
                candle_times=candle_times,
                start_short_trades=start_short_trades,
                start_long_trades=start_long_trades,
                exit_short_trades=exit_short_trades,
                exit_long_trades=exit_long_trades,
            )
        else:
            basic_utilities.end_measure_time(
                s_time,
                f" Lorentzian Classification {self.trading_mode.symbol} -"
                " classifying candles",
            )
            await self.trade_live_candle(
                ctx=ctx,
                order_settings=self.trading_mode.order_settings,
                symbol=self.trading_mode.symbol,
                start_short_trades=start_short_trades,
                start_long_trades=start_long_trades,
                exit_short_trades=exit_short_trades,
                exit_long_trades=exit_long_trades,
            )
        s_time = basic_utilities.start_measure_time()
        await self._handle_plottings(
            ctx=ctx,
            this_symbol_settings=this_symbol_settings,
            y_train_series=y_train_series,
            _filters=_filters,
            candle_closes=candle_closes,
            candle_highs=candle_highs,
            candle_lows=candle_lows,
            candle_times=candle_times,
            candles_hlc3=candles_hlc3,
            candles_ohlc4=candles_ohlc4,
            feature_arrays=feature_arrays,
            alerts_bullish=alerts_bullish,
            alerts_bearish=alerts_bearish,
            is_bullishs=is_bullishs,
            is_bearishs=is_bearishs,
            is_bearish_changes=is_bearish_changes,
            is_bullish_changes=is_bullish_changes,
            is_bullish_cross_alerts=is_bullish_cross_alerts,
            is_bearish_cross_alerts=is_bearish_cross_alerts,
            kernel_estimate=kernel_estimate,
            yhat2=yhat2,
            is_bearish_rates=is_bearish_rates,
            was_bullish_rates=was_bullish_rates,
            is_bullish_rates=is_bullish_rates,
            was_bearish_rates=was_bearish_rates,
            historical_predictions=historical_predictions,
            start_long_trades=start_long_trades,
            start_short_trades=start_short_trades,
            exit_short_trades=exit_short_trades,
            exit_long_trades=exit_long_trades,
            previous_signals=previous_signals,
            is_buy_signals=is_buy_signals,
            is_sell_signals=is_sell_signals,
        )
        basic_utilities.end_measure_time(
            s_time,
            f" Lorentzian Classification {self.trading_mode.symbol} - storing plots",
        )

    def _get_ma_filters(
        self, candle_closes: npt.NDArray[numpy.float64], data_length: int
    ) -> typing.Tuple[
        npt.NDArray[numpy.bool_],
        npt.NDArray[numpy.bool_],
        npt.NDArray[numpy.bool_],
        npt.NDArray[numpy.bool_],
    ]:
        if self.trading_mode.filter_settings.use_ema_filter:
            filter_ema_candles, filter_ema = basic_utilities.cut_data_to_same_len(
                (
                    candle_closes,
                    tulipy.ema(
                        candle_closes, self.trading_mode.filter_settings.ema_period
                    ),
                )
            )
            is_ema_uptrend: npt.NDArray[numpy.bool_] = filter_ema_candles > filter_ema
            is_ema_downtrend: npt.NDArray[numpy.bool_] = filter_ema_candles < filter_ema
        else:
            is_ema_uptrend: npt.NDArray[numpy.bool_] = numpy.repeat(True, data_length)
            is_ema_downtrend: npt.NDArray[numpy.bool_] = is_ema_uptrend
        if self.trading_mode.filter_settings.use_sma_filter:
            filter_sma_candles, filter_sma = basic_utilities.cut_data_to_same_len(
                (
                    candle_closes,
                    tulipy.sma(
                        candle_closes, self.trading_mode.filter_settings.sma_period
                    ),
                )
            )
            is_sma_uptrend: npt.NDArray[numpy.bool_] = filter_sma_candles > filter_sma
            is_sma_downtrend: npt.NDArray[numpy.bool_] = filter_sma_candles < filter_sma
        else:
            is_sma_uptrend: npt.NDArray[numpy.bool_] = numpy.repeat(True, data_length)
            is_sma_downtrend: npt.NDArray[numpy.bool_] = is_sma_uptrend
        return is_ema_uptrend, is_ema_downtrend, is_sma_uptrend, is_sma_downtrend

    async def _handle_plottings(
        self,
        ctx: context_management.Context,
        this_symbol_settings: utils.SymbolSettings,
        y_train_series: npt.NDArray[numpy.int64],
        _filters: utils.Filter,
        candle_closes: npt.NDArray[numpy.float64],
        candle_highs: npt.NDArray[numpy.float64],
        candle_lows: npt.NDArray[numpy.float64],
        candle_times: npt.NDArray[numpy.float64],
        candles_hlc3: npt.NDArray[numpy.float64],
        candles_ohlc4: npt.NDArray[numpy.float64],
        feature_arrays: utils.FeatureArrays,
        alerts_bullish: npt.NDArray[numpy.bool_],
        alerts_bearish: npt.NDArray[numpy.bool_],
        is_bullishs: npt.NDArray[numpy.bool_],
        is_bearishs: npt.NDArray[numpy.bool_],
        is_bearish_changes: npt.NDArray[numpy.bool_],
        is_bullish_changes: npt.NDArray[numpy.bool_],
        is_bullish_cross_alerts: npt.NDArray[numpy.bool_],
        is_bearish_cross_alerts: npt.NDArray[numpy.bool_],
        kernel_estimate: npt.NDArray[numpy.float64],
        yhat2: npt.NDArray[numpy.float64],
        is_bearish_rates: npt.NDArray[numpy.bool_],
        was_bullish_rates: npt.NDArray[numpy.bool_],
        is_bullish_rates: npt.NDArray[numpy.bool_],
        was_bearish_rates: npt.NDArray[numpy.bool_],
        historical_predictions: list,
        start_long_trades: list,
        start_short_trades: list,
        exit_short_trades: list,
        exit_long_trades: list,
        previous_signals: list,
        is_buy_signals: list,
        is_sell_signals: list,
    ) -> None:
        slightly_below_lows: npt.NDArray[numpy.float64] = candle_lows * 0.999
        slightly_above_highs: npt.NDArray[numpy.float64] = candle_highs * 1.001
        # use_own_y_axis: bool = this_symbol_settings.use_custom_pair
        cache_key_prefix: str = "b-" if self.exchange_manager.is_backtesting else "l-"

        await self._handle_full_history_plottings(
            ctx=ctx,
            cache_key_prefix=cache_key_prefix,
            this_symbol_settings=this_symbol_settings,
            y_train_series=y_train_series,
            _filters=_filters,
            candle_closes=candle_closes,
            candle_highs=candle_highs,
            candle_lows=candle_lows,
            candle_times=candle_times,
            candles_hlc3=candles_hlc3,
            candles_ohlc4=candles_ohlc4,
            feature_arrays=feature_arrays,
            alerts_bullish=alerts_bullish,
            alerts_bearish=alerts_bearish,
            is_bullishs=is_bullishs,
            is_bearishs=is_bearishs,
            is_bearish_changes=is_bearish_changes,
            is_bullish_changes=is_bullish_changes,
            is_bullish_cross_alerts=is_bullish_cross_alerts,
            is_bearish_cross_alerts=is_bearish_cross_alerts,
            kernel_estimate=kernel_estimate,
            yhat2=yhat2,
            is_bearish_rates=is_bearish_rates,
            was_bullish_rates=was_bullish_rates,
            is_bullish_rates=is_bullish_rates,
            was_bearish_rates=was_bearish_rates,
            slightly_below_lows=slightly_below_lows,
            slightly_above_highs=slightly_above_highs,
        )
        await self._handle_short_history_plottings(
            ctx=ctx,
            cache_key_prefix=cache_key_prefix,
            use_own_y_axis=this_symbol_settings.use_custom_pair,
            historical_predictions=historical_predictions,
            candle_times=candle_times,
            start_long_trades=start_long_trades,
            start_short_trades=start_short_trades,
            exit_short_trades=exit_short_trades,
            exit_long_trades=exit_long_trades,
            slightly_below_lows=slightly_below_lows,
            slightly_above_highs=slightly_above_highs,
            previous_signals=previous_signals,
            is_buy_signals=is_buy_signals,
            is_sell_signals=is_sell_signals,
        )

    async def _handle_short_history_plottings(
        self,
        ctx: context_management.Context,
        cache_key_prefix: str,
        use_own_y_axis: bool,
        historical_predictions: list,
        candle_times: npt.NDArray[numpy.float64],
        start_long_trades: list,
        start_short_trades: list,
        exit_short_trades: list,
        exit_long_trades: list,
        slightly_below_lows: npt.NDArray[numpy.float64],
        slightly_above_highs: npt.NDArray[numpy.float64],
        previous_signals: list,
        is_buy_signals: list,
        is_sell_signals: list,
    ) -> None:
        (
            historical_predictions,
            candle_times,
            start_long_trades,
            start_short_trades,
            slightly_below_lows,
            slightly_above_highs,
            previous_signals,
            is_buy_signals,
            is_sell_signals,
        ) = basic_utilities.cut_data_to_same_len(
            (
                historical_predictions,
                candle_times,
                start_long_trades,
                start_short_trades,
                slightly_below_lows,
                slightly_above_highs,
                previous_signals,
                is_buy_signals,
                is_sell_signals,
            )
        )
        await matrix_plots.plot_conditional(
            ctx=ctx,
            is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
            title="Start Long Trades",
            signals=start_long_trades,
            values=slightly_below_lows,
            times=candle_times,
            value_key=f"{cache_key_prefix}st-l",
            color="green",
        )
        await matrix_plots.plot_conditional(
            ctx=ctx,
            is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
            title="Start Short Trades",
            signals=start_short_trades,
            values=slightly_above_highs,
            times=candle_times,
            value_key=f"{cache_key_prefix}st-s",
            color="red",
        )
        has_exit_signals = len(exit_short_trades) and len(exit_long_trades)
        if has_exit_signals:
            (
                _candle_times,
                _slightly_above_highs,
                _slightly_below_lows,
                start_long_trades,
                exit_short_trades,
            ) = basic_utilities.cut_data_to_same_len(
                (
                    candle_times,
                    slightly_above_highs,
                    slightly_below_lows,
                    start_long_trades,
                    exit_short_trades,
                )
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="Exit Long Trades",
                signals=exit_long_trades,
                values=_slightly_above_highs,
                times=_candle_times,
                value_key=f"{cache_key_prefix}ex-l",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="Exit Short Trades",
                signals=exit_short_trades,
                values=_slightly_below_lows,
                times=_candle_times,
                value_key=f"{cache_key_prefix}ex-s",
            )
        if self.trading_mode.display_settings.show_bar_predictions:
            await plotting.plot(
                ctx,
                title="Bar Prediction Values",
                cache_value=f"{cache_key_prefix}historical_predictions",
                chart="sub-chart",
            )
            if self.trading_mode.display_settings.is_plot_recording_mode:
                await ctx.set_cached_value(
                    value=historical_predictions[-1],
                    value_key=f"{cache_key_prefix}historical_predictions",
                )
            else:
                await ctx.set_cached_values(
                    values=historical_predictions,
                    cache_keys=candle_times,
                    value_key=f"{cache_key_prefix}historical_predictions",
                )

        if self.trading_mode.display_settings.enable_additional_plots:
            plot_signal_state = True
            if plot_signal_state:
                await matrix_plots.plot_conditional(
                    ctx=ctx,
                    is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                    title="is_buy_signals",
                    signals=is_buy_signals,
                    values=[1] * len(is_buy_signals),
                    # values=slightly_below_lows,
                    times=candle_times,
                    value_key=f"{cache_key_prefix}is_buy_signals",
                    chart_location="sub-chart",
                )
                await matrix_plots.plot_conditional(
                    ctx=ctx,
                    is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                    title="is_sell_signals",
                    signals=is_sell_signals,
                    values=[-1] * len(is_sell_signals),
                    # values=slightly_above_highs,
                    times=candle_times,
                    value_key=f"{cache_key_prefix}is_sell_signals",
                    chart_location="sub-chart",
                )
                await plotting.plot(
                    ctx,
                    title="Signal State",
                    cache_value=f"{cache_key_prefix}previous_signals",
                    chart="sub-chart",
                )
                if self.trading_mode.display_settings.is_plot_recording_mode:
                    await ctx.set_cached_value(
                        value=previous_signals[-1],
                        value_key=f"{cache_key_prefix}previous_signals",
                    )
                else:
                    await ctx.set_cached_values(
                        values=previous_signals,
                        cache_keys=candle_times,
                        value_key=f"{cache_key_prefix}previous_signals",
                    )

    async def _handle_full_history_plottings(
        self,
        ctx: context_management.Context,
        cache_key_prefix: str,
        this_symbol_settings: utils.SymbolSettings,
        y_train_series: npt.NDArray[numpy.int64],
        _filters: utils.Filter,
        candle_closes: npt.NDArray[numpy.float64],
        candle_highs: npt.NDArray[numpy.float64],
        candle_lows: npt.NDArray[numpy.float64],
        candle_times: npt.NDArray[numpy.float64],
        candles_hlc3: npt.NDArray[numpy.float64],
        candles_ohlc4: npt.NDArray[numpy.float64],
        feature_arrays: utils.FeatureArrays,
        alerts_bullish: npt.NDArray[numpy.bool_],
        alerts_bearish: npt.NDArray[numpy.bool_],
        is_bullishs: npt.NDArray[numpy.bool_],
        is_bearishs: npt.NDArray[numpy.bool_],
        is_bearish_changes: npt.NDArray[numpy.bool_],
        is_bullish_changes: npt.NDArray[numpy.bool_],
        is_bullish_cross_alerts: npt.NDArray[numpy.bool_],
        is_bearish_cross_alerts: npt.NDArray[numpy.bool_],
        kernel_estimate: npt.NDArray[numpy.float64],
        yhat2: npt.NDArray[numpy.float64],
        is_bearish_rates: npt.NDArray[numpy.bool_],
        was_bullish_rates: npt.NDArray[numpy.bool_],
        is_bullish_rates: npt.NDArray[numpy.bool_],
        was_bearish_rates: npt.NDArray[numpy.bool_],
        slightly_below_lows: npt.NDArray[numpy.float64],
        slightly_above_highs: npt.NDArray[numpy.float64],
    ) -> None:
        (
            y_train_series,
            _filters.filter_all,
            _filters.is_uptrend,
            _filters.is_downtrend,
            _filters.volatility,
            _filters.regime,
            _filters.adx,
            candle_closes,
            candle_highs,
            candle_lows,
            candle_times,
            candles_hlc3,
            candles_ohlc4,
            alerts_bullish,
            alerts_bearish,
            is_bullishs,
            is_bearishs,
            is_bearish_changes,
            is_bullish_changes,
            is_bullish_cross_alerts,
            is_bearish_cross_alerts,
            kernel_estimate,
            yhat2,
            is_bearish_rates,
            was_bullish_rates,
            is_bullish_rates,
            was_bearish_rates,
            slightly_below_lows,
            slightly_above_highs,
        ) = basic_utilities.cut_data_to_same_len(
            (
                y_train_series,
                _filters.filter_all,
                _filters.is_uptrend,
                _filters.is_downtrend,
                _filters.volatility,
                _filters.regime,
                _filters.adx,
                candle_closes,
                candle_highs,
                candle_lows,
                candle_times,
                candles_hlc3,
                candles_ohlc4,
                alerts_bullish,
                alerts_bearish,
                is_bullishs,
                is_bearishs,
                is_bearish_changes,
                is_bullish_changes,
                is_bullish_cross_alerts,
                is_bearish_cross_alerts,
                kernel_estimate,
                yhat2,
                is_bearish_rates,
                was_bullish_rates,
                is_bullish_rates,
                was_bearish_rates,
                slightly_below_lows,
                slightly_above_highs,
            ),
            reference_length=feature_arrays.cut_data_to_same_len(),
        )
        feature_arrays.cut_data_to_same_len(reference_length=len(candle_closes))
        if self.trading_mode.filter_settings.plot_volatility_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="Volatility Filter",
                signals=_filters.volatility,
                values=slightly_below_lows,
                times=candle_times,
                value_key=f"{cache_key_prefix}volatility",
            )
        if self.trading_mode.filter_settings.plot_regime_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="Regime filter",
                signals=_filters.regime,
                values=slightly_below_lows,
                times=candle_times,
                value_key=f"{cache_key_prefix}regime",
            )
        if self.trading_mode.filter_settings.plot_adx_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="ADX filter",
                signals=_filters.adx,
                values=slightly_below_lows,
                times=candle_times,
                value_key=f"{cache_key_prefix}adx",
            )
        if (
            self.trading_mode.filter_settings.plot_adx_filter
            or self.trading_mode.filter_settings.plot_volatility_filter
            or self.trading_mode.filter_settings.plot_regime_filter
        ):
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="both side filter",
                signals=_filters.filter_all,
                values=slightly_below_lows,
                times=candle_times,
                value_key=f"{cache_key_prefix}filter_all",
            )

        if self.trading_mode.filter_settings.plot_ema_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="is_ema_uptrend",
                signals=_filters.is_ema_uptrend,
                values=slightly_below_lows,
                times=candle_times,
                value_key=f"{cache_key_prefix}is_ema_uptrend",
            )
        if self.trading_mode.filter_settings.plot_sma_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="is_sma_uptrend",
                signals=_filters.is_sma_uptrend,
                values=slightly_below_lows,
                times=candle_times,
                value_key=f"{cache_key_prefix}is_sma_uptrend",
            )
        if self.trading_mode.filter_settings.plot_ema_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="is_ema_downtrend",
                signals=_filters.is_ema_downtrend,
                values=slightly_above_highs,
                times=candle_times,
                value_key=f"{cache_key_prefix}is_ema_downtrend",
            )
        if self.trading_mode.filter_settings.plot_sma_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="is_sma_downtrend",
                signals=_filters.is_sma_downtrend,
                values=slightly_above_highs,
                times=candle_times,
                value_key=f"{cache_key_prefix}is_sma_downtrend",
            )

        if (
            self.trading_mode.filter_settings.plot_ema_filter
            or self.trading_mode.filter_settings.plot_sma_filter
        ):
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="is uptrend",
                signals=_filters.is_uptrend,
                values=slightly_below_lows,
                times=candle_times,
                value_key=f"{cache_key_prefix}uptrend",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="is downtrend",
                signals=_filters.is_downtrend,
                values=slightly_below_lows,
                times=candle_times,
                value_key=f"{cache_key_prefix}downtrend",
            )
        additional_values_by_key = {}
        if this_symbol_settings.use_custom_pair:
            additional_values_by_key[f"{cache_key_prefix}clo"] = candle_closes
            await plotting.plot(
                ctx,
                title="Candle CLoses " + this_symbol_settings.this_target_symbol,
                cache_value=f"{cache_key_prefix}clo",
                chart="main-chart",
                own_yaxis=True,
            )

        if self.trading_mode.feature_engineering_settings.plot_features:
            for feature_id, feature_setting in enumerate(
                self.trading_mode.feature_engineering_settings.features_settings
            ):
                additional_values_by_key[
                    f"{cache_key_prefix}f{feature_id}"
                ] = feature_arrays.feature_arrays[feature_id]
                await plotting.plot(
                    ctx,
                    title=f"Feature {feature_id} - {feature_setting.indicator_name} "
                    f"(a: {feature_setting.param_a}, b: {feature_setting.param_b}",
                    cache_value=f"{cache_key_prefix}f{feature_id}",
                    chart="sub-chart",
                )
        if self.trading_mode.kernel_settings.show_kernel_estimate:
            additional_values_by_key[f"{cache_key_prefix}k_esti"] = kernel_estimate
            await plotting.plot(
                ctx,
                title="Kernel estimate",
                cache_value=f"{cache_key_prefix}k_esti",
                chart="main-chart",
            )
        if self.trading_mode.display_settings.enable_additional_plots:
            additional_values_by_key[f"{cache_key_prefix}yhat2"] = yhat2
            additional_values_by_key[f"{cache_key_prefix}yt"] = y_train_series
            await plotting.plot(
                ctx,
                title="yhat2",
                cache_value=f"{cache_key_prefix}yhat2",
                chart="main-chart",
            )

            await plotting.plot(
                ctx,
                title="y_train_series",
                cache_value=f"{cache_key_prefix}yt",
                chart="sub-chart",
                own_yaxis=True,
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="is_bearish_rates",
                signals=is_bearish_rates,
                values=slightly_above_highs,
                times=candle_times,
                value_key=f"{cache_key_prefix}is_bearish_rates",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="was_bullish_rates",
                signals=was_bullish_rates,
                values=slightly_below_lows,
                times=candle_times,
                value_key=f"{cache_key_prefix}was_bullish_rates",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="is_bullish_rates",
                signals=is_bullish_rates,
                values=slightly_below_lows,
                times=candle_times,
                value_key=f"{cache_key_prefix}is_bullish_rates",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="was_bearish_rates",
                signals=was_bearish_rates,
                values=slightly_above_highs,
                times=candle_times,
                value_key=f"{cache_key_prefix}was_bearish_rates",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="is_bullish_cross_alerts",
                signals=is_bullish_cross_alerts,
                values=slightly_below_lows,
                times=candle_times,
                value_key=f"{cache_key_prefix}is_bullish_cross_alerts",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="is_bearish_cross_alerts",
                signals=is_bearish_cross_alerts,
                values=slightly_above_highs,
                times=candle_times,
                value_key=f"{cache_key_prefix}is_bearish_cross_alerts",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="alerts_bullish",
                signals=alerts_bullish,
                values=slightly_below_lows,
                times=candle_times,
                value_key=f"{cache_key_prefix}alerts_bullish",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="alerts_bearish",
                signals=alerts_bearish,
                values=slightly_above_highs,
                times=candle_times,
                value_key=f"{cache_key_prefix}alerts_bearish",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="is_bullishs",
                signals=is_bullishs,
                values=slightly_below_lows,
                times=candle_times,
                value_key=f"{cache_key_prefix}is_bullishs",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="is_bearishs",
                signals=is_bearishs,
                values=slightly_above_highs,
                times=candle_times,
                value_key=f"{cache_key_prefix}is_bearishs",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="is_bearish_changes",
                signals=is_bearish_changes,
                values=slightly_above_highs,
                times=candle_times,
                value_key=f"{cache_key_prefix}is_bearish_changes",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                is_recording_mode=self.trading_mode.display_settings.is_plot_recording_mode,
                title="is_bullish_changes",
                signals=is_bullish_changes,
                values=slightly_below_lows,
                times=candle_times,
                value_key=f"{cache_key_prefix}is_bullish_changes",
            )
        if additional_values_by_key != {}:
            if (
                not self.exchange_manager.is_backtesting
                and self.trading_mode.display_settings.is_plot_recording_mode
            ):
                for key, value in additional_values_by_key.items():
                    await ctx.set_cached_value(
                        value=value[-1],
                        value_key=key,
                    )
            else:
                first_key = next(iter(additional_values_by_key))
                first_values = additional_values_by_key[first_key]
                del additional_values_by_key[first_key]
                await ctx.set_cached_values(
                    values=first_values,
                    cache_keys=candle_times,
                    value_key=first_key,
                    additional_values_by_key=additional_values_by_key,
                )

    def _get_all_filters(
        self,
        candle_closes: npt.NDArray[numpy.float64],
        data_length: int,
        candles_ohlc4: npt.NDArray[numpy.float64],
        candle_highs: npt.NDArray[numpy.float64],
        candle_lows: npt.NDArray[numpy.float64],
        user_selected_candles: npt.NDArray[numpy.float64],
    ) -> utils.Filter:
        # Filter object for filtering the ML predictions
        (
            is_ema_uptrend,
            is_ema_downtrend,
            is_sma_uptrend,
            is_sma_downtrend,
        ) = self._get_ma_filters(candle_closes, data_length)
        volatility: npt.NDArray[numpy.bool_] = ml_extensions.filter_volatility(
            candle_highs=candle_highs,
            candle_lows=candle_lows,
            candle_closes=candle_closes,
            min_length=1,
            max_length=10,
            use_volatility_filter=self.trading_mode.filter_settings.use_volatility_filter,
        )
        regime: npt.NDArray[numpy.bool_] = ml_extensions.regime_filter(
            ohlc4=candles_ohlc4,
            highs=candle_highs,
            lows=candle_lows,
            threshold=self.trading_mode.filter_settings.regime_threshold,
            use_regime_filter=self.trading_mode.filter_settings.use_regime_filter,
        )
        _filter: utils.Filter = utils.Filter(
            volatility=volatility,
            regime=regime,
            adx=ml_extensions.filter_adx(
                candle_closes=user_selected_candles,
                candle_highs=candle_highs,
                candle_lows=candle_lows,
                length=14,
                adx_threshold=self.trading_mode.filter_settings.adx_threshold,
                use_adx_filter=self.trading_mode.filter_settings.use_adx_filter,
            ),
            is_ema_uptrend=is_ema_uptrend,
            is_ema_downtrend=is_ema_downtrend,
            is_sma_uptrend=is_sma_uptrend,
            is_sma_downtrend=is_sma_downtrend,
        )
        return _filter

    def _get_feature_arrays(
        self,
        candle_closes: npt.NDArray[numpy.float64],
        candle_highs: npt.NDArray[numpy.float64],
        candle_lows: npt.NDArray[numpy.float64],
        candles_hlc3: npt.NDArray[numpy.float64],
    ) -> utils.FeatureArrays:
        feature_arrays: utils.FeatureArrays = utils.FeatureArrays()
        for (
            feature_settings
        ) in self.trading_mode.feature_engineering_settings.features_settings:
            feature_arrays.add_feature_array(
                feature_array=utils.series_from(
                    feature_settings.indicator_name,
                    candle_closes,
                    candle_highs,
                    candle_lows,
                    candles_hlc3,
                    feature_settings.param_a,
                    feature_settings.param_b,
                )
            )
        return feature_arrays

    async def _get_candle_data(
        self,
        ctx: context_management.Context,
        candle_source_name: str,
        data_source_symbol: str,
    ) -> tuple:
        max_history = True if ctx.exchange_manager.is_backtesting else False
        candle_times = await exchange_public_data.Time(
            ctx, symbol=data_source_symbol, max_history=max_history
        )
        candle_opens = await exchange_public_data.Open(
            ctx, symbol=data_source_symbol, max_history=max_history
        )
        candle_closes = await exchange_public_data.Close(
            ctx, symbol=data_source_symbol, max_history=max_history
        )
        candle_highs = await exchange_public_data.High(
            ctx, symbol=data_source_symbol, max_history=max_history
        )
        candle_lows = await exchange_public_data.Low(
            ctx, symbol=data_source_symbol, max_history=max_history
        )
        candles_hlc3 = CandlesUtil.HLC3(
            candle_highs,
            candle_lows,
            candle_closes,
        )
        candles_ohlc4 = CandlesUtil.OHLC4(
            candle_opens,
            candle_highs,
            candle_lows,
            candle_closes,
        )
        user_selected_candles = None
        if candle_source_name == enums.PriceStrings.STR_PRICE_CLOSE.value:
            user_selected_candles = candle_closes
        if candle_source_name == enums.PriceStrings.STR_PRICE_OPEN.value:
            user_selected_candles = await exchange_public_data.Open(
                ctx, symbol=data_source_symbol, max_history=max_history
            )
        if candle_source_name == enums.PriceStrings.STR_PRICE_HIGH.value:
            user_selected_candles = candle_highs
        if candle_source_name == enums.PriceStrings.STR_PRICE_LOW.value:
            user_selected_candles = candle_lows
        if candle_source_name == "hlc3":
            user_selected_candles = candles_hlc3
        if candle_source_name == "ohlc4":
            user_selected_candles = candles_ohlc4
        return (
            candle_closes,
            candle_highs,
            candle_lows,
            candles_hlc3,
            candles_ohlc4,
            user_selected_candles,
            candle_times,
        )

    def _get_max_bars_back_index(self, cutted_data_length: int) -> int:
        if (
            cutted_data_length
            >= self.trading_mode.classification_settings.max_bars_back
        ):
            if self.ctx.exchange_manager.is_backtesting:
                return self.trading_mode.classification_settings.max_bars_back
            return (
                cutted_data_length
                - self.trading_mode.classification_settings.max_bars_back
            )
        else:
            self.logger.warning(
                "Not enough historical bars for the current max_bars_back. "
                "Either increase the amount of initialized candles "
                "or reduce the max_bars_back setting. Classification will run "
                f"on {cutted_data_length} bars"
            )
            return 0  # start on first bar with all filters, indicators etc. available
