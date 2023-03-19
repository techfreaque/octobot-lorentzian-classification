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


import math
import typing
import numpy
import numpy.typing as npt
import tulipy

import octobot_commons.enums as enums
import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords
import octobot_trading.modes.script_keywords.context_management as context_management
import tentacles.Meta.Keywords.scripting_library.backtesting.backtesting_settings as backtesting_settings
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_public_data as exchange_public_data
import tentacles.Meta.Keywords.scripting_library.data.writing.plotting as plotting
import tentacles.Meta.Keywords.scripting_library.orders.order_types.market_order as market_order
import tentacles.Trading.Mode.lorentzian_classification.classification_utils as classification_utils

import tentacles.Trading.Mode.lorentzian_classification.kernel_functions.kernel as kernel
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

# try:
#     import tentacles.Meta.Keywords.matrix_library.pro_tentacles.pro_keywords.orders.managed_order_pro.activate_managed_order as activate_managed_order
# except (ImportError, ModuleNotFoundError):
activate_managed_order = None


class LorentzianClassificationScript(
    abstract_producer_base.AbstractBaseModeProducer,
    producer_base.MatrixProducerBase,
):
    def __init__(self, channel, config, trading_mode, exchange_manager):
        abstract_producer_base.AbstractBaseModeProducer.__init__(
            self, channel, config, trading_mode, exchange_manager
        )
        producer_base.MatrixProducerBase.__init__(
            self, channel, config, trading_mode, exchange_manager
        )

    managend_orders_long_settings = None
    managend_orders_short_settings = None

    start_long_trades_cache: dict = None
    start_short_trades_cache: dict = None
    exit_long_trades_cache: dict = None
    exit_short_trades_cache: dict = None

    async def evaluate_lorentzian_classification(
        self,
        ctx: context_management.Context,
    ):
        if await self._trade_cached_backtesting_candles_if_available(ctx):
            return
        s_time = basic_utilities.start_measure_time(" Lorentzian Classification -")
        await self.init_order_settings(ctx)
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
            candle_source_name=self.trading_mode.general_settings.source,
        )
        data_length = len(candle_highs)
        (_filters, recentAtr, historicalAtr,) = self._get_all_filters(
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
        ) = self.get_kernel_data(user_selected_candles, data_length)

        feature_arrays: utils.FeatureArrays = self._get_feature_arrays(
            candle_closes=candle_closes,
            candle_highs=candle_highs,
            candle_lows=candle_lows,
            candles_hlc3=candles_hlc3,
        )
        y_train_series: npt.NDArray[numpy.bool_] = self._get_y_train_series(
            user_selected_candles
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
            recentAtr,
            historicalAtr,
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
                recentAtr,
                historicalAtr,
            )
        )

        cutted_data_length: int = len(candle_closes)
        max_bars_back_index: int = self._get_max_bars_back_index(cutted_data_length)

        missing_data_length = data_length - cutted_data_length

        # =================================
        # ==== Next Bar Classification ====
        # =================================

        # This model specializes specifically in predicting the direction of price
        # action over the course of the next general_settings.only_train_on_every_x_bars.

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
            " Lorentzian Classification - calculating full history indicators",
        )
        s_time = basic_utilities.start_measure_time(
            " Lorentzian Classification - classifying candles"
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
                alerts_bullish=alerts_bullish,
                alerts_bearish=alerts_bearish,
                is_bearish_changes=is_bearish_changes,
                is_bullish_changes=is_bullish_changes,
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
                missing_data_length=missing_data_length,
            )
        if ctx.exchange_manager.is_backtesting:
            self._cache_backtesting_signals(
                ctx=ctx,
                s_time=s_time,
                candle_times=candle_times,
                start_short_trades=start_short_trades,
                start_long_trades=start_long_trades,
                exit_short_trades=exit_short_trades,
                exit_long_trades=exit_long_trades,
            )
        else:
            await self._trade_live_candle(
                s_time=s_time,
                start_short_trades=start_short_trades,
                start_long_trades=start_long_trades,
                exit_short_trades=exit_short_trades,
                exit_long_trades=exit_long_trades,
            )
        s_time = basic_utilities.start_measure_time()
        await self._handle_plottings(
            ctx=ctx,
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
            recentAtr=recentAtr,
            historicalAtr=historicalAtr,
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
            " Lorentzian Classification - storing plots",
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
        alerts_bullish: npt.NDArray[numpy.bool_],
        alerts_bearish: npt.NDArray[numpy.bool_],
        is_bearish_changes: npt.NDArray[numpy.bool_],
        is_bullish_changes: npt.NDArray[numpy.bool_],
        bars_since_red_entry: int,
        bars_since_green_entry: int,
        distances: list,
        predictions: list,
        start_long_trades: list,
        start_short_trades: list,
        exit_short_trades: list,
        exit_long_trades: list,
        is_buy_signals,
        is_sell_signals,
        missing_data_length,
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
            lorentzian_distance: float = classification_utils.get_lorentzian_distance(
                self.trading_mode.feature_engineering_settings.feature_count,
                candle_index=current_candle_index,
                candles_back_index=candles_back,
                feature_arrays=feature_arrays,
            )
            if lorentzian_distance >= last_distance and (
                not self.trading_mode.general_settings.use_down_sampling
                or candles_back
                % self.trading_mode.general_settings.only_train_on_every_x_bars
            ):
                last_distance = lorentzian_distance
                predictions.append(y_train_series[candles_back])
                distances.append(lorentzian_distance)
                if (
                    len(predictions)
                    > self.trading_mode.general_settings.neighbors_count
                ):
                    last_distance = distances[
                        self.trading_mode.general_settings.last_distance_neighbors_count
                    ]
                    del distances[0]
                    del predictions[0]
        prediction = sum(predictions)
        historical_predictions.append(prediction)
        (
            bars_since_green_entry,
            bars_since_red_entry,
        ) = self._set_signals_from_prediction(
            prediction=prediction,
            _filters=_filters,
            candle_index=current_candle_index,
            previous_signals=previous_signals,
            start_long_trades=start_long_trades,
            start_short_trades=start_short_trades,
            is_bullishs=is_bullishs,
            is_bearishs=is_bearishs,
            alerts_bullish=alerts_bullish,
            alerts_bearish=alerts_bearish,
            is_bearish_changes=is_bearish_changes,
            is_bullish_changes=is_bullish_changes,
            exit_short_trades=exit_short_trades,
            exit_long_trades=exit_long_trades,
            bars_since_green_entry=bars_since_green_entry,
            bars_since_red_entry=bars_since_red_entry,
            is_buy_signals=is_buy_signals,
            is_sell_signals=is_sell_signals,
        )
        return bars_since_green_entry, bars_since_red_entry

    def _get_candles_back_start_end_index(self, current_candle_index: int):
        size_loop: int = min(
            self.trading_mode.general_settings.max_bars_back - 1,
            current_candle_index,
        )

        if self.trading_mode.general_settings.use_remote_fractals:
            # classify starting from:
            #   live mode: first bar
            #   backtesting:  current bar - live_history_size
            start_index: int = max(
                current_candle_index
                - self.trading_mode.general_settings.live_history_size,
                0,
            )
            end_index: int = start_index + size_loop
        else:
            start_index: int = current_candle_index - size_loop
            end_index: int = current_candle_index
        return range(start_index, end_index)

    def _get_ma_filters(self, candle_closes, data_length):
        if self.trading_mode.filter_settings.use_ema_filter:
            filter_ema_candles, filter_ema = basic_utilities.cut_data_to_same_len(
                (
                    candle_closes,
                    tulipy.ema(
                        candle_closes, self.trading_mode.filter_settings.ema_period
                    ),
                )
            )
            is_ema_uptrend = filter_ema_candles > filter_ema
            is_ema_downtrend = filter_ema_candles < filter_ema
        else:
            is_ema_uptrend = [True] * data_length
            is_ema_downtrend = [True] * data_length
        if self.trading_mode.filter_settings.use_sma_filter:
            filter_sma_candles, filter_sma = basic_utilities.cut_data_to_same_len(
                (
                    candle_closes,
                    tulipy.sma(
                        candle_closes, self.trading_mode.filter_settings.sma_period
                    ),
                )
            )
            is_sma_uptrend = filter_sma_candles > filter_sma
            is_sma_downtrend = filter_sma_candles < filter_sma
        else:
            is_sma_uptrend = [True] * data_length
            is_sma_downtrend = [True] * data_length
        return is_ema_uptrend, is_ema_downtrend, is_sma_uptrend, is_sma_downtrend

    def _set_signals_from_prediction(
        self,
        prediction,
        _filters: utils.Filter,
        candle_index,
        previous_signals: list,
        start_long_trades: list,
        start_short_trades: list,
        is_bullishs,
        is_bearishs,
        alerts_bullish,
        alerts_bearish,
        is_bearish_changes,
        is_bullish_changes,
        exit_short_trades: list,
        exit_long_trades: list,
        bars_since_green_entry: int,
        bars_since_red_entry: int,
        is_buy_signals,
        is_sell_signals,
    ):
        # ============================
        # ==== Prediction Filters ====
        # ============================

        # Filtered Signal: The model's prediction of future price movement direction with user-defined filters applied
        signal = (
            utils.SignalDirection.long
            if prediction > 0 and _filters.filter_all[candle_index]
            else (
                utils.SignalDirection.short
                if prediction < 0 and _filters.filter_all[candle_index]
                else previous_signals[-1]
            )
        )
        is_different_signal_type: bool = previous_signals[-1] != signal
        previous_signals.append(signal)

        # Fractal Filters: Derived from relative appearances of signals in a given time series fractal/segment with a default length of 4 bars
        # is_early_signal_flip = previous_signals[-1] and (
        #     previous_signals[-2] or previous_signals[-3] or previous_signals[-4]
        # )
        is_buy_signal = (
            signal == utils.SignalDirection.long and _filters.is_uptrend[candle_index]
        )
        is_buy_signals.append(is_buy_signal)
        is_sell_signal = (
            signal == utils.SignalDirection.short
            and _filters.is_downtrend[candle_index]
        )
        is_sell_signals.append(is_sell_signal)

        is_new_buy_signal = is_buy_signal and is_different_signal_type
        is_new_sell_signal = is_sell_signal and is_different_signal_type

        # ===========================
        # ==== Entries and Exits ====
        # ===========================

        # Entry Conditions: Booleans for ML Model Position Entries
        start_long_trade = (
            is_new_buy_signal
            and is_bullishs[candle_index]
            and _filters.is_uptrend[candle_index]
        )
        start_long_trades.append(start_long_trade)
        start_short_trade = (
            is_new_sell_signal
            and is_bearishs[candle_index]
            and _filters.is_downtrend[candle_index]
        )
        start_short_trades.append(start_short_trade)

        # exits

        # utils.ExitTypes.SWITCH_SIDES doesnt need exits

        if self.trading_mode.general_settings.exit_type == utils.ExitTypes.FOUR_BARS:
            # Bar-Count Filters: Represents strict filters based on a pre-defined holding period of 4 bars
            bars_since_green_entry, bars_since_red_entry = self._handle_four_bar_exit(
                bars_since_green_entry,
                bars_since_red_entry,
                exit_short_trades,
                exit_long_trades,
                start_long_trade,
                start_short_trade,
            )
        # elif self.trading_mode.general_settings.exit_type == utils.ExitTypes.DYNAMIC:
        # TODO
        #     pass

        #     if alerts_bullish[candle_index]:
        #         bars_since_red_exit = 0
        #     else:
        #         bars_since_red_exit += 1
        #     if alerts_bearish[candle_index]:
        #         bars_since_green_exit = 0
        #     else:
        #         bars_since_green_exit += 1

        #     # Dynamic Exit Conditions: Booleans for ML Model Position Exits based on Fractal Filters and Kernel Regression Filters
        #     last_signal_was_bullish = bars_since_green_entry < bars_since_red_entry
        #     last_signal_was_bearish = bars_since_red_entry < bars_since_green_entry
        #     is_valid_short_exit = bars_since_green_exit > bars_since_red_entry
        #     is_valid_long_exit = bars_since_green_exit > bars_since_green_entry
        #     end_long_trade_dynamic = (
        #         is_bearish_changes[candle_index] and previous_is_valid_long_exit
        #     )
        #     end_short_trade_dynamic = (
        #         is_bullish_changes[candle_index] and previous_is_valid_short_exit
        #     )
        #     previous_is_valid_short_exit = is_valid_short_exit
        #     previous_is_valid_long_exit = is_valid_long_exit

        #     # # Fixed Exit Conditions: Booleans for ML Model Position Exits based on a Bar-Count Filters
        #     # end_long_trade_strict = (
        #     #     (is_held_four_bars and is_last_signal_buy)
        #     #     or (
        #     #         is_held_less_than_four_bars
        #     #         and is_new_sell_signal
        #     #         and is_last_signal_buy
        #     #     )
        #     # ) and start_long_trades[-5]
        #     # end_short_trade_strict = (
        #     #     (is_held_four_bars and is_last_signal_sell)
        #     #     or (
        #     #         is_held_less_than_four_bars
        #     #         and is_new_buy_signal
        #     #         and is_last_signal_sell
        #     #     )
        #     # ) and start_short_trades[-5]
        #     # is_dynamic_exit_valid = (
        #     #     not self.trading_mode.filter_settings.use_ema_filter
        #     #     and not self.trading_mode.filter_settings.use_sma_filter
        #     #     and not self.trading_mode.kernel_settings.use_kernel_smoothing
        #     # )
        #     # end_long_trade = self.trading_mode.general_settings.use_dynamic_exits and (
        #     #     end_long_trade_dynamic
        #     #     if is_dynamic_exit_valid
        #     #     else end_long_trade_strict
        #     # )
        #     # end_short_trade = self.trading_mode.general_settings.use_dynamic_exits and (
        #     #     end_short_trade_dynamic
        #     #     if is_dynamic_exit_valid
        #     #     else end_short_trade_strict
        #     # )
        return bars_since_green_entry, bars_since_red_entry

    def _handle_four_bar_exit(
        self,
        bars_since_green_entry: int,
        bars_since_red_entry: int,
        exit_short_trades: list,
        exit_long_trades: list,
        start_long_trade: bool,
        start_short_trade: bool,
    ):
        # TODO to compute in one go:
        #   use shifted start_long_trade / start_short_trade arrays for exits
        #   + use numpy.where for other side signals for bars_since <4
        if start_long_trade:
            bars_since_green_entry = 0
        else:
            bars_since_green_entry += 1
        if start_short_trade:
            bars_since_red_entry = 0
        else:
            bars_since_red_entry += 1

        if bars_since_red_entry == 4:
            exit_short_trades.append(True)
            exit_long_trades.append(False)
        elif bars_since_green_entry == 4:
            exit_long_trades.append(True)
            exit_short_trades.append(False)
        else:
            if bars_since_red_entry < 4 and start_long_trade:
                exit_short_trades.append(True)
            else:
                exit_short_trades.append(False)
            if bars_since_green_entry < 4 and start_short_trade:
                exit_long_trades.append(True)
            else:
                exit_long_trades.append(False)
        return bars_since_green_entry, bars_since_red_entry

    def _get_y_train_series(self, user_selected_candles):
        cutted_candles, shifted_candles = utils.shift_data(user_selected_candles, 4)
        return numpy.where(
            shifted_candles < cutted_candles,
            utils.SignalDirection.short,
            numpy.where(
                shifted_candles > cutted_candles,
                utils.SignalDirection.long,
                utils.SignalDirection.neutral,
            ),
        )

    async def _handle_plottings(
        self,
        ctx,
        y_train_series,
        _filters,
        candle_closes,
        candle_highs,
        candle_lows,
        candle_times,
        candles_hlc3,
        candles_ohlc4,
        feature_arrays,
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
        recentAtr,
        historicalAtr,
        historical_predictions,
        start_long_trades,
        start_short_trades,
        exit_short_trades,
        exit_long_trades,
        previous_signals,
        is_buy_signals,
        is_sell_signals,
    ):
        slightly_below_lows = candle_lows * 0.999
        slightly_above_highs = candle_highs * 1.001
        await self._handle_full_history_plottings(
            ctx,
            y_train_series,
            _filters,
            candle_closes,
            candle_highs,
            candle_lows,
            candle_times,
            candles_hlc3,
            candles_ohlc4,
            feature_arrays,
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
            recentAtr,
            historicalAtr,
            slightly_below_lows,
            slightly_above_highs,
        )
        await self._handle_short_history_plottings(
            ctx,
            historical_predictions,
            candle_times,
            start_long_trades,
            start_short_trades,
            exit_short_trades,
            exit_long_trades,
            slightly_below_lows,
            slightly_above_highs,
            previous_signals,
            is_buy_signals,
            is_sell_signals,
        )

    async def _handle_short_history_plottings(
        self,
        ctx: context_management.Context,
        historical_predictions,
        candle_times,
        start_long_trades,
        start_short_trades,
        exit_short_trades,
        exit_long_trades,
        slightly_below_lows,
        slightly_above_highs,
        previous_signals,
        is_buy_signals,
        is_sell_signals,
    ):
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
        )
        await matrix_plots.plot_conditional(
            ctx=ctx,
            title="Start Short Trades",
            signals=start_short_trades,
            values=slightly_above_highs,
            times=candle_times,
            value_key="st-s",
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
        y_train_series,
        _filters,
        candle_closes,
        candle_highs,
        candle_lows,
        candle_times,
        candles_hlc3,
        candles_ohlc4,
        feature_arrays,
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
        recentAtr,
        historicalAtr,
        slightly_below_lows,
        slightly_above_highs,
    ):
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
            recentAtr,
            historicalAtr,
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
                recentAtr,
                historicalAtr,
                slightly_below_lows,
                slightly_above_highs,
            )
        )
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
            if recentAtr:
                additional_values_by_key["recentAtr"] = recentAtr
                await plotting.plot(
                    ctx,
                    title="recentAtr",
                    cache_value="recentAtr",
                    chart="sub-chart",
                )

            if historicalAtr:
                additional_values_by_key["historicalAtr"] = historicalAtr
                await plotting.plot(
                    ctx,
                    title="historicalAtr",
                    cache_value="historicalAtr",
                    chart="sub-chart",
                )

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
        candle_closes,
        data_length,
        candles_ohlc4,
        candle_highs,
        candle_lows,
        user_selected_candles,
    ) -> utils.Filter:

        # Filter object for filtering the ML predictions
        (
            is_ema_uptrend,
            is_ema_downtrend,
            is_sma_uptrend,
            is_sma_downtrend,
        ) = self._get_ma_filters(candle_closes, data_length)
        volatility, recentAtr, historicalAtr = ml_extensions.filter_volatility(
            candle_highs=candle_highs,
            candle_lows=candle_lows,
            candle_closes=candle_closes,
            min_length=1,
            max_length=10,
            use_volatility_filter=self.trading_mode.filter_settings.use_volatility_filter,
        )
        regime = ml_extensions.regime_filter(
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
        return _filter, recentAtr, historicalAtr

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

    def get_kernel_data(self, user_selected_candles, data_length: int) -> tuple:
        # TODO colors
        # c_green = color.new(#009988, 20)
        # c_red = color.new(#CC3311, 20)
        # transparent = color.new(#000000, 100)

        yhat1: npt.NDArray[numpy.float64] = kernel.rationalQuadratic(
            user_selected_candles,
            self.trading_mode.kernel_settings.lookback_window,
            self.trading_mode.kernel_settings.relative_weighting,
            self.trading_mode.kernel_settings.regression_level,
        )
        yhat2: npt.NDArray[numpy.float64] = kernel.gaussian(
            user_selected_candles,
            self.trading_mode.kernel_settings.lookback_window
            - self.trading_mode.kernel_settings.lag,
            self.trading_mode.kernel_settings.regression_level,
        )
        yhat1, yhat2 = basic_utilities.cut_data_to_same_len((yhat1, yhat2))

        kernel_estimate: npt.NDArray[numpy.float64] = yhat1
        # Kernel Rates of Change
        # shift and cut data for numpy
        yhat1_cutted_1, yhat1_shifted_1 = utils.shift_data(yhat1, 1)
        yhat1_cutted_2, yhat1_shifted_2 = utils.shift_data(yhat1, 2)
        was_bearish_rates: npt.NDArray[numpy.bool_] = yhat1_shifted_2 > yhat1_cutted_2
        was_bullish_rates: npt.NDArray[numpy.bool_] = yhat1_shifted_2 < yhat1_cutted_2

        is_bearish_rates: npt.NDArray[numpy.bool_] = yhat1_shifted_1 > yhat1_cutted_1
        is_bullish_rates: npt.NDArray[numpy.bool_] = yhat1_shifted_1 < yhat1_cutted_1

        is_bearish_rates, was_bullish_rates = basic_utilities.cut_data_to_same_len(
            (is_bearish_rates, was_bullish_rates)
        )
        is_bearish_changes: npt.NDArray[numpy.bool_] = numpy.logical_and(
            is_bearish_rates, was_bullish_rates
        )
        is_bullish_rates, was_bearish_rates = basic_utilities.cut_data_to_same_len(
            (is_bullish_rates, was_bearish_rates)
        )
        is_bullish_changes: npt.NDArray[numpy.bool_] = numpy.logical_and(
            is_bullish_rates, was_bearish_rates
        )
        # Kernel Crossovers
        is_bullish_cross_alerts, is_bearish_cross_alerts = utils.get_is_crossing_data(
            yhat2, yhat1
        )
        is_bullish_smooths: npt.NDArray[numpy.bool_] = yhat2 >= yhat1
        is_bearish_smooths: npt.NDArray[numpy.bool_] = yhat2 <= yhat1

        # # Kernel Colors
        # TODO
        # # color colorByCross = isBullishSmooth ? c_green : c_red
        # # color colorByRate = isBullishRate ? c_green : c_red
        # # color plotColor = showKernelEstimate ? (useKernelSmoothing ? colorByCross : colorByRate) : transparent
        # # plot(kernelEstimate, color=plotColor, linewidth=2, title="Kernel Regression Estimate")

        # # Alert Variables
        alerts_bullish: npt.NDArray[numpy.bool_] = (
            is_bullish_cross_alerts
            if self.trading_mode.kernel_settings.use_kernel_smoothing
            else is_bullish_changes
        )
        alerts_bearish: npt.NDArray[numpy.bool_] = (
            is_bearish_cross_alerts
            if self.trading_mode.kernel_settings.use_kernel_smoothing
            else is_bearish_changes
        )
        # Bullish and Bearish Filters based on Kernel
        is_bullishs: npt.NDArray[numpy.bool_] = (
            (
                is_bullish_smooths
                if self.trading_mode.kernel_settings.use_kernel_smoothing
                else is_bullish_rates
            )
            if self.trading_mode.kernel_settings.use_kernel_filter
            else [True] * data_length
        )
        is_bearishs: npt.NDArray[numpy.bool_] = (
            (
                is_bearish_smooths
                if self.trading_mode.kernel_settings.use_kernel_smoothing
                else is_bearish_rates
            )
            if self.trading_mode.kernel_settings.use_kernel_filter
            else [True] * data_length
        )
        return (
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

    async def _get_candle_data(
        self,
        ctx: context_management.Context,
        candle_source_name,
    ):
        max_history = True if ctx.exchange_manager.is_backtesting else False
        candle_times = await exchange_public_data.Time(ctx, max_history=max_history)
        candle_opens = await exchange_public_data.Open(ctx, max_history=max_history)
        candle_closes = await exchange_public_data.Close(ctx, max_history=max_history)
        candle_highs = await exchange_public_data.High(ctx, max_history=max_history)
        candle_lows = await exchange_public_data.Low(ctx, max_history=max_history)
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
                ctx, max_history=max_history
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

    def _get_max_bars_back_index(self, cutted_data_length) -> int:
        if cutted_data_length >= self.trading_mode.general_settings.max_bars_back:
            if self.ctx.exchange_manager.is_backtesting:
                return self.trading_mode.general_settings.max_bars_back
            return cutted_data_length - self.trading_mode.general_settings.max_bars_back
        else:
            self.logger.warning(
                "Not enough historical bars for the current max_bars_back. "
                "Either increase the amount of initialized candles "
                "or reduce the max_bars_back setting. Classification will run "
                f"on {cutted_data_length} bars"
            )
            return 0  # start on first bar with all filters, indicators etc. available

    async def _trade_live_candle(
        self,
        s_time,
        start_short_trades,
        start_long_trades,
        exit_short_trades,
        exit_long_trades,
    ):
        basic_utilities.end_measure_time(
            s_time,
            " Lorentzian Classification - classifying candles",
        )
        s_time = basic_utilities.start_measure_time()
        if start_short_trades[-1]:
            await self.enter_short_trade()
        if start_long_trades[-1]:
            await self.enter_long_trade()
        has_exit_signals = len(exit_short_trades) and len(exit_long_trades)
        if has_exit_signals:
            if exit_short_trades[-1]:
                await self.exit_short_trade()
            if exit_long_trades[-1]:
                await self.exit_long_trade()
        basic_utilities.end_measure_time(
            s_time,
            " Lorentzian Classification - trading eventual singals",
        )

    def _cache_backtesting_signals(
        self,
        ctx,
        s_time,
        candle_times,
        start_short_trades,
        start_long_trades,
        exit_short_trades,
        exit_long_trades,
    ) -> bool:
        # cache signals for backtesting
        has_exit_signals = len(exit_short_trades) and len(exit_long_trades)
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
        self.start_short_trades_cache = {}
        self.start_long_trades_cache = {}
        if has_exit_signals:
            self.exit_long_trades_cache = {}
            self.exit_short_trades_cache = {}
        trades_count = 0
        for index, candle_time in enumerate(candle_times):
            candle_time = int(candle_time)
            self.start_short_trades_cache[candle_time] = start_short_trades[index]
            self.start_long_trades_cache[candle_time] = start_long_trades[index]
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
                open_time = candle_time - (
                    enums.TimeFramesMinutes[enums.TimeFrames(self.ctx.time_frame)] * 60
                )
                candle_times_to_whitelist.append(candle_time)
                candle_times_to_whitelist.append(open_time)
        backtesting_settings.register_backtesting_timestamp_whitelist(
            ctx, list(set(candle_times_to_whitelist))
        )
        basic_utilities.end_measure_time(
            s_time,
            f" Lorentzian Classification - building strategy for "
            f"{self.ctx.time_frame} {trades_count} trades",
        )

    async def _trade_cached_backtesting_candles_if_available(self, ctx) -> bool:
        if ctx.exchange_manager.is_backtesting:
            if self.start_long_trades_cache is not None:
                trigger_cache_timestamp = int(ctx.trigger_cache_timestamp)
                try:
                    if self.start_short_trades_cache[trigger_cache_timestamp]:
                        await self.enter_short_trade()
                    elif self.start_long_trades_cache[trigger_cache_timestamp]:
                        await self.enter_long_trade()
                    if (
                        self.exit_short_trades_cache
                        and self.exit_short_trades_cache[trigger_cache_timestamp]
                    ):
                        await self.exit_short_trade()
                    elif (
                        self.exit_long_trades_cache
                        and self.exit_long_trades_cache[trigger_cache_timestamp]
                    ):
                        await self.exit_long_trade()
                    return True
                except KeyError as error:
                    print(f"No cached strategy signal for this candle - error: {error}")
                    return True
        return False

    async def init_order_settings(self, ctx):
        if activate_managed_order:
            long_settings_name = "long_order_settings"
            await basic_keywords.user_input(
                ctx,
                long_settings_name,
                "object",
                None,
                title="Long Trade Settings",
                editor_options={
                    "grid_columns": 12,
                },
                other_schema_values={"display_as_tab": True},
            )
            if activate_managed_order:
                self.managend_orders_long_settings = (
                    await activate_managed_order.activate_managed_orders(
                        self,
                        parent_input_name=long_settings_name,
                        name_prefix="long",
                    )
                )
            short_settings_name = "short_order_settings"
            await basic_keywords.user_input(
                ctx,
                short_settings_name,
                "object",
                None,
                title="short Trade Settings",
                editor_options={
                    "grid_columns": 12,
                },
                other_schema_values={"display_as_tab": True},
            )
            self.managend_orders_short_settings = (
                await activate_managed_order.activate_managed_orders(
                    self,
                    parent_input_name=short_settings_name,
                    name_prefix="short",
                )
            )
        else:
            await basic_keywords.set_leverage(
                ctx, self.trading_mode.order_settings.leverage
            )

    async def enter_short_trade(self):
        if self.trading_mode.order_settings.enable_long_orders:
            await self.exit_long_trade()
        if self.trading_mode.order_settings.enable_short_orders:
            if activate_managed_order:
                await activate_managed_order.managed_order(
                    self,
                    trading_side="short",
                    orders_settings=self.managend_orders_short_settings,
                )
            else:
                await market_order.market(
                    self.ctx,
                    target_position=f"-{self.trading_mode.order_settings.short_order_volume}%a",
                )

    async def enter_long_trade(self):
        if self.trading_mode.order_settings.enable_short_orders:
            await self.exit_short_trade()
        if self.trading_mode.order_settings.enable_long_orders:
            if activate_managed_order:
                await activate_managed_order.managed_order(
                    self,
                    trading_side="long",
                    orders_settings=self.managend_orders_long_settings,
                )
            else:
                await market_order.market(
                    self.ctx,
                    target_position=f"{self.trading_mode.order_settings.long_order_volume}%a",
                )

    async def exit_short_trade(self):
        await market_order.market(self.ctx, target_position=0, reduce_only=True)

    async def exit_long_trade(self):
        await market_order.market(self.ctx, target_position=0, reduce_only=True)
