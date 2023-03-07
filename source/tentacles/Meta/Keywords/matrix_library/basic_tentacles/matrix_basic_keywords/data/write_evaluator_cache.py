import numpy as np
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.matrix_basic_keywords.data.public_exchange_data as public_exchange_data


async def store_evaluator_history(
    maker,
    ctx,
    indicator_values,
    signals_data,
    plot_enabled=True,
    additional_values_by_key=None,
):
    # store it in one go
    times = await public_exchange_data.get_candles_(
        maker, "time", time_frame=maker.ctx.time_frame
    )
    data_length = len(signals_data)
    times = times[-data_length:]

    if plot_enabled:
        plot_cache_key = (
            f"{commons_enums.CacheDatabaseColumns.VALUE.value}"
            f"{commons_constants.CACHE_RELATED_DATA_SEPARATOR}y"
        )
        y_cache = []
        y_times = []
        indicator_values = indicator_values[-data_length:]
        for index, signal_value in enumerate(signals_data):
            if signal_value:
                y_cache.append(indicator_values[index])
                y_times.append(times[index])
        await ctx.set_cached_values(
            values=y_cache, cache_keys=y_times, value_key=plot_cache_key
        )
    await ctx.set_cached_values(
        values=signals_data,
        cache_keys=times,
        value_key=commons_enums.CacheDatabaseColumns.VALUE.value,
        additional_values_by_key=additional_values_by_key,
    )
    # write cache flag on the first candle,
    # cause we dont know on which timestamp the first cached result is
    await ctx.set_cached_value(value=True, value_key="csh")


async def store_indicator_history(
    maker,
    indicator_values,
    value_key=commons_enums.CacheDatabaseColumns.VALUE.value,
    additional_values_by_key=None,
    enable_rounding=True,
    filter_nan_for_plots=False,
):
    if additional_values_by_key is None:
        additional_values_by_key = {}
    round_decimals = None
    if enable_rounding:
        if max(indicator_values) < 1 and min(indicator_values) > -1:
            round_decimals = 8
        else:
            round_decimals = 3
    # store it in one go
    time_data = await public_exchange_data.get_candles_(
        maker, "time", time_frame=maker.ctx.time_frame
    )
    cut_t = time_data[-len(indicator_values) :]
    if round_decimals:
        indicator_values = np.round(indicator_values, decimals=round_decimals)
        if additional_values_by_key:
            for key in additional_values_by_key:
                additional_values_by_key[key] = np.round(
                    additional_values_by_key[key], decimals=2
                )
    if filter_nan_for_plots:
        additional_values_by_key[value_key] = indicator_values
        for _value_key, values in additional_values_by_key.items():
            final_values = []
            final_times = []
            cut_t = time_data[-len(values) :]
            for index, value in enumerate(values):
                if str(value) != str(np.nan):
                    final_values.append(value)
                    final_times.append(cut_t[index])
            await maker.ctx.set_cached_values(
                values=final_values,
                cache_keys=final_times,
                value_key=_value_key,
            )
    else:
        await maker.ctx.set_cached_values(
            values=indicator_values,
            cache_keys=cut_t,
            value_key=value_key,
            additional_values_by_key=additional_values_by_key,
        )
