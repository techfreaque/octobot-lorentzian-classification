import math

import tentacles.Trading.Mode.lorentzian_classification.utils as utils


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
