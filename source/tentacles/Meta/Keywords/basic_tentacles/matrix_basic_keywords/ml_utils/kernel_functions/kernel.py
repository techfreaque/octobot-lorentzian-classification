import math
import typing
import numpy.typing as npt
import numpy as numpy

import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.tools.utilities as basic_utilities
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.ml_utils.utils as utils


def rationalQuadratic(
    data_source: npt.NDArray[numpy.float64],
    look_back: int,
    relative_weight: float,
    start_at_Bar: int,
) -> npt.NDArray[numpy.float64]:
    yhat: typing.List[float] = []
    start_at_Bar += 1  # because this is 1 on tv: _size = array.size(array.from(_src))
    for index in range(start_at_Bar, len(data_source)):
        _currentWeight: float = 0
        _cumulativeWeight: float = 0
        for bars_back_index in range(0, start_at_Bar):
            y = data_source[index - bars_back_index]
            w = pow(
                1
                + (
                    pow(bars_back_index, 2)
                    / ((pow(look_back, 2) * 2 * relative_weight))
                ),
                -relative_weight,
            )
            _currentWeight += y * w
            _cumulativeWeight += w
        yhat.append(_currentWeight / _cumulativeWeight)
    return numpy.array(yhat)


def gaussian(
    data_source: npt.NDArray[numpy.float64], look_back: int, start_at_Bar: int
) -> npt.NDArray[numpy.float64]:
    start_at_Bar += 1
    yhat: typing.List[float] = []
    for index in range(start_at_Bar, len(data_source)):
        _currentWeight: float = 0
        _cumulativeWeight: float = 0
        for bars_back_index in range(0, start_at_Bar):
            y = data_source[index - bars_back_index]
            w = math.exp(-pow(bars_back_index, 2) / (2 * pow(look_back, 2)))
            _currentWeight += y * w
            _cumulativeWeight += w
        yhat.append(_currentWeight / _cumulativeWeight)
    return numpy.array(yhat)


def get_kernel_data(
    kernel_settings, user_selected_candles: npt.NDArray[numpy.float64], data_length: int
) -> tuple:
    # TODO colors
    # c_green = color.new(#009988, 20)
    # c_red = color.new(#CC3311, 20)
    # transparent = color.new(#000000, 100)

    yhat1: npt.NDArray[numpy.float64] = rationalQuadratic(
        user_selected_candles,
        kernel_settings.lookback_window,
        kernel_settings.relative_weighting,
        kernel_settings.regression_level,
    )
    yhat2: npt.NDArray[numpy.float64] = gaussian(
        user_selected_candles,
        kernel_settings.lookback_window - kernel_settings.lag,
        kernel_settings.regression_level,
    )
    yhat1, yhat2 = basic_utilities.cut_data_to_same_len((yhat1, yhat2))

    kernel_estimate: npt.NDArray[numpy.float64] = yhat1
    # Kernel Rates of Change
    # shift and cut data for numpy
    yhat1_cutted_1, yhat1_shifted_1 = basic_utilities.shift_data(yhat1, 1)
    yhat1_cutted_2, yhat1_shifted_2 = basic_utilities.shift_data(yhat1, 2)
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
        if kernel_settings.use_kernel_smoothing
        else is_bullish_changes
    )
    alerts_bearish: npt.NDArray[numpy.bool_] = (
        is_bearish_cross_alerts
        if kernel_settings.use_kernel_smoothing
        else is_bearish_changes
    )
    # Bullish and Bearish Filters based on Kernel
    is_bullishs: npt.NDArray[numpy.bool_] = (
        (
            is_bullish_smooths
            if kernel_settings.use_kernel_smoothing
            else is_bullish_rates
        )
        if kernel_settings.use_kernel_filter
        else [True] * data_length
    )
    is_bearishs: npt.NDArray[numpy.bool_] = (
        (
            is_bearish_smooths
            if kernel_settings.use_kernel_smoothing
            else is_bearish_rates
        )
        if kernel_settings.use_kernel_filter
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
