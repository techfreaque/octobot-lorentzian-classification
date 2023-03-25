from __future__ import annotations
import typing
import numpy.typing as npt

import numpy
import tulipy
import tentacles.Trading.Mode.lorentzian_classification.ml_extensions_2.ml_extensions as ml_extensions
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.matrix_basic_keywords.tools.utilities as basic_utils


def series_from(
    feature_string: str,
    _close: npt.NDArray[numpy.float64],
    _high: npt.NDArray[numpy.float64],
    _low: npt.NDArray[numpy.float64],
    _hlc3: npt.NDArray[numpy.float64],
    f_paramA: int,
    f_paramB: int,
) -> npt.NDArray[numpy.float64]:
    if feature_string == "RSI":
        return ml_extensions.n_rsi(_close, f_paramA, f_paramB)
    if feature_string == "WT":
        return ml_extensions.n_wt(_hlc3, f_paramA, f_paramB)
    if feature_string == "CCI":
        return ml_extensions.n_cci(_high, _low, _close, f_paramA, f_paramB)
    if feature_string == "ADX":
        return ml_extensions.n_adx(_high, _low, _close, f_paramA)


class ClassificationSettings:
    def __init__(
        self,
        neighbors_count: int,
        max_bars_back: int,
        color_compression: int,
        live_history_size: int,
        use_remote_fractals: bool,
        down_sampler: typing.Callable[[int, int], bool],
        only_train_on_every_x_bars: typing.Optional[int] = None,
    ):
        self.neighbors_count: int = neighbors_count
        self.last_distance_neighbors_count: int = round(neighbors_count * 3 / 4)
        self.max_bars_back: int = max_bars_back
        self.color_compression: int = color_compression
        self.live_history_size: int = live_history_size
        self.use_remote_fractals: bool = use_remote_fractals
        self.only_train_on_every_x_bars: typing.Optional[
            int
        ] = only_train_on_every_x_bars
        self.down_sampler: typing.Callable[[int, int], bool] = down_sampler


class SignalDirection:
    long: int = 1
    short: int = -1
    neutral: int = 0


class FeatureArrays:
    def __init__(
        self,
        f1: npt.NDArray[numpy.float64],
        f2: npt.NDArray[numpy.float64],
        f3: npt.NDArray[numpy.float64],
        f4: npt.NDArray[numpy.float64],
        f5: npt.NDArray[numpy.float64],
    ):
        self.f1: npt.NDArray[numpy.float64] = f1
        self.f2: npt.NDArray[numpy.float64] = f2
        self.f3: npt.NDArray[numpy.float64] = f3
        self.f4: npt.NDArray[numpy.float64] = f4
        self.f5: npt.NDArray[numpy.float64] = f5


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


class SymbolSettings:
    def __init__(
        self,
        symbol: str,
        this_target_symbol: typing.Optional[str],
        trade_on_this_pair: bool,
        use_custom_pair: bool,
    ):
        self.this_target_symbol: typing.Optional[str] = this_target_symbol
        self.trade_on_this_pair: bool = trade_on_this_pair
        self.use_custom_pair: bool = use_custom_pair
        self.symbol: str = symbol

    def get_data_source_symbol_name(self) -> str:
        if self.use_custom_pair:
            return self.this_target_symbol
        else:
            return self.symbol


class DataSourceSettings:
    def __init__(
        self,
        available_symbols: typing.List[str],
        symbol_settings_by_symbols: typing.Dict[str, SymbolSettings],
        source: str,
    ):
        self.available_symbols: typing.List[str] = available_symbols
        self.symbol_settings_by_symbols: typing.Dict[
            str, SymbolSettings
        ] = symbol_settings_by_symbols
        self.source: str = source


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


class LorentzianOrderSettings:
    def __init__(
        self,
        long_order_volume: typing.Optional[float],
        short_order_volume: typing.Optional[float],
        enable_short_orders: bool,
        enable_long_orders: bool,
        exit_type: str,
        leverage: typing.Optional[int] = None,
    ):
        self.long_order_volume: typing.Optional[float] = long_order_volume
        self.short_order_volume: typing.Optional[float] = short_order_volume
        self.enable_short_orders: bool = enable_short_orders
        self.enable_long_orders: bool = enable_long_orders
        self.leverage: typing.Optional[int] = leverage
        self.exit_type: str = exit_type


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
    def __init__(
        self,
        volatility: npt.NDArray[numpy.bool_],
        regime: npt.NDArray[numpy.bool_],
        adx: npt.NDArray[numpy.bool_],
        is_ema_uptrend: npt.NDArray[numpy.bool_],
        is_ema_downtrend: npt.NDArray[numpy.bool_],
        is_sma_uptrend: npt.NDArray[numpy.bool_],
        is_sma_downtrend: npt.NDArray[numpy.bool_],
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


def get_is_crossing_data(
    data1: npt.NDArray[numpy.float64], data2: npt.NDArray[numpy.float64]
) -> typing.Tuple[npt.NDArray[numpy.bool_], npt.NDArray[numpy.bool_]]:
    data1_cutted_1, data1_shifted_1 = basic_utils.shift_data(data1, 1)
    data2_cutted_1, data2_shifted_1 = basic_utils.shift_data(data2, 1)
    crossing_ups = numpy.logical_and(
        data1_shifted_1 < data2_shifted_1, data1_cutted_1 > data2_cutted_1
    )
    crossing_downs = numpy.logical_and(
        data1_shifted_1 > data2_shifted_1, data1_cutted_1 < data2_cutted_1
    )
    return crossing_ups, crossing_downs


def calculate_rma(
    src: npt.NDArray[numpy.float64], length
) -> npt.NDArray[numpy.float64]:
    alpha = 1 / length
    sma = tulipy.sma(src, length)[50:]  # cut first data as its not very accurate
    src, sma = basic_utils.cut_data_to_same_len((src, sma))
    rma: typing.List[float] = [sma[0]]
    for index in range(1, len(src)):
        rma.append((src[index] * alpha) + ((1 - alpha) * rma[-1]))
    return numpy.array(rma)


class ExitTypes:
    FOUR_BARS = "exit after 4 bars"
    # DYNAMIC = "dynamic exit"
    SWITCH_SIDES = "switch sides on exits / entries"
