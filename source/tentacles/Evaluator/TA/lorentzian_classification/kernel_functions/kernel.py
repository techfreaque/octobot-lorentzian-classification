import math
import typing
import numpy.typing as npt
import numpy as numpy

def rationalQuadratic(_src: npt.NDArray[numpy.float64],  _lookback: int,  _relativeWeight: float,  startAtBar: int):
    yhat: typing.List[float] = []
    for index in range(len(_src)):
        _currentWeight: float = 0
        _cumulativeWeight: float = 0
        _size = array.size(array.from(_src))
        for i = 0 to _size + startAtBar
            y = _src[i]
            w = math.pow(1 + (math.pow(i, 2) / ((math.pow(_lookback, 2) * 2 * _relativeWeight))), -_relativeWeight)
            _currentWeight += y*w
            _cumulativeWeight += w
        yhat.append(_currentWeight / _cumulativeWeight)
    return yhat

def gaussian(_src: npt.NDArray[numpy.float64],  _lookback: int,  startAtBar: int):
    data_length = len(_src)
    _currentWeight: float = 0
    _cumulativeWeight: float = 0
    yhat: typing.List[float] = []

    for index in range(1, len(_src)-startAtBar):
        bar_back_count = bars_back_index-index*-1
        y = _src[-index] 
        w = math.exp(-pow(bar_back_count, 2) / (2 * pow(_lookback, 2)))
        _currentWeight += y*w
        _cumulativeWeight += w
        yhat = _currentWeight / _cumulativeWeight
    return yhat
    
        bars_back_index-index*-1 = index-startAtBar