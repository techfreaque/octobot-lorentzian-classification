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
import numpy
import tulipy

import octobot_commons.enums as enums
import octobot_evaluators.util as evaluators_util
from octobot_trading.modes.script_keywords.context_management import Context
from tentacles.Meta.Keywords.matrix_library.matrix_basic_keywords.plottings.plots import plot_conditional
from tentacles.Meta.Keywords.scripting_library.data.reading import exchange_public_data
from tentacles.Meta.Keywords.scripting_library.data.writing import plotting
from tentacles.Trading.Mode.lorentzian_classification.kernel_functions import kernel
import tentacles.Trading.Mode.lorentzian_classification.utils as utils
import tentacles.Trading.Mode.lorentzian_classification.ml_extensions_2.ml_extensions as ml_extensions
from tentacles.Meta.Keywords.matrix_library.matrix_basic_keywords.tools.utilities import (
    cut_data_to_same_len,
)
import tentacles.Meta.Keywords.matrix_library.matrix_basic_keywords.mode.mode_base.trading_mode as trading_mode_basis

try:
    from tentacles.Evaluator.Util.candles_util import CandlesUtil
except (ModuleNotFoundError, ImportError) as error:
    raise RuntimeError("CandlesUtil tentacle is required to use HLC3") from error


class LorentzianClassificationScript(trading_mode_basis.MatrixModeProducer):
    async def evaluate_lorentzian_classification(
        self,
        ctx: Context,
    ):
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
        # _filters: utils.Filter = self._get_filters(
        _filters, recentAtr, historicalAtr = self._get_filters(
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
        ) = self.get_kernel_data(user_selected_candles, data_length)

        feature_arrays: utils.FeatureArrays = self.get_feature_arrays(
            candle_closes=candle_closes,
            candle_highs=candle_highs,
            candle_lows=candle_lows,
            candles_hlc3=candles_hlc3,
        )

        y_train_series = self.get_y_train_series(user_selected_candles)
        # TOD remove
        rma = utils.calculate_rma(candle_closes, 15)

        # cut all historical data to same length for numpy and loop indizies being aligned
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
            candles_ohlc4,
            feature_arrays.f1,
            feature_arrays.f2,
            feature_arrays.f3,
            feature_arrays.f4,
            feature_arrays.f5,
            # is_bullishs,
            # is_bearishs,
            # alerts_bullish,
            # alerts_bearish,
            rma,
            recentAtr,
            historicalAtr,
        ) = cut_data_to_same_len(
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
                # is_bullishs,
                # is_bearishs,
                # alerts_bullish,
                # alerts_bearish,
                rma,
                recentAtr,
                historicalAtr,
            )
        )

        slightly_below_lows = candle_lows * 0.995
        await plot_conditional(
            ctx=ctx,
            title="filter_all",
            signals=_filters.filter_all,
            values=slightly_below_lows,
            times=candle_times,
            value_key="filter_all",
        )
        await plot_conditional(
            ctx=ctx,
            title="uptrend",
            signals=_filters.is_uptrend,
            values=slightly_below_lows,
            times=candle_times,
            value_key="uptrend",
        )
        await plot_conditional(
            ctx=ctx,
            title="downtrend",
            signals=_filters.is_downtrend,
            values=slightly_below_lows,
            times=candle_times,
            value_key="downtrend",
        )

        await ctx.set_cached_values(
            values=y_train_series,
            cache_keys=candle_times,
            value_key="yt",
            additional_values_by_key={
                "f1": feature_arrays.f1,
                "f2": feature_arrays.f2,
                "f3": feature_arrays.f3,
                "f4": feature_arrays.f4,
                "f5": feature_arrays.f5,
                "rma": rma,
                "recentAtr": recentAtr,
                "historicalAtr": historicalAtr,
            },
        )

        await plotting.plot(
            ctx,
            title="recentAtr",
            cache_value="recentAtr",
            chart="sub-chart",
        )
        await plotting.plot(
            ctx,
            title="historicalAtr",
            cache_value="historicalAtr",
            chart="sub-chart",
        )
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
        await plotting.plot(
            ctx,
            title="Feature 3",
            cache_value="f3",
            chart="sub-chart",
        )
        await plotting.plot(
            ctx,
            title="Feature 4",
            cache_value="f4",
            chart="sub-chart",
        )
        await plotting.plot(
            ctx,
            title="Feature 5",
            cache_value="f5",
            chart="sub-chart",
        )
        await plotting.plot(
            ctx,
            title="y_train_series",
            cache_value="yt",
            chart="sub-chart",
            own_yaxis=True,
        )
        await plotting.plot(
            ctx,
            title="rma",
            cache_value="rma",
            chart="sub-chart",
            own_yaxis=True,
        )
        cutted_data_length = len(candle_closes)
        max_bars_back_index = self.get_max_bars_back_index(cutted_data_length)

        # =================================
        # ==== Next Bar Classification ====
        # =================================

        # This model specializes specifically in predicting the direction of price
        # action over the course of the next 4 bars.
        # To avoid complications with the ML model, this value is hardcoded to 4 bars
        # but support for other training lengths may be added in the future.

        previous_signals: list = [utils.SignalDirection.neutral]
        bars_held: int = 0
        previous_is_valid_short_exit = False
        previous_is_valid_long_exit = False
        for candle_index in range(max_bars_back_index, cutted_data_length):
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

            this_y_train_series = y_train_series[:candle_index]
            # Variables used for ML Logic
            prediction: float = 0
            last_distance: float = -1
            size: int = min(
                self.trading_mode.general_settings.max_bars_back - 1,
                len(this_y_train_series) - 1,
            )
            size_Loop: int = (
                min(self.trading_mode.general_settings.max_bars_back - 1, size) + 1
            )
            distances: list = []
            predictions: list = []
            start_long_trades: list = []
            start_short_trades: list = []
            for candles_back in range(0, size_Loop):
                # TODO check if index is right
                candles_back_index = candle_index - candles_back - 1
                lorentzian_distance = self.get_lorentzian_distance(
                    candle_index=candle_index,
                    candles_back_index=candles_back_index,
                    feature_arrays=feature_arrays,
                )
                if lorentzian_distance >= last_distance and candles_back % 4:
                    last_distance = lorentzian_distance
                    distances.append(lorentzian_distance)
                    predictions.append(round(this_y_train_series[candles_back_index]))
                    if (
                        len(predictions)
                        > self.trading_mode.general_settings.neighbors_count
                    ):
                        last_distance = distances[
                            round(
                                self.trading_mode.general_settings.neighbors_count
                                * 3
                                / 4
                            )
                        ]
                        del distances[0]
                        del predictions[0]
            prediction = sum(predictions)
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
                    else previous_signals
                )
            )
            is_different_signal_type: bool = previous_signals[-1] != signal
            # Bar-Count Filters: Represents strict filters based on a pre-defined holding period of 4 bars
            if is_different_signal_type:
                bars_held = 0
            else:
                bars_held += 1
            is_held_four_bars = bars_held == 4
            is_held_less_than_four_bars = 0 < bars_held and bars_held < 4

            # Fractal Filters: Derived from relative appearances of signals in a given time series fractal/segment with a default length of 4 bars
            is_early_signal_flip = previous_signals[-1] and (
                previous_signals[-2] or previous_signals[-3] or previous_signals[-4]
            )
            is_buy_signal = (
                signal == utils.SignalDirection.long
                and _filters.is_uptrend[candle_index]
            )
            is_sell_signal = (
                signal == utils.SignalDirection.short
                and _filters.is_downtrend[candle_index]
            )
            is_last_signal_buy = (
                signal[-5] == utils.SignalDirection.long
                and _filters.is_uptrend[candle_index - 4]
            )
            is_last_signal_sell = (
                signal[-5] == utils.SignalDirection.short
                and _filters.is_downtrend[candle_index - 4]
            )
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
            if start_long_trade:
                bars_since_green_entry = 0
            else:
                bars_since_green_entry += 1
            start_short_trade = (
                is_new_sell_signal
                and is_bearishs[candle_index]
                and _filters.is_downtrend[candle_index]
            )
            start_short_trades.append(start_short_trade)
            if start_short_trade:
                bars_since_red_entry = 0
            else:
                bars_since_red_entry += 1

            if alerts_bullish[candle_index]:
                bars_since_red_exit = 0
            else:
                bars_since_red_exit += 1
            if alerts_bearish[candle_index]:
                bars_since_green_exit = 0
            else:
                bars_since_green_exit += 1

            # Dynamic Exit Conditions: Booleans for ML Model Position Exits based on Fractal Filters and Kernel Regression Filters
            last_signal_was_bullish = bars_since_green_entry < bars_since_red_entry
            last_signal_was_bearish = bars_since_red_entry < bars_since_green_entry
            is_valid_short_exit = bars_since_green_exit > bars_since_red_entry
            is_valid_long_exit = bars_since_green_exit > bars_since_green_entry
            end_long_trade_dynamic = (
                is_bearish_changes[candle_index] and previous_is_valid_long_exit
            )
            end_short_trade_dynamic = (
                is_bullish_changes[candle_index] and previous_is_valid_short_exit
            )
            previous_is_valid_short_exit = is_valid_short_exit
            previous_is_valid_long_exit = is_valid_long_exit

            # Fixed Exit Conditions: Booleans for ML Model Position Exits based on a Bar-Count Filters
            end_long_trade_strict = (
                (is_held_four_bars and is_last_signal_buy)
                or (
                    is_held_less_than_four_bars
                    and is_new_sell_signal
                    and is_last_signal_buy
                )
            ) and start_long_trades[-5]
            end_short_trade_strict = (
                (is_held_four_bars and is_last_signal_sell)
                or (
                    is_held_less_than_four_bars
                    and is_new_buy_signal
                    and is_last_signal_sell
                )
            ) and start_short_trades[-5]
            is_dynamic_exit_valid = (
                not self.trading_mode.filter_settings.use_ema_filter
                and not self.trading_mode.filter_settings.use_sma_filter
                and not self.trading_mode.kernel_settings.use_kernel_smoothing
            )
            end_long_trade = self.trading_mode.general_settings.use_dynamic_exits and (
                end_long_trade_dynamic
                if is_dynamic_exit_valid
                else end_long_trade_strict
            )
            end_short_trade = self.trading_mode.general_settings.use_dynamic_exits and (
                end_short_trade_dynamic
                if is_dynamic_exit_valid
                else end_short_trade_strict
            )

            previous_signals.append(signal)

    def get_filters(self, candle_closes, data_length):
        if self.trading_mode.filter_settings.use_ema_filter:
            filter_ema_candles, filter_ema = cut_data_to_same_len(
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
            filter_sma_candles, filter_sma = cut_data_to_same_len(
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

    def get_y_train_series(self, user_selected_candles):
        # TODO check if 4/-5 is same as on tradingview
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

    def get_lorentzian_distance(
        self,
        candle_index: int,
        candles_back_index: int,
        feature_arrays: utils.FeatureArrays,
    ) -> float:
        if self.feature_engineering_settings.feature_count == 5:
            return (
                math.log(
                    1
                    + abs(
                        feature_arrays.f1[candle_index]
                        - feature_arrays.f1[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f2[candle_index]
                        - feature_arrays.f2[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f3[candle_index]
                        - feature_arrays.f3[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f4[candle_index]
                        - feature_arrays.f4[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f5[candle_index]
                        - feature_arrays.f5[candles_back_index]
                    )
                )
            )
        elif self.feature_engineering_settings.feature_count == 4:
            return (
                math.log(
                    1
                    + abs(
                        feature_arrays.f1[candle_index]
                        - feature_arrays.f1[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f2[candle_index]
                        - feature_arrays.f2[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f3[candle_index]
                        - feature_arrays.f3[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f4[candle_index]
                        - feature_arrays.f4[candles_back_index]
                    )
                )
            )
        elif self.feature_engineering_settings.feature_count == 3:
            return (
                math.log(
                    1
                    + abs(
                        feature_arrays.f1[candle_index]
                        - feature_arrays.f1[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f2[candle_index]
                        - feature_arrays.f2[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f3[candle_index]
                        - feature_arrays.f3[candles_back_index]
                    )
                )
            )
        elif self.feature_engineering_settings.feature_count == 2:
            return math.log(
                1
                + abs(
                    feature_arrays.f1[candle_index]
                    - feature_arrays.f1[candles_back_index]
                )
            ) + math.log(
                1
                + abs(
                    feature_arrays.f2[candle_index]
                    - feature_arrays.f2[candles_back_index]
                )
            )

    def _get_filters(
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
        ) = self.get_filters(candle_closes, data_length)
        volatility, recentAtr, historicalAtr = ml_extensions.filter_volatility(
            candle_highs=candle_highs,
            candle_lows=candle_lows,
            candle_closes=candle_closes,
            min_length=1,
            max_length=10,
            use_volatility_filter=self.trading_mode.filter_settings.use_volatility_filter,
        )
        _filter: utils.Filter = utils.Filter(
            volatility=volatility,
            regime=ml_extensions.regime_filter(
                ohlc4=candles_ohlc4,
                highs=candle_highs,
                lows=candle_lows,
                threshold=self.trading_mode.filter_settings.regime_threshold,
                use_regime_filter=self.trading_mode.filter_settings.use_regime_filter,
            ),
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

    def get_feature_arrays(
        self, candle_closes, candle_highs, candle_lows, candles_hlc3
    ) -> utils.FeatureArrays:
        return utils.FeatureArrays(
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
        # c_green = color.new(#009988, 20)
        # c_red = color.new(#CC3311, 20)
        # transparent = color.new(#000000, 100)
        yhat1: numpy.array = kernel.rationalQuadratic(
            user_selected_candles,
            self.trading_mode.kernel_settings.lookback_window,
            self.trading_mode.kernel_settings.relative_weighting,
            self.trading_mode.kernel_settings.regression_level,
        )
        yhat2: numpy.array = kernel.gaussian(
            user_selected_candles,
            self.trading_mode.kernel_settings.lookback_window
            - self.trading_mode.kernel_settings.lag,
            self.trading_mode.kernel_settings.regression_level,
        )
        yhat1, yhat2 = cut_data_to_same_len((yhat1, yhat2))

        kernelEstimate: numpy.array = yhat1
        # Kernel Rates of Change
        # shift and cut data for numpy
        yhat1_cutted_1, yhat1_shifted_1 = utils.shift_data(yhat1, 1)
        yhat1_cutted_2, yhat1_shifted_2 = utils.shift_data(yhat1_shifted_1, 1)
        was_bearish_rates: numpy.array = yhat1_shifted_2 > yhat1_cutted_2
        was_bullish_rates: numpy.array = yhat1_shifted_2 < yhat1_cutted_2
        is_bearish_rates: numpy.array = yhat1_shifted_1 > yhat1_cutted_1
        is_bullish_rates: numpy.array = yhat1_shifted_1 < yhat1_cutted_1
        is_bearish_changes: numpy.array = numpy.logical_and(
            is_bearish_rates, was_bullish_rates
        )
        is_bullish_changes: numpy.array = numpy.logical_and(
            is_bullish_rates, was_bearish_rates
        )
        # Kernel Crossovers
        is_bullish_cross_alerts, is_bearish_cross_alerts = utils.get_is_crossing_data(
            yhat2, yhat1
        )
        is_bullish_smooths: numpy.array = yhat2 >= yhat1
        is_bearish_smooths: numpy.array = yhat2 <= yhat1

        # # Kernel Colors
        # # color colorByCross = isBullishSmooth ? c_green : c_red
        # # color colorByRate = isBullishRate ? c_green : c_red
        # # color plotColor = showKernelEstimate ? (useKernelSmoothing ? colorByCross : colorByRate) : transparent
        # # plot(kernelEstimate, color=plotColor, linewidth=2, title="Kernel Regression Estimate")
        # # Alert Variables
        alerts_bullish = (
            is_bullish_cross_alerts
            if self.trading_mode.kernel_settings.use_kernel_smoothing
            else is_bullish_changes
        )
        alerts_bearish = (
            is_bearish_cross_alerts
            if self.trading_mode.kernel_settings.use_kernel_smoothing
            else is_bearish_changes
        )
        # Bullish and Bearish Filters based on Kernel
        is_bullishs: numpy.array = (
            (
                is_bullish_smooths
                if self.trading_mode.kernel_settings.use_kernel_smoothing
                else is_bullish_rates
            )
            if self.trading_mode.kernel_settings.use_kernel_filter
            else [True] * data_length
        )
        is_bearishs: numpy.array = (
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
        )

    async def _get_candle_data(
        self,
        ctx: Context,
        candle_source_name,
    ):
        candle_times = await exchange_public_data.Time(ctx)
        candle_opens = await exchange_public_data.Open(ctx)
        candle_closes = await exchange_public_data.Close(ctx)
        candle_highs = await exchange_public_data.High(ctx)
        candle_lows = await exchange_public_data.Low(ctx)
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
            user_selected_candles = await exchange_public_data.Open(ctx)
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

    def get_max_bars_back_index(self, cutted_data_length) -> int:
        if cutted_data_length >= self.trading_mode.general_settings.max_bars_back:
            return cutted_data_length - self.trading_mode.general_settings.max_bars_back
        else:
            # todo logger warning
            return cutted_data_length
