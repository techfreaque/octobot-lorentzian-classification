import math
import typing
import numpy
import numpy.typing as npt

import tentacles.Trading.Mode.lorentzian_classification.utils as utils
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.matrix_basic_keywords.tools.utilities as basic_utilities


def get_lorentzian_distance(
    feature_count: int,
    candle_index: int,
    candles_back_index: int,
    feature_arrays: utils.FeatureArrays,
) -> float:
    if feature_count == 5:
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
    elif feature_count == 4:
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
    elif feature_count == 3:
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
    elif feature_count == 2:
        return math.log(
            1
            + abs(
                feature_arrays.f1[candle_index] - feature_arrays.f1[candles_back_index]
            )
        ) + math.log(
            1
            + abs(
                feature_arrays.f2[candle_index] - feature_arrays.f2[candles_back_index]
            )
        )


def get_y_train_series(user_selected_candles):
    cutted_candles, shifted_candles = basic_utilities.shift_data(
        user_selected_candles, 4
    )
    return numpy.where(
        shifted_candles < cutted_candles,
        utils.SignalDirection.short,
        numpy.where(
            shifted_candles > cutted_candles,
            utils.SignalDirection.long,
            utils.SignalDirection.neutral,
        ),
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
) -> typing.Tuple[int, int]:
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
