import math
import typing
import numpy
import tulipy
import numpy.typing as npt
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.ml_utils.utils as utils
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.tools.utilities as basic_utils


def rescale(
    src: npt.NDArray[numpy.float64],
    oldMin: float,
    oldMax: float,
    newMin: float,
    newMax: float,
):
    return newMin + (newMax - newMin) * (src - oldMin) / max(oldMax - oldMin, 10e-10)


def normalize(
    src: npt.NDArray[numpy.float64],
    #   _min: float, _max: float
):
    # normalizes to values from 0 -1
    min_val = numpy.min(src)
    return (src - min_val) / (numpy.max(src) - min_val)

    # return _min + (_max - _min) * (src - numpy.min(src)) / numpy.max(src)


def n_rsi(_close: npt.NDArray[numpy.float64], f_paramA, f_paramB):
    return rescale(tulipy.ema(tulipy.rsi(_close, f_paramA), f_paramB), 0, 100, 0, 1)


def n_wt(_hlc3: npt.NDArray[numpy.float64], f_paramA, f_paramB):
    ema1 = tulipy.ema(_hlc3, f_paramA)
    ema2 = tulipy.ema(abs(_hlc3 - ema1), f_paramA)
    ci = (_hlc3[1:] - ema1[1:]) / (0.015 * ema2[1:])
    wt1 = tulipy.ema(ci, f_paramB)  # tci
    wt2 = tulipy.sma(wt1, 4)
    wt1, wt2 = basic_utils.cut_data_to_same_len((wt1, wt2))
    return normalize(wt1 - wt2)  # , 0, 1)


def n_cci(
    highs: npt.NDArray[numpy.float64],
    lows: npt.NDArray[numpy.float64],
    closes: npt.NDArray[numpy.float64],
    f_paramA,
    f_paramB,
):
    # use closes, closes, closes to get same cci as on tradingview
    return normalize(
        tulipy.ema(tulipy.cci(closes, closes, closes, f_paramA), f_paramB)
    )  # , 0, 1)


def n_adx(
    highSrc: npt.NDArray[numpy.float64],
    lowSrc: npt.NDArray[numpy.float64],
    closeSrc: npt.NDArray[numpy.float64],
    f_paramA: int,
):
    length: int = f_paramA
    data_length: int = len(highSrc)
    trSmooth: typing.List[float] = [0]
    smoothnegMovement: typing.List[float] = [0]
    smoothDirectionalMovementPlus: typing.List[float] = [0]
    dx: typing.List[float] = []

    for index in range(1, data_length):
        tr = max(
            max(
                highSrc[index] - lowSrc[index],
                abs(highSrc[index] - closeSrc[index - 1]),
            ),
            abs(lowSrc[index] - closeSrc[index - 1]),
        )
        directionalMovementPlus = (
            max(highSrc[index] - highSrc[index - 1], 0)
            if highSrc[index] - highSrc[index - 1] > lowSrc[index - 1] - lowSrc[index]
            else 0
        )
        negMovement = (
            max(lowSrc[index - 1] - lowSrc[index], 0)
            if lowSrc[index - 1] - lowSrc[index] > highSrc[index] - highSrc[index - 1]
            else 0
        )
        trSmooth.append(trSmooth[-1] - trSmooth[-1] / length + tr)
        smoothDirectionalMovementPlus.append(
            smoothDirectionalMovementPlus[-1]
            - smoothDirectionalMovementPlus[-1] / length
            + directionalMovementPlus
        )
        smoothnegMovement.append(
            smoothnegMovement[-1] - smoothnegMovement[-1] / length + negMovement
        )
        diPositive = smoothDirectionalMovementPlus[-1] / trSmooth[-1] * 100
        diNegative = smoothnegMovement[-1] / trSmooth[-1] * 100

        if index > 3:
            # skip early candles as its division by 0
            dx.append(abs(diPositive - diNegative) / (diPositive + diNegative) * 100)
    dx = numpy.array(dx)
    adx = utils.calculate_rma(dx, length)
    return rescale(adx, 0, 100, 0, 1)


def regime_filter(
    ohlc4: npt.NDArray[numpy.float64],
    highs: npt.NDArray[numpy.float64],
    lows: npt.NDArray[numpy.float64],
    threshold: float,
    use_regime_filter: bool,
) -> npt.NDArray[numpy.bool_]:
    data_length = len(ohlc4)
    if not use_regime_filter:
        return numpy.repeat(True, len(ohlc4))
    # Calculate the slope of the curve.
    values_1: list = [0.0]
    values_2: list = [0.0]
    klmfs: list = [0.0]
    abs_curve_slope: list = []
    for index in range(1, data_length):
        value_1 = 0.2 * (ohlc4[index] - ohlc4[index - 1]) + 0.8 * values_1[-1]
        value_2 = 0.1 * (highs[index] - lows[index]) + 0.8 * values_2[-1]
        values_1.append(value_1)
        values_2.append(value_2)
        omega = abs(value_1 / value_2)
        alpha = (-pow(omega, 2) + math.sqrt(pow(omega, 4) + 16 * pow(omega, 2))) / 8
        klmfs.append(alpha * ohlc4[index] + (1 - alpha) * klmfs[-1])
        abs_curve_slope.append(abs(klmfs[-1] - klmfs[-2]))
    abs_curve_slope_np: npt.NDArray[numpy.float64] = numpy.array(abs_curve_slope)
    exponentialAverageAbsCurveSlope: npt.NDArray[numpy.float64] = tulipy.ema(
        abs_curve_slope_np, 200
    )
    (
        exponentialAverageAbsCurveSlope,
        abs_curve_slope_np,
    ) = basic_utils.cut_data_to_same_len(
        (exponentialAverageAbsCurveSlope, abs_curve_slope_np)
    )
    normalized_slope_decline: npt.NDArray[numpy.float64] = (
        abs_curve_slope_np - exponentialAverageAbsCurveSlope
    ) / exponentialAverageAbsCurveSlope
    # Calculate the slope of the curve.

    return normalized_slope_decline >= threshold


def filter_adx(
    candle_closes: npt.NDArray[numpy.float64],
    candle_highs: npt.NDArray[numpy.float64],
    candle_lows: npt.NDArray[numpy.float64],
    length: int,
    adx_threshold: int,
    use_adx_filter: bool,
) -> npt.NDArray[numpy.bool_]:
    data_length: int = len(candle_closes)
    if not use_adx_filter:
        return numpy.repeat(True, len(candle_closes))
    tr_smooths: typing.List[float] = [0.0]
    smoothneg_movements: typing.List[float] = [0.0]
    smooth_directional_movement_plus: typing.List[float] = [0.0]
    dx: typing.List[float] = []
    for index in range(1, data_length):
        tr: float = max(
            max(
                candle_highs[index] - candle_lows[index],
                abs(candle_highs[index] - candle_closes[-2]),
            ),
            abs(candle_lows[index] - candle_closes[-2]),
        )
        directional_movement_plus: float = (
            max(candle_highs[index] - candle_highs[-2], 0)
            if candle_highs[index] - candle_highs[-2]
            > candle_lows[-2] - candle_lows[index]
            else 0
        )
        negMovement: float = (
            max(candle_lows[-2] - candle_lows[index], 0)
            if candle_lows[-2] - candle_lows[index]
            > candle_highs[index] - candle_highs[-2]
            else 0
        )
        tr_smooths.append(tr_smooths[-1] - tr_smooths[-1] / length + tr)

        smooth_directional_movement_plus.append(
            smooth_directional_movement_plus[-1]
            - smooth_directional_movement_plus[-1] / length
            + directional_movement_plus
        )

        smoothneg_movements.append(
            smoothneg_movements[-1] - smoothneg_movements[-1] / length + negMovement
        )

        di_positive = smooth_directional_movement_plus[-1] / tr_smooths[-1] * 100
        di_negative = smoothneg_movements[-1] / tr_smooths[-1] * 100
        if index > 3:
            # skip early candles as its division by 0
            dx.append(
                abs(di_positive - di_negative) / (di_positive + di_negative) * 100
            )
    dx: npt.NDArray[numpy.float64] = numpy.array(dx)
    adx: npt.NDArray[numpy.float64] = utils.calculate_rma(dx, length)
    return adx > adx_threshold


def filter_volatility(
    candle_highs: npt.NDArray[numpy.float64],
    candle_lows: npt.NDArray[numpy.float64],
    candle_closes: npt.NDArray[numpy.float64],
    min_length: int = 1,
    max_length: int = 10,
    use_volatility_filter: bool = True,
) -> npt.NDArray[numpy.bool_]:
    if not use_volatility_filter:
        return numpy.repeat(True, len(candle_closes))
    recentAtr = tulipy.atr(candle_highs, candle_lows, candle_closes, min_length)
    historicalAtr = tulipy.atr(candle_highs, candle_lows, candle_closes, max_length)
    recentAtr, historicalAtr = basic_utils.cut_data_to_same_len(
        (recentAtr, historicalAtr)
    )
    return recentAtr > historicalAtr
