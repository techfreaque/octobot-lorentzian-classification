import math
import typing
import numpy.typing as npt
import numpy as numpy


def rationalQuadratic(
    _src: npt.NDArray[numpy.float64],
    _lookback: int,
    _relativeWeight: float,
    startAtBar: int,
):
    yhat: typing.List[float] = []
    _currentWeight: float = 0
    _cumulativeWeight: float = 0
    for index in range(1, len(_src) - startAtBar + 1):
        y = _src[index]
        w = pow(
            1 + (pow(index - 1, 2) / ((pow(_lookback, 2) * 2 * _relativeWeight))),
            -_relativeWeight,
        )
        _currentWeight += y * w
        _cumulativeWeight += w
        yhat.append(_currentWeight / _cumulativeWeight)
    return yhat


def gaussian(_src: npt.NDArray[numpy.float64], _lookback: int, startAtBar: int):
    _currentWeight: float = 0
    _cumulativeWeight: float = 0
    yhat: typing.List[float] = []

    for index in range(1, len(_src) - startAtBar):
        y = _src[-index]
        w = math.exp(-pow(index - 1, 2) / (2 * pow(_lookback, 2)))
        _currentWeight += y * w
        _cumulativeWeight += w
        yhat.insert(0, _currentWeight / _cumulativeWeight)
    return yhat
