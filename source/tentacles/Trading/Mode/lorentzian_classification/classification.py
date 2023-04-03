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
import tentacles.Trading.Mode.lorentzian_classification.classification_functions.classification_utils as classification_utils

import tentacles.Trading.Mode.lorentzian_classification.kernel_functions.kernel as kernel
import tentacles.Trading.Mode.lorentzian_classification.trade_execution as trade_execution
import tentacles.Trading.Mode.lorentzian_classification.utils as utils
import tentacles.Trading.Mode.lorentzian_classification.ml_extensions_2.ml_extensions as ml_extensions

import tentacles.Meta.Keywords.matrix_library.basic_tentacles.matrix_basic_keywords.tools.utilities as basic_utilities
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.matrix_basic_keywords.plottings.plots as matrix_plots
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.basic_modes.mode_base.abstract_producer_base as abstract_producer_base
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.basic_modes.mode_base.producer_base as producer_base

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

    async def evaluate_lorentzian_classification(
        self,
        ctx: context_management.Context,
    ):
        this_symbol_settings: utils.SymbolSettings = (
            self.trading_mode.data_source_settings.symbol_settings_by_symbols[
                self.trading_mode.symbol
            ]
        )
        if not this_symbol_settings.trade_on_this_pair:
            return

        if await self._trade_cached_backtesting_candles_if_available(ctx):
            return
        s_time = basic_utilities.start_measure_time(
            f" Lorentzian Classification {self.trading_mode.symbol} -"
        )
        await self.init_order_settings(
            ctx, leverage=self.trading_mode.order_settings.leverage
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
        ] = classification_utils.get_y_train_series(user_selected_candles)

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
            feature_arrays.f1,
            feature_arrays.f2,
            feature_arrays.f3,
            feature_arrays.f4,
            feature_arrays.f5,
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
                feature_arrays.f1,
                feature_arrays.f2,
                feature_arrays.f3,
                feature_arrays.f4,
                feature_arrays.f5,
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
            )
        )

        cutted_data_length: int = len(candle_closes)
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

        distances: list = []
        predictions: list = []
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
            ) = self._classify_current_candle(
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
                distances=distances,
                predictions=predictions,
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

    def _classify_current_candle(
        self,
        y_train_series: npt.NDArray[numpy.float64],
        current_candle_index: int,
        feature_arrays: utils.FeatureArrays,
        historical_predictions: list,
        _filters: utils.Filter,
        previous_signals: list,
        is_bullishs: npt.NDArray[numpy.bool_],
        is_bearishs: npt.NDArray[numpy.bool_],
        # alerts_bullish: npt.NDArray[numpy.bool_],
        # alerts_bearish: npt.NDArray[numpy.bool_],
        # is_bearish_changes: npt.NDArray[numpy.bool_],
        # is_bullish_changes: npt.NDArray[numpy.bool_],
        bars_since_red_entry: int,
        bars_since_green_entry: int,
        distances: list,
        predictions: list,
        start_long_trades: list,
        start_short_trades: list,
        exit_short_trades: list,
        exit_long_trades: list,
        is_buy_signals: list,
        is_sell_signals: list,
    ) -> typing.Tuple[int, int]:

        # =========================
        # ====  Core ML Logic  ====
        # =========================

        # Approximate Nearest Neighbors Search with Lorentzian Distance:
        # A novel variation of the Nearest Neighbors (NN) search algorithm that ensures
        # a chronologically uniform distribution of neighbors.

        # In a traditional KNN-based approach, we would iterate through the entire
        # dataset and calculate the distance between the current bar
        # and every other bar in the dataset and then sort the distances in ascending
        # order. We would then take the first k bars and use their
        # labels to determine the label of the current bar.

        # There are several problems with this traditional KNN approach in the context
        # of real-time calculations involving time series data:
        # - It is computationally expensive to iterate through the entire dataset and
        #   calculate the distance between every historical bar and
        #   the current bar.
        # - Market time series data is often non-stationary, meaning that the
        #   statistical properties of the data change slightly over time.
        # - It is possible that the nearest neighbors are not the most informative ones,
        #   and the KNN algorithm may return poor results if the
        #   nearest neighbors are not representative of the majority of the data.

        # Previously, the user @capissimo attempted to address some of these issues in
        # several of his PineScript-based KNN implementations by:
        # - Using a modified KNN algorithm based on consecutive furthest neighbors to
        #   find a set of approximate "nearest" neighbors.
        # - Using a sliding window approach to only calculate the distance between the
        #   current bar and the most recent n bars in the dataset.

        # Of these two approaches, the latter is inherently limited by the fact that it
        # only considers the most recent bars in the overall dataset.

        # The former approach has more potential to leverage historical price action,
        # but is limited by:
        # - The possibility of a sudden "max" value throwing off the estimation
        # - The possibility of selecting a set of approximate neighbors that are not
        #       representative of the majority of the data by oversampling
        #       values that are not chronologically distinct enough from one another
        # - The possibility of selecting too many "far" neighbors,
        #       which may result in a poor estimation of price action

        # To address these issues, a novel Approximate Nearest Neighbors (ANN)
        # algorithm is used in this indicator.

        # In the below ANN algorithm:
        # 1. The algorithm iterates through the dataset in chronological order,
        #       using the modulo operator to only perform calculations every 4 bars.
        #       This serves the dual purpose of reducing the computational overhead of
        #       the algorithm and ensuring a minimum chronological spacing
        #       between the neighbors of at least 4 bars.
        # 2. A list of the k-similar neighbors is simultaneously maintained in both a
        #       predictions array and corresponding distances array.
        # 3. When the size of the predictions array exceeds the desired number of
        #       nearest neighbors specified in settings.neighborsCount,
        #       the algorithm removes the first neighbor from the predictions
        #       array and the corresponding distance array.
        # 4. The lastDistance variable is overriden to be a distance in the lower 25% of
        #       the array. This step helps to boost overall accuracy by ensuring
        #       subsequent newly added distance values increase at a slower rate.
        # 5. Lorentzian distance is used as a distance metric in order to minimize the
        #       effect of outliers and take into account the warping of
        #       "price-time" due to proximity to significant economic events.


        last_distance: float = -1
        prediction: float = 0
        for candles_back in self._get_candles_back_start_end_index(
            current_candle_index
        ):
            if self.trading_mode.classification_settings.down_sampler(
                candles_back,
                self.trading_mode.classification_settings.only_train_on_every_x_bars,
            ):
                lorentzian_distance: float = (
                    classification_utils.get_lorentzian_distance(
                        self.trading_mode.feature_engineering_settings.feature_count,
                        candle_index=current_candle_index,
                        candles_back_index=candles_back,
                        feature_arrays=feature_arrays,
                    )
                )
                if lorentzian_distance >= last_distance:
                    last_distance = lorentzian_distance
                    predictions.append(y_train_series[candles_back])
                    distances.append(lorentzian_distance)
                    if (
                        len(predictions)
                        > self.trading_mode.classification_settings.neighbors_count
                    ):
                        last_distance = distances[
                            self.trading_mode.classification_settings.last_distance_neighbors_count
                        ]
                        del distances[0]
                        del predictions[0]
        prediction: int = sum(predictions)
        historical_predictions.append(prediction)
        (
            bars_since_green_entry,
            bars_since_red_entry,
        ) = classification_utils.set_signals_from_prediction(
            prediction=prediction,
            _filters=_filters,
            candle_index=current_candle_index,
            previous_signals=previous_signals,
            start_long_trades=start_long_trades,
            start_short_trades=start_short_trades,
            is_bullishs=is_bullishs,
            is_bearishs=is_bearishs,
            # alerts_bullish=alerts_bullish,
            # alerts_bearish=alerts_bearish,
            # is_bearish_changes=is_bearish_changes,
            # is_bullish_changes=is_bullish_changes,
            exit_short_trades=exit_short_trades,
            exit_long_trades=exit_long_trades,
            bars_since_green_entry=bars_since_green_entry,
            bars_since_red_entry=bars_since_red_entry,
            is_buy_signals=is_buy_signals,
            is_sell_signals=is_sell_signals,
            exit_type=self.trading_mode.order_settings.exit_type,
        )
        return bars_since_green_entry, bars_since_red_entry

    def _get_candles_back_start_end_index(self, current_candle_index: int):
        size_loop: int = min(
            self.trading_mode.classification_settings.max_bars_back - 1,
            current_candle_index,
        )
        if self.trading_mode.classification_settings.use_remote_fractals:
            # classify starting from:
            #   live mode: first bar
            #   backtesting:  current bar - live_history_size
            start_index: int = max(
                current_candle_index
                - self.trading_mode.classification_settings.live_history_size,
                0,
            )
            end_index: int = start_index + size_loop
        else:
            start_index: int = current_candle_index - size_loop
            end_index: int = current_candle_index
        return range(start_index, end_index)

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
        await self._handle_full_history_plottings(
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
            slightly_below_lows=slightly_below_lows,
            slightly_above_highs=slightly_above_highs,
        )
        await self._handle_short_history_plottings(
            ctx=ctx,
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
            title="Start Long Trades",
            signals=start_long_trades,
            values=slightly_below_lows,
            times=candle_times,
            value_key="st-l",
            color="green",
        )
        await matrix_plots.plot_conditional(
            ctx=ctx,
            title="Start Short Trades",
            signals=start_short_trades,
            values=slightly_above_highs,
            times=candle_times,
            value_key="st-s",
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
                title="Exit Long Trades",
                signals=exit_long_trades,
                values=_slightly_above_highs,
                times=_candle_times,
                value_key="ex-l",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="Exit Short Trades",
                signals=exit_short_trades,
                values=_slightly_below_lows,
                times=_candle_times,
                value_key="ex-s",
            )
        if self.trading_mode.display_settings.show_bar_predictions:
            await ctx.set_cached_values(
                values=historical_predictions,
                cache_keys=candle_times,
                value_key="historical_predictions",
            )
            await plotting.plot(
                ctx,
                title="Bar Prediction Values",
                cache_value="historical_predictions",
                chart="sub-chart",
            )

        if self.trading_mode.display_settings.enable_additional_plots:
            plot_signal_state = True
            if plot_signal_state:
                await matrix_plots.plot_conditional(
                    ctx=ctx,
                    title="is_buy_signals",
                    signals=is_buy_signals,
                    values=[1] * len(is_buy_signals),
                    # values=slightly_below_lows,
                    times=candle_times,
                    value_key="is_buy_signals",
                    chart_location="sub-chart",
                )
                await matrix_plots.plot_conditional(
                    ctx=ctx,
                    title="is_sell_signals",
                    signals=is_sell_signals,
                    values=[-1] * len(is_sell_signals),
                    # values=slightly_above_highs,
                    times=candle_times,
                    value_key="is_sell_signals",
                    chart_location="sub-chart",
                )
                await plotting.plot(
                    ctx,
                    title="Signal State",
                    cache_value="previous_signals",
                    chart="sub-chart",
                )
                await ctx.set_cached_values(
                    values=previous_signals,
                    cache_keys=candle_times,
                    value_key="previous_signals",
                )

    async def _handle_full_history_plottings(
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
            feature_arrays.f1,
            feature_arrays.f2,
            feature_arrays.f3,
            feature_arrays.f4,
            feature_arrays.f5,
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
                feature_arrays.f1,
                feature_arrays.f2,
                feature_arrays.f3,
                feature_arrays.f4,
                feature_arrays.f5,
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
            )
        )
        # TODO handle when custom pair
        # use_own_y_axis:bool = this_symbol_settings.use_custom_pair
        if self.trading_mode.filter_settings.plot_volatility_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="Volatility Filter",
                signals=_filters.volatility,
                values=slightly_below_lows,
                times=candle_times,
                value_key="volatility",
            )
        if self.trading_mode.filter_settings.plot_regime_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="Regime filter",
                signals=_filters.regime,
                values=slightly_below_lows,
                times=candle_times,
                value_key="regime",
            )
        if self.trading_mode.filter_settings.plot_adx_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="ADX filter",
                signals=_filters.adx,
                values=slightly_below_lows,
                times=candle_times,
                value_key="adx",
            )
        if (
            self.trading_mode.filter_settings.plot_adx_filter
            or self.trading_mode.filter_settings.plot_volatility_filter
            or self.trading_mode.filter_settings.plot_regime_filter
        ):
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="both side filter",
                signals=_filters.filter_all,
                values=slightly_below_lows,
                times=candle_times,
                value_key="filter_all",
            )

        if self.trading_mode.filter_settings.plot_ema_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="is_ema_uptrend",
                signals=_filters.is_ema_uptrend,
                values=slightly_below_lows,
                times=candle_times,
                value_key="is_ema_uptrend",
            )
        if self.trading_mode.filter_settings.plot_sma_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="is_sma_uptrend",
                signals=_filters.is_sma_uptrend,
                values=slightly_below_lows,
                times=candle_times,
                value_key="is_sma_uptrend",
            )
        if self.trading_mode.filter_settings.plot_ema_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="is_ema_downtrend",
                signals=_filters.is_ema_downtrend,
                values=slightly_above_highs,
                times=candle_times,
                value_key="is_ema_downtrend",
            )
        if self.trading_mode.filter_settings.plot_sma_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="is_sma_downtrend",
                signals=_filters.is_sma_downtrend,
                values=slightly_above_highs,
                times=candle_times,
                value_key="is_sma_downtrend",
            )

        if (
            self.trading_mode.filter_settings.plot_ema_filter
            or self.trading_mode.filter_settings.plot_sma_filter
        ):
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="is uptrend",
                signals=_filters.is_uptrend,
                values=slightly_below_lows,
                times=candle_times,
                value_key="uptrend",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="is downtrend",
                signals=_filters.is_downtrend,
                values=slightly_below_lows,
                times=candle_times,
                value_key="downtrend",
            )
        additional_values_by_key = {}
        if this_symbol_settings.use_custom_pair:
            additional_values_by_key["clo"] = candle_closes
            await plotting.plot(
                ctx,
                title="Candle CLoses " + this_symbol_settings.this_target_symbol,
                cache_value="clo",
                chart="main-chart",
                own_yaxis=True,
            )

        if self.trading_mode.feature_engineering_settings.plot_features:
            additional_values_by_key["f1"] = feature_arrays.f1
            additional_values_by_key["f2"] = feature_arrays.f2
            await plotting.plot(
                ctx,
                title="Feature 1",
                cache_value="f1",
                chart="sub-chart",
            )
            await plotting.plot(
                ctx,
                title="Feature 2",
                cache_value="f2",
                chart="sub-chart",
            )
            if feature_arrays.f3 is not None:
                additional_values_by_key["f3"] = feature_arrays.f3
                await plotting.plot(
                    ctx,
                    title="Feature 3",
                    cache_value="f3",
                    chart="sub-chart",
                )
            if feature_arrays.f4 is not None:
                additional_values_by_key["f4"] = feature_arrays.f4
                await plotting.plot(
                    ctx,
                    title="Feature 4",
                    cache_value="f4",
                    chart="sub-chart",
                )
            if feature_arrays.f5 is not None:
                additional_values_by_key["f5"] = feature_arrays.f5
                await plotting.plot(
                    ctx,
                    title="Feature 5",
                    cache_value="f5",
                    chart="sub-chart",
                )
        if self.trading_mode.kernel_settings.show_kernel_estimate:
            additional_values_by_key["k_esti"] = kernel_estimate
            await plotting.plot(
                ctx,
                title="Kernel estimate",
                cache_value="k_esti",
                chart="main-chart",
            )
        if self.trading_mode.display_settings.enable_additional_plots:
            additional_values_by_key["yhat2"] = yhat2
            additional_values_by_key["yt"] = y_train_series
            await plotting.plot(
                ctx,
                title="yhat2",
                cache_value="yhat2",
                chart="main-chart",
            )

            await plotting.plot(
                ctx,
                title="y_train_series",
                cache_value="yt",
                chart="sub-chart",
                own_yaxis=True,
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="is_bearish_rates",
                signals=is_bearish_rates,
                values=slightly_above_highs,
                times=candle_times,
                value_key="is_bearish_rates",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="was_bullish_rates",
                signals=was_bullish_rates,
                values=slightly_below_lows,
                times=candle_times,
                value_key="was_bullish_rates",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="is_bullish_rates",
                signals=is_bullish_rates,
                values=slightly_below_lows,
                times=candle_times,
                value_key="is_bullish_rates",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="was_bearish_rates",
                signals=was_bearish_rates,
                values=slightly_above_highs,
                times=candle_times,
                value_key="was_bearish_rates",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="is_bullish_cross_alerts",
                signals=is_bullish_cross_alerts,
                values=slightly_below_lows,
                times=candle_times,
                value_key="is_bullish_cross_alerts",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="is_bearish_cross_alerts",
                signals=is_bearish_cross_alerts,
                values=slightly_above_highs,
                times=candle_times,
                value_key="is_bearish_cross_alerts",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="alerts_bullish",
                signals=alerts_bullish,
                values=slightly_below_lows,
                times=candle_times,
                value_key="alerts_bullish",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="alerts_bearish",
                signals=alerts_bearish,
                values=slightly_above_highs,
                times=candle_times,
                value_key="alerts_bearish",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="is_bullishs",
                signals=is_bullishs,
                values=slightly_below_lows,
                times=candle_times,
                value_key="is_bullishs",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="is_bearishs",
                signals=is_bearishs,
                values=slightly_above_highs,
                times=candle_times,
                value_key="is_bearishs",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="is_bearish_changes",
                signals=is_bearish_changes,
                values=slightly_above_highs,
                times=candle_times,
                value_key="is_bearish_changes",
            )
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="is_bullish_changes",
                signals=is_bullish_changes,
                values=slightly_below_lows,
                times=candle_times,
                value_key="is_bullish_changes",
            )
        if additional_values_by_key is not {}:
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
        return utils.FeatureArrays(
            # TODO use list and loop instead
            f1=utils.series_from(
                self.trading_mode.feature_engineering_settings.f1_string,
                candle_closes,
                candle_highs,
                candle_lows,
                candles_hlc3,
                self.trading_mode.feature_engineering_settings.f1_paramA,
                self.trading_mode.feature_engineering_settings.f1_paramB,
            ),
            f2=utils.series_from(
                self.trading_mode.feature_engineering_settings.f2_string,
                candle_closes,
                candle_highs,
                candle_lows,
                candles_hlc3,
                self.trading_mode.feature_engineering_settings.f2_paramA,
                self.trading_mode.feature_engineering_settings.f2_paramB,
            ),
            f3=utils.series_from(
                self.trading_mode.feature_engineering_settings.f3_string,
                candle_closes,
                candle_highs,
                candle_lows,
                candles_hlc3,
                self.trading_mode.feature_engineering_settings.f3_paramA,
                self.trading_mode.feature_engineering_settings.f3_paramB,
            ),
            f4=utils.series_from(
                self.trading_mode.feature_engineering_settings.f4_string,
                candle_closes,
                candle_highs,
                candle_lows,
                candles_hlc3,
                self.trading_mode.feature_engineering_settings.f4_paramA,
                self.trading_mode.feature_engineering_settings.f4_paramB,
            ),
            f5=utils.series_from(
                self.trading_mode.feature_engineering_settings.f5_string,
                candle_closes,
                candle_highs,
                candle_lows,
                candles_hlc3,
                self.trading_mode.feature_engineering_settings.f5_paramA,
                self.trading_mode.feature_engineering_settings.f5_paramB,
            ),
        )

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
