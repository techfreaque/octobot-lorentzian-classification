import typing

import numpy
import tentacles.Evaluator.TA.lorentzian_classification.ml_extensions_2.ml_extensions as ml_extensions


def series_from(feature_string, _close, _high, _low, _hlc3, f_paramA, f_paramB):
    if feature_string == "RSI":
        return ml_extensions.n_rsi(_close, f_paramA, f_paramB)
    if feature_string == "WT":
        return ml_extensions.n_wt(_hlc3, f_paramA, f_paramB)
    if feature_string == "CCI":
        return ml_extensions.n_cci(_close, f_paramA, f_paramB)
    if feature_string == "ADX":
        return ml_extensions.n_adx(_high, _low, _close, f_paramA)


class Settings:
    def __init__(
        self,
        source: float,
        neighbors_count: int,
        max_bars_back: int,
        color_compression: int,
        show_default_exits: bool,
        use_dynamic_exits: bool,
    ):
        self.source: float = source
        self.neighbors_count: int = neighbors_count
        self.max_bars_back: int = max_bars_back
        self.color_compression: int = color_compression
        self.show_default_exits: bool = show_default_exits
        self.use_dynamic_exits: bool = use_dynamic_exits


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
    ):
        self.show_bar_colors: bool = show_bar_colors
        self.show_bar_predictions: bool = show_bar_predictions
        self.use_atr_offset: bool = use_atr_offset
        self.bar_predictions_offset: float = bar_predictions_offset


class KernelSettings:
    def __init__(
        self,
        use_kernel_filter: bool,
        show_kernel_estimate: bool,
        use_kernel_smoothing: bool,
        h: int,
        r: float,
        x: int,
        lag: int,
    ):
        self.use_kernel_filter: bool = use_kernel_filter
        self.show_kernel_estimate: bool = show_kernel_estimate
        self.use_kernel_smoothing: bool = use_kernel_smoothing
        self.h: int = h
        self.r: float = r
        self.x: int = x
        self.lag: int = lag


class FilterSettings:
    def __init__(
        self,
        use_volatility_filter: bool,
        use_regime_filter: bool,
        use_adx_filter: bool,
        regime_threshold: float,
        adx_threshold: int,
        use_ema_filter: bool,
        ema_period: int,
        use_sma_filter: bool,
        sma_period: int,
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


class FeatureEngineeringSettings:
    def __init__(
        self,
        feature_count: int,
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
    def __init__(self, volatility: bool, regime: bool, adx: bool):
        self.volatility: bool = volatility
        self.regime: bool = regime
        self.adx: bool = adx


def shift_data(data_source: list or numpy.array, shift_by: int = 1):
    cutted_data = data_source[shift_by:]
    shifted_data = data_source[: -shift_by - 1]
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