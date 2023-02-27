import typing
import numpy.typing as npt

import numpy
import tulipy
import tentacles.Trading.Mode.lorentzian_classification.ml_extensions_2.ml_extensions as ml_extensions
import tentacles.Meta.Keywords.matrix_library.matrix_basic_keywords.tools.utilities as basic_utils


def series_from(feature_string, _close, _high, _low, _hlc3, f_paramA, f_paramB):
    if feature_string == "RSI":
        return ml_extensions.n_rsi(_close, f_paramA, f_paramB)
    if feature_string == "WT":
        return ml_extensions.n_wt(_hlc3, f_paramA, f_paramB)
    if feature_string == "CCI":
        return ml_extensions.n_cci(_high, _low, _close, f_paramA, f_paramB)
    if feature_string == "ADX":
        return ml_extensions.n_adx(_high, _low, _close, f_paramA)


class Settings:
    def __init__(
        self,
        source: float,
        neighbors_count: int,
        max_bars_back: int,
        color_compression: int,
        # use_dynamic_exits: bool,
        exit_type: str,
    ):
        self.source: float = source
        self.neighbors_count: int = neighbors_count
        self.max_bars_back: int = max_bars_back
        self.color_compression: int = color_compression
        # self.use_dynamic_exits: bool = use_dynamic_exits
        self.exit_type: str = exit_type


class SignalDirection:
    long = 1
    short = -1
    neutral = 0


class FeatureArrays:
    def __init__(
        self,
        f1: typing.List[float],
        f2: typing.List[float],
        f3: typing.List[float],
        f4: typing.List[float],
        f5: typing.List[float],
    ):
        self.f1: typing.List[float] = f1
        self.f2: typing.List[float] = f2
        self.f3: typing.List[float] = f3
        self.f4: typing.List[float] = f4
        self.f5: typing.List[float] = f5


class FeatureSeries:
    def __init__(self, f1: float, f2: float, f3: float, f4: float, f5: float):
        self.f1: float = f1
        self.f2: float = f2
        self.f3: float = f3
        self.f4: float = f4
        self.f5: float = f5


class MLModel:
    def __init__(
        self,
        first_bar_index: int,
        training_labels: typing.List[int],
        loop_size: int,
        last_distance: float,
        distances_array: typing.List[float],
        predictions_array: typing.List[int],
        prediction: int,
    ):
        self.first_bar_index: int = first_bar_index
        self.training_labels: typing.List[int] = training_labels
        self.loop_size: int = loop_size
        self.last_distance: float = last_distance
        self.distances_array: typing.List[float] = distances_array
        self.predictions_array: typing.List[int] = predictions_array
        self.prediction: int = prediction


class DisplaySettings:
    def __init__(
        self,
        show_bar_colors: bool,
        show_bar_predictions: bool,
        use_atr_offset: bool,
        bar_predictions_offset: float,
        enable_additional_plots: bool,
    ):
        self.show_bar_colors: bool = show_bar_colors
        self.show_bar_predictions: bool = show_bar_predictions
        self.use_atr_offset: bool = use_atr_offset
        self.enable_additional_plots: bool = enable_additional_plots
        self.bar_predictions_offset: float = bar_predictions_offset


class KernelSettings:
    def __init__(
        self,
        use_kernel_filter: bool,
        show_kernel_estimate: bool,
        use_kernel_smoothing: bool,
        lookback_window: int,
        relative_weighting: float,
        regression_level: int,
        lag: int,
    ):
        self.use_kernel_filter: bool = use_kernel_filter
        self.show_kernel_estimate: bool = show_kernel_estimate
        self.use_kernel_smoothing: bool = use_kernel_smoothing
        self.lookback_window: int = lookback_window
        self.relative_weighting: float = relative_weighting
        self.regression_level: int = regression_level
        self.lag: int = lag


class FilterSettings:
    def __init__(
        self,
        use_volatility_filter: bool,
        plot_volatility_filter: bool,
        use_regime_filter: bool,
        regime_threshold: float,
        plot_regime_filter: bool,
        use_adx_filter: bool,
        adx_threshold: int,
        plot_adx_filter: bool,
        use_ema_filter: bool,
        ema_period: int,
        plot_ema_filter: bool,
        use_sma_filter: bool,
        sma_period: int,
        plot_sma_filter: bool,
    ):
        self.use_volatility_filter: bool = use_volatility_filter
        self.use_regime_filter: bool = use_regime_filter
        self.use_adx_filter: bool = use_adx_filter
        self.regime_threshold: float = regime_threshold
        self.adx_threshold: int = adx_threshold
        self.use_ema_filter: int = use_ema_filter
        self.ema_period: int = ema_period
        self.use_sma_filter: int = use_sma_filter
        self.sma_period: int = sma_period
        self.plot_volatility_filter: int = plot_volatility_filter
        self.plot_regime_filter: int = plot_regime_filter
        self.plot_adx_filter: int = plot_adx_filter
        self.plot_ema_filter: int = plot_ema_filter
        self.plot_sma_filter: int = plot_sma_filter


class FeatureEngineeringSettings:
    def __init__(
        self,
        feature_count: int,
        plot_features: bool,
        f1_string: str,
        f1_paramA: int,
        f1_paramB: int,
        f2_string: str,
        f2_paramA: int,
        f2_paramB: int,
        f3_string: str,
        f3_paramA: int,
        f3_paramB: int,
        f4_string: str,
        f4_paramA: int,
        f4_paramB: int,
        f5_string: str,
        f5_paramA: int,
        f5_paramB: int,
    ):
        self.feature_count: int = feature_count
        self.plot_features: bool = plot_features
        self.f1_string: str = f1_string
        self.f1_paramA: int = f1_paramA
        self.f1_paramB: int = f1_paramB
        self.f2_string: str = f2_string
        self.f2_paramA: int = f2_paramA
        self.f2_paramB: int = f2_paramB
        self.f3_string: str = f3_string
        self.f3_paramA: int = f3_paramA
        self.f3_paramB: int = f3_paramB
        self.f4_string: str = f4_string
        self.f4_paramA: int = f4_paramA
        self.f4_paramB: int = f4_paramB
        self.f5_string: str = f5_string
        self.f5_paramA: int = f5_paramA
        self.f5_paramB: int = f5_paramB


class Filter:
    # numpy bool arays
    def __init__(
        self,
        volatility,
        regime,
        adx,
        is_ema_uptrend,
        is_ema_downtrend,
        is_sma_uptrend,
        is_sma_downtrend,
    ):
        (
            volatility,
            regime,
            adx,
            is_ema_uptrend,
            is_sma_uptrend,
            is_ema_downtrend,
            is_sma_downtrend,
        ) = basic_utils.cut_data_to_same_len(
            (
                volatility,
                regime,
                adx,
                is_ema_uptrend,
                is_sma_uptrend,
                is_ema_downtrend,
                is_sma_downtrend,
            )
        )
        # User Defined Filters: Used for adjusting the frequency of the ML Model's predictions
        self.filter_all = numpy.logical_and(
            volatility,
            regime,
            adx,
        )
        # Fractal Filters: Derived from relative appearances of signals in a given time series fractal/segment with a default length of 4 bars
        self.is_uptrend = numpy.logical_and(is_ema_uptrend, is_sma_uptrend)
        self.is_downtrend = numpy.logical_and(is_ema_downtrend, is_sma_downtrend)

        self.volatility = volatility
        self.regime = regime
        self.adx = adx
        self.is_ema_uptrend = is_ema_uptrend
        self.is_sma_uptrend = is_sma_uptrend
        self.is_ema_downtrend = is_ema_downtrend
        self.is_sma_downtrend = is_sma_downtrend


def shift_data(data_source: list or numpy.array, shift_by: int = 1):
    cutted_data = data_source[shift_by:]
    shifted_data = data_source[:-shift_by]
    return cutted_data, shifted_data


def get_is_crossing_data(
    data1: numpy.array, data2: numpy.array
) -> typing.Tuple[list or numpy.array]:
    data1_cutted_1, data1_shifted_1 = shift_data(data1, 1)
    data2_cutted_1, data2_shifted_1 = shift_data(data2, 1)
    crossing_ups = numpy.logical_and(
        data1_shifted_1 < data2_shifted_1, data1_cutted_1 > data2_cutted_1
    )
    crossing_downs = numpy.logical_and(
        data1_shifted_1 > data2_shifted_1, data1_cutted_1 < data2_cutted_1
    )
    return crossing_ups, crossing_downs


def calculate_rma(src, length):
    # TODO not the same as on here: https://www.tradingview.com/pine-script-reference/v5/#fun_ta%7Bdot%7Drma
    alpha = 1 / length
    sma = tulipy.sma(src, length)[50:]  # cut first data as its not very accurate
    src, sma = basic_utils.cut_data_to_same_len((src, sma))
    rma: typing.List[float] = [0]
    for index in range(0, len(src)):
        rma.append(
            sma[index] if rma[-1] else (src[index] * alpha) + ((1 - alpha) * rma[-1])
        )
    return numpy.array(rma)


class ExitTypes:
    FOUR_BARS = "exit after 4 bars"
    # DYNAMIC = "dynamic exit"
    SWITCH_SIDES = "switch sides on exits / entries"
