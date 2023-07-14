import math
import typing
import numpy
import numpy.typing as npt
import octobot_commons.constants as commons_constants
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.ml_utils.utils as utils
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.tools.utilities as basic_utilities


def classify_current_candle(
    order_settings: utils.LorentzianOrderSettings,
    classification_settings: utils.ClassificationSettings,
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
    start_long_trades: list,
    start_short_trades: list,
    exit_short_trades: list,
    exit_long_trades: list,
    is_buy_signals: list,
    is_sell_signals: list,
) -> typing.Tuple[int, int]:
    historical_predictions.append(
        get_classification_predictions(
            current_candle_index,
            classification_settings,
            feature_arrays,
            y_train_series,
        )
    )
    (
        bars_since_green_entry,
        bars_since_red_entry,
    ) = set_signals_from_prediction(
        prediction=historical_predictions[-1],
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
        exit_type=order_settings.exit_type,
        classification_settings=classification_settings,
    )
    return bars_since_green_entry, bars_since_red_entry


def get_classification_predictions(
    current_candle_index: int, classification_settings, feature_arrays, y_train_series
) -> int:
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
    predictions: list = []
    distances: list = []
    for candles_back in _get_candles_back_start_end_index(
        classification_settings, current_candle_index
    ):
        if classification_settings.down_sampler(
            candles_back,
            classification_settings.only_train_on_every_x_bars,
        ):
            lorentzian_distance: float = get_lorentzian_distance(
                candle_index=current_candle_index,
                candles_back_index=candles_back,
                feature_arrays=feature_arrays,
            )
            if lorentzian_distance >= last_distance:
                last_distance = lorentzian_distance
                predictions.append(y_train_series[candles_back])
                distances.append(lorentzian_distance)
                if len(predictions) > classification_settings.neighbors_count:
                    last_distance = distances[
                        classification_settings.last_distance_neighbors_count
                    ]
                    del distances[0]
                    del predictions[0]
    return sum(predictions)


def _get_candles_back_start_end_index(
    classification_settings: utils.ClassificationSettings, current_candle_index: int
):
    size_loop: int = min(
        classification_settings.max_bars_back - 1,
        current_candle_index,
    )
    if classification_settings.use_remote_fractals:
        # classify starting from:
        #   live mode: first bar
        #   backtesting:  current bar - live_history_size
        start_index: int = max(
            current_candle_index - classification_settings.live_history_size,
            0,
        )
        end_index: int = start_index + size_loop
    else:
        start_index: int = current_candle_index - size_loop
        end_index: int = current_candle_index
    return range(start_index, end_index)


def get_config_candles(config):
    candles = config.get(commons_constants.CONFIG_TENTACLES_REQUIRED_CANDLES_COUNT, 0)
    return candles if candles > 200 else 200


def get_lorentzian_distance(
    candle_index: int,
    candles_back_index: int,
    feature_arrays: utils.FeatureArrays,
) -> float:
    distance: float = 0
    for feature_array in feature_arrays.feature_arrays:
        distance += math.log(
            1 + abs(feature_array[candle_index] - feature_array[candles_back_index])
        )
    return distance


def get_y_train_series(
    closes: npt.NDArray[numpy.float64],
    lows: npt.NDArray[numpy.float64],
    highs: npt.NDArray[numpy.float64],
    training_data_settings: utils.YTrainSettings,
    raise_missing_data: bool = False,
):
    if training_data_settings.training_data_type == utils.YTrainTypes.IS_WINNING_TRADE:
        y_train_series = []
        data_length = len(closes)
        for candle_index, candle in enumerate(closes):
            long_win_price = (
                candle / 100 * (100 + training_data_settings.percent_for_a_win)
            )
            long_lose_price = (
                candle / 100 * (100 - training_data_settings.percent_for_a_loss)
            )
            short_win_price = (
                candle / 100 * (100 - training_data_settings.percent_for_a_win)
            )
            short_lose_price = (
                candle / 100 * (100 + training_data_settings.percent_for_a_loss)
            )
            is_short = None
            is_long = None
            signal = utils.SignalDirection.neutral
            for inner_candle_index in range(1, data_length - candle_index):
                # # neutral
                if is_short is False and is_long is False:
                    signal = utils.SignalDirection.neutral
                    break
                comparing_high_candle = highs[candle_index + inner_candle_index]
                comparing_low_candle = lows[candle_index + inner_candle_index]
                if is_long is None:
                    # long
                    if comparing_high_candle >= long_win_price:
                        signal = utils.SignalDirection.long
                        break
                    if comparing_low_candle <= long_lose_price:
                        is_long = False

                if is_short is None:
                    # short
                    if comparing_low_candle <= short_win_price:
                        signal = utils.SignalDirection.short
                        break
                    if comparing_high_candle >= short_lose_price:
                        is_short = False
            y_train_series.append(signal)
    elif (
        training_data_settings.training_data_type
        == utils.YTrainTypes.IS_IN_PROFIT_AFTER_4_BARS
    ):
        cutted_closes, _ = basic_utilities.shift_data(closes, 4)
        _, shifted_lows = basic_utilities.shift_data(lows, 4)
        _, shifted_highs = basic_utilities.shift_data(highs, 4)
        y_train_series = numpy.where(
            shifted_highs < cutted_closes,
            utils.SignalDirection.short,
            numpy.where(
                shifted_lows > cutted_closes,
                utils.SignalDirection.long,
                utils.SignalDirection.neutral,
            ),
        )
    elif (
        training_data_settings.training_data_type
        == utils.YTrainTypes.IS_IN_PROFIT_AFTER_4_BARS_CLOSES
    ):
        cutted_closes, shifted_closes = basic_utilities.shift_data(closes, 4)
        y_train_series = numpy.where(
            shifted_closes < cutted_closes,
            utils.SignalDirection.short,
            numpy.where(
                shifted_closes > cutted_closes,
                utils.SignalDirection.long,
                utils.SignalDirection.neutral,
            ),
        )
    if raise_missing_data:
        verify_training_prediction_labels_completeness(y_train_series)
    return y_train_series


def verify_training_prediction_labels_completeness(y_train_series):
    if (
        utils.SignalDirection.short not in y_train_series
        or utils.SignalDirection.short not in y_train_series
        or utils.SignalDirection.short not in y_train_series
    ):
        raise RuntimeError(
            "Not enough historical data available, increase the available history "
            "or change your training prediction labels settings"
        )


def set_signals_from_prediction(
    prediction: int,
    _filters: utils.Filter,
    candle_index: int,
    previous_signals: list,
    start_long_trades: list,
    start_short_trades: list,
    is_bullishs: npt.NDArray[numpy.bool_],
    is_bearishs: npt.NDArray[numpy.bool_],
    # alerts_bullish: npt.NDArray[numpy.bool_],
    # alerts_bearish: npt.NDArray[numpy.bool_],
    # is_bearish_changes: npt.NDArray[numpy.bool_],
    # is_bullish_changes: npt.NDArray[numpy.bool_],
    exit_short_trades: list,
    exit_long_trades: list,
    bars_since_green_entry: int,
    bars_since_red_entry: int,
    is_buy_signals: list,
    is_sell_signals: list,
    exit_type: str,
    classification_settings: utils.ClassificationSettings,
) -> typing.Tuple[int, int]:
    # ============================
    # ==== Prediction Filters ====
    # ============================

    # Filtered Signal: The model's prediction of future price movement direction with user-defined filters applied
    signal = (
        utils.SignalDirection.long
        if prediction > classification_settings.required_neighbors
        and _filters.filter_all[candle_index]
        else (
            utils.SignalDirection.short
            if prediction < -classification_settings.required_neighbors
            and _filters.filter_all[candle_index]
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
        signal == utils.SignalDirection.short and _filters.is_downtrend[candle_index]
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

    if exit_type == utils.ExitTypes.FOUR_BARS:
        # Bar-Count Filters: Represents strict filters based on a pre-defined holding period of 4 bars
        bars_since_green_entry, bars_since_red_entry = _handle_four_bar_exit(
            bars_since_green_entry,
            bars_since_red_entry,
            exit_short_trades,
            exit_long_trades,
            start_long_trade,
            start_short_trade,
        )
    # elif self.trading_mode.order_settings.exit_type == utils.ExitTypes.DYNAMIC:
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
    bars_since_green_entry: int,
    bars_since_red_entry: int,
    exit_short_trades: list,
    exit_long_trades: list,
    start_long_trade: bool,
    start_short_trade: bool,
) -> typing.Tuple[int, int]:
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
