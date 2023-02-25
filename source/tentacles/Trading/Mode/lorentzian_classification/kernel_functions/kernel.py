import math
import typing
import numpy.typing as npt
import numpy as numpy


def rationalQuadratic(
    data_source: npt.NDArray[numpy.float64],
    look_back: int,
    relative_weight: float,
    start_at_Bar: int,
):
    yhat: typing.List[float] = []
    start_at_Bar += 1 # because this is 1 on tv: _size = array.size(array.from(_src))
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
):
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
