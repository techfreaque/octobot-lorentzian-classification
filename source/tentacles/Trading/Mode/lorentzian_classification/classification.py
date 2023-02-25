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
import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords
import octobot_trading.modes.script_keywords.context_management as context_management
import tentacles.Meta.Keywords.scripting_library.backtesting.backtesting_settings as backtesting_settings
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_public_data as exchange_public_data
import tentacles.Meta.Keywords.scripting_library.data.writing.plotting as plotting
from tentacles.Meta.Keywords.scripting_library.orders.order_types.market_order import (
    market,
)

import tentacles.Trading.Mode.lorentzian_classification.kernel_functions.kernel as kernel
import tentacles.Trading.Mode.lorentzian_classification.utils as utils
import tentacles.Trading.Mode.lorentzian_classification.ml_extensions_2.ml_extensions as ml_extensions

import tentacles.Meta.Keywords.matrix_library.matrix_basic_keywords.tools.utilities as basic_utilities
import tentacles.Meta.Keywords.matrix_library.matrix_basic_keywords.mode.mode_base.trading_mode as trading_mode_basis
import tentacles.Meta.Keywords.matrix_library.matrix_basic_keywords.plottings.plots as matrix_plots

try:
    from tentacles.Evaluator.Util.candles_util import CandlesUtil
except (ModuleNotFoundError, ImportError) as error:
    raise RuntimeError("CandlesUtil tentacle is required to use HLC3") from error

# try:
#     import tentacles.Meta.Keywords.matrix_library.matrix_pro_keywords.managed_order_pro.managed_orders as managed_orders
#     import tentacles.Meta.Keywords.matrix_library.matrix_pro_keywords.managed_order_pro.activate_managed_order as activate_managed_order
#     import tentacles.Meta.Keywords.matrix_library.matrix_pro_keywords.managed_order_pro.settings.all_settings as all_settings
# except (ImportError, ModuleNotFoundError):
managed_orders = None
activate_managed_order = None
all_settings = None


class LorentzianClassificationScript(trading_mode_basis.MatrixModeProducer):
    if managed_orders:
        managend_orders_long_settings: all_settings.ManagedOrdersSettings = None
        managend_orders_short_settings: all_settings.ManagedOrdersSettings = None
    else:
        managend_orders_long_settings = None
        managend_orders_short_settings = None

    start_long_trades_cache: dict = None
    start_short_trades_cache: dict = None

    async def evaluate_lorentzian_classification(
        self,
        ctx: context_management.Context,
    ):
        if await self._trade_cached_backtesting_candles_if_available(ctx):
            return
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
            is_bullish_cross_alerts,
            is_bearish_cross_alerts,
            kernel_estimate,
            yhat2,
            is_bearish_rates,
            was_bullish_rates,
            is_bullish_rates,
            was_bearish_rates,
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
            rma,
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
                rma,
                recentAtr,
                historicalAtr,
            )
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
        last_signal = utils.SignalDirection.neutral

        historical_predictions: list = []
        lorentzian_distance_test: list = []
        bars_held: int = 0
        previous_is_valid_short_exit = False
        previous_is_valid_long_exit = False
        bars_since_red_entry = 0
        bars_since_green_entry = 0
        bars_since_red_exit = 0
        bars_since_green_exit = 0

        distances: list = []
        last_distances: list = []
        predictions: list = []
        start_long_trades: list = []
        start_short_trades: list = []
        for candle_index in range(max_bars_back_index, cutted_data_length):
            self.classify_current_candle(
                y_train_series,
                candle_index,
                feature_arrays,
                historical_predictions,
                _filters,
                previous_signals,
                is_bullishs,
                is_bearishs,
                alerts_bullish,
                alerts_bearish,
                is_bearish_changes,
                is_bullish_changes,
                last_signal,
                bars_held,
                previous_is_valid_short_exit,
                previous_is_valid_long_exit,
                bars_since_red_entry,
                bars_since_green_entry,
                bars_since_red_exit,
                bars_since_green_exit,
                distances,
                predictions,
                last_distances,
                start_long_trades,
                start_short_trades,
            )
        if ctx.exchange_manager.is_backtesting:
            self._cache_backtesting_signals(
                ctx, candle_times, start_short_trades, start_long_trades
            )
        else:
            await self._trade_live_candle(start_short_trades, start_long_trades)
        await self._handle_plottings(
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
            rma,
            recentAtr,
            historicalAtr,
            historical_predictions,
            # distances,
            last_distances,
            start_long_trades,
            start_short_trades,
        )

    def classify_current_candle(
        self,
        y_train_series,
        candle_index: int,
        feature_arrays: utils.FeatureArrays,
        historical_predictions: list,
        _filters,
        previous_signals: list,
        is_bullishs,
        is_bearishs,
        alerts_bullish,
        alerts_bearish,
        is_bearish_changes,
        is_bullish_changes,
        last_signal,
        bars_held: int,
        previous_is_valid_short_exit,
        previous_is_valid_long_exit,
        bars_since_red_entry: int,
        bars_since_green_entry: int,
        bars_since_red_exit: int,
        bars_since_green_exit: int,
        distances: list,
        predictions: list,
        last_distances: list,
        start_long_trades: list,
        start_short_trades: list,
    ):
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

        # Variables used for ML Logic
        this_y_train_series = y_train_series[:candle_index]
        last_distance: float = -1
        prediction: float = 0
        size: int = min(
            self.trading_mode.general_settings.max_bars_back - 1,
            len(this_y_train_series) - 1,
        )
        size_Loop: int = min(self.trading_mode.general_settings.max_bars_back - 1, size)

        for candles_back in range(0, size_Loop):
            candles_back_index = candle_index - size_Loop + candles_back
            lorentzian_distance = self.get_lorentzian_distance(
                candle_index=candle_index,
                candles_back_index=candles_back,
                feature_arrays=feature_arrays,
            )
            if lorentzian_distance >= last_distance and candles_back % 4:
                last_distance = lorentzian_distance
                predictions.append(round(y_train_series[candles_back]))
                distances.append(lorentzian_distance)
                if (
                    len(predictions)
                    > self.trading_mode.general_settings.neighbors_count
                ):
                    last_distance = distances[
                        round(
                            self.trading_mode.general_settings.neighbors_count * 3 / 4
                        )
                    ]
                    del distances[0]
                    del predictions[0]
        prediction = sum(predictions)
        historical_predictions.append(prediction)
        last_distances.append(last_distance)
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

        # Bar-Count Filters: Represents strict filters based on a pre-defined holding period of 4 bars
        if is_different_signal_type:
            last_signal = signal
            bars_held = 0
        else:
            bars_held += 1
        is_held_four_bars = bars_held == 4
        is_held_less_than_four_bars = 0 < bars_held and bars_held < 4

        # Fractal Filters: Derived from relative appearances of signals in a given time series fractal/segment with a default length of 4 bars
        # is_early_signal_flip = previous_signals[-1] and (
        #     previous_signals[-2] or previous_signals[-3] or previous_signals[-4]
        # )
        is_buy_signal = (
            signal == utils.SignalDirection.long and _filters.is_uptrend[candle_index]
        )
        is_sell_signal = (
            signal == utils.SignalDirection.short
            and _filters.is_downtrend[candle_index]
        )
        is_last_signal_buy = (
            last_signal
            == utils.SignalDirection.long
            # and _filters.is_uptrend[candle_index - 4]
        )
        is_last_signal_sell = (
            last_signal
            == utils.SignalDirection.short
            # and _filters.is_downtrend[candle_index - 4]
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

        # # Fixed Exit Conditions: Booleans for ML Model Position Exits based on a Bar-Count Filters
        # end_long_trade_strict = (
        #     (is_held_four_bars and is_last_signal_buy)
        #     or (
        #         is_held_less_than_four_bars
        #         and is_new_sell_signal
        #         and is_last_signal_buy
        #     )
        # ) and start_long_trades[-5]
        # end_short_trade_strict = (
        #     (is_held_four_bars and is_last_signal_sell)
        #     or (
        #         is_held_less_than_four_bars
        #         and is_new_buy_signal
        #         and is_last_signal_sell
        #     )
        # ) and start_short_trades[-5]
        # is_dynamic_exit_valid = (
        #     not self.trading_mode.filter_settings.use_ema_filter
        #     and not self.trading_mode.filter_settings.use_sma_filter
        #     and not self.trading_mode.kernel_settings.use_kernel_smoothing
        # )
        # end_long_trade = self.trading_mode.general_settings.use_dynamic_exits and (
        #     end_long_trade_dynamic
        #     if is_dynamic_exit_valid
        #     else end_long_trade_strict
        # )
        # end_short_trade = self.trading_mode.general_settings.use_dynamic_exits and (
        #     end_short_trade_dynamic
        #     if is_dynamic_exit_valid
        #     else end_short_trade_strict
        # )

        return start_long_trades, start_short_trades

    def get_filters(self, candle_closes, data_length):
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

    def get_y_train_series(self, user_selected_candles):
        # TODO check if 4/ is same as on tradingview
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
        if self.trading_mode.feature_engineering_settings.feature_count == 5:
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
        elif self.trading_mode.feature_engineering_settings.feature_count == 4:
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
        elif self.trading_mode.feature_engineering_settings.feature_count == 3:
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
        elif self.trading_mode.feature_engineering_settings.feature_count == 2:
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
        rma,
        recentAtr,
        historicalAtr,
        historical_predictions,
        # distances,
        last_distances,
        start_long_trades,
        start_short_trades,
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
            rma,
            recentAtr,
            historicalAtr,
            slightly_below_lows,
            slightly_above_highs,
        )
        await self._handle_short_history_plottings(
            ctx,
            historical_predictions,
            last_distances,
            candle_times,
            start_long_trades,
            start_short_trades,
            slightly_below_lows,
            slightly_above_highs,
        )

    async def _handle_short_history_plottings(
        self,
        ctx: context_management.Context,
        historical_predictions,
        last_distances,
        candle_times,
        start_long_trades,
        start_short_trades,
        slightly_below_lows,
        slightly_above_highs,
    ):
        (
            historical_predictions,
            last_distances,
            candle_times,
            start_long_trades,
            start_short_trades,
            slightly_below_lows,
            slightly_above_highs,
        ) = basic_utilities.cut_data_to_same_len(
            (
                historical_predictions,
                last_distances,
                candle_times,
                start_long_trades,
                start_short_trades,
                slightly_below_lows,
                slightly_above_highs,
            )
        )
        await matrix_plots.plot_conditional(
            ctx=ctx,
            title="Start Long Trades",
            signals=start_long_trades,
            values=slightly_below_lows,
            times=candle_times,
            value_key="start_long_trades",
        )
        await matrix_plots.plot_conditional(
            ctx=ctx,
            title="Start Short Trades",
            signals=start_short_trades,
            values=slightly_above_highs,
            times=candle_times,
            value_key="start_short_trades",
        )
        await ctx.set_cached_values(
            values=historical_predictions,
            cache_keys=candle_times,
            value_key="historical_predictions",
        )
        await ctx.set_cached_values(
            values=last_distances,
            cache_keys=candle_times,
            value_key="last_distances",
        )
        # await plotting.plot(
        #     ctx,
        #     title="lorentzian_distance_test",
        #     cache_value="lorentzian_distance_test",
        #     chart="sub-chart",
        # )
        await plotting.plot(
            ctx,
            title="last_distances",
            cache_value="last_distances",
            chart="sub-chart",
        )
        await plotting.plot(
            ctx,
            title="historical_predictions",
            cache_value="historical_predictions",
            chart="sub-chart",
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
        rma,
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
            rma,
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
                rma,
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
                signals=_filters.volatility_rates,
                values=slightly_below_lows,
                times=candle_times,
                value_key="volatility",
            )
        if self.trading_mode.filter_settings.plot_regime_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="Regime filter",
                signals=_filters.regimerish_rates,
                values=slightly_below_lows,
                times=candle_times,
                value_key="regime",
            )
        if self.trading_mode.filter_settings.plot_adx_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="ADX filter",
                signals=_filters.adxbearish_rates,
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
                signals=_filters.is_ema_uptrendes,
                values=slightly_below_lows,
                times=candle_times,
                value_key="is_ema_uptrend",
            )
        if self.trading_mode.filter_settings.plot_sma_filter:
            await matrix_plots.plot_conditional(
                ctx=ctx,
                title="is_sma_uptrend",
                signals=_filters.is_sma_uptrendes,
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
            additional_values_by_key["rma"] = rma
            additional_values_by_key["recentAtr"] = recentAtr
            additional_values_by_key["historicalAtr"] = historicalAtr
            additional_values_by_key["yhat2"] = yhat2

            additional_values_by_key["yt"] = y_train_series

            await plotting.plot(
                ctx,
                title="recentAtr",
                cache_value="recentAtr",
                chart="sub-chart",
            )
            await plotting.plot(
                ctx,
                title="yhat2",
                cache_value="yhat2",
                chart="main-chart",
            )
            await plotting.plot(
                ctx,
                title="historicalAtr",
                cache_value="historicalAtr",
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
        yhat1, yhat2 = basic_utilities.cut_data_to_same_len((yhat1, yhat2))

        kernel_estimate: numpy.array = yhat1
        # Kernel Rates of Change
        # shift and cut data for numpy
        yhat1_cutted_1, yhat1_shifted_1 = utils.shift_data(yhat1, 1)
        yhat1_cutted_2, yhat1_shifted_2 = utils.shift_data(yhat1, 2)
        was_bearish_rates: numpy.array = yhat1_shifted_2 > yhat1_cutted_2
        was_bullish_rates: numpy.array = yhat1_shifted_2 < yhat1_cutted_2

        is_bearish_rates: numpy.array = yhat1_shifted_1 > yhat1_cutted_1
        is_bullish_rates: numpy.array = yhat1_shifted_1 < yhat1_cutted_1

        is_bearish_rates, was_bullish_rates = basic_utilities.cut_data_to_same_len(
            (is_bearish_rates, was_bullish_rates)
        )
        is_bearish_changes: numpy.array = numpy.logical_and(
            is_bearish_rates, was_bullish_rates
        )
        is_bullish_rates, was_bearish_rates = basic_utilities.cut_data_to_same_len(
            (is_bullish_rates, was_bearish_rates)
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

    def get_max_bars_back_index(self, cutted_data_length) -> int:
        if self.ctx.exchange_manager.is_backtesting:
            return self.trading_mode.general_settings.max_bars_back
        if cutted_data_length >= self.trading_mode.general_settings.max_bars_back:
            return cutted_data_length - self.trading_mode.general_settings.max_bars_back
        else:
            self.logger.warning(
                "Not enough historical bars for the current max_bars_back. "
                "Either increase the amount of initialized candles "
                "or reduce the max_bars_back setting. Classification will run "
                f"on {cutted_data_length} bars"
            )
            return 0  # start on bar 0

    async def _trade_live_candle(self, start_short_trades, start_long_trades):
        if start_short_trades[-1]:
            await self.execute_short_trade()
        if start_long_trades[-1]:
            await self.execute_long_trade()

    def _cache_backtesting_signals(
        self, ctx, candle_times, start_short_trades, start_long_trades
    ) -> bool:
        # cache signals for backtesting
        (
            candle_times,
            start_short_trades,
            start_long_trades,
        ) = basic_utilities.cut_data_to_same_len(
            (candle_times, start_short_trades, start_long_trades)
        )
        candle_times_to_whitelist: list = []
        self.start_short_trades_cache = {}
        self.start_long_trades_cache = {}
        trades_count = 0
        for index, candle_time in enumerate(candle_times):

            self.start_short_trades_cache[candle_time] = start_short_trades[index]
            self.start_long_trades_cache[candle_time] = start_long_trades[index]
            if start_long_trades[index] or start_short_trades[index]:
                if start_long_trades[index]:
                    trades_count += 1
                if start_short_trades[index]:
                    trades_count += 1
                open_time = candle_time - (
                    enums.TimeFramesMinutes[enums.TimeFrames(self.ctx.time_frame)] * 60
                )
                # candle_times_to_whitelist.append(candle_time)
                candle_times_to_whitelist.append(open_time)
        s_time = basic_utilities.start_measure_time(
            " strategy maker - building backtesting cache"
        )
        basic_utilities.end_measure_time(
            s_time,
            f" strategy maker - building strategy for "
            f"{self.ctx.time_frame} {trades_count} trades",
        )
        backtesting_settings.register_backtesting_timestamp_whitelist(
            ctx, candle_times_to_whitelist
        )

    async def _trade_cached_backtesting_candles_if_available(self, ctx) -> bool:
        if ctx.exchange_manager.is_backtesting:
            if self.start_long_trades_cache:
                try:
                    if self.start_short_trades_cache[ctx.trigger_cache_timestamp]:
                        await self.execute_short_trade()
                    elif self.start_long_trades_cache[ctx.trigger_cache_timestamp]:
                        await self.execute_long_trade()
                    return True
                except KeyError as error:
                    print(f"Failed to get cached strategy signal - error: {error}")
                    return True
        return False

    async def init_order_settings(self, ctx):
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
        if activate_managed_order:
            self.managend_orders_short_settings = (
                await activate_managed_order.activate_managed_orders(
                    self,
                    parent_input_name=short_settings_name,
                    name_prefix="short",
                )
            )

    async def execute_short_trade(self):
        if managed_orders:
            await managed_orders.managed_order(
                self,
                trading_side="short",
                orders_settings=self.managend_orders_short_settings,
            )
        else:
            await market(self.ctx, side="sell", amount="100%a")

    async def execute_long_trade(self):
        if managed_orders:
            await managed_orders.managed_order(
                self,
                trading_side="long",
                orders_settings=self.managend_orders_long_settings,
            )
        else:
            await market(self.ctx, side="buy", amount="100%a")
