from octobot_trading.modes.script_keywords.context_management import Context
from tentacles.Meta.Keywords.scripting_library.data.writing import plotting


async def plot_conditional(
    ctx: Context,
    title: str,
    signals,
    values,
    times,
    value_key: str,
    chart_location: str = "main-chart",
    own_yaxis: bool = False,
):
    y_values = []
    y_times = []
    for index, signal in enumerate(signals):
        if signal:
            y_values.append(values[index])
            y_times.append(times[index])
    if len(y_values) > 0:
        await ctx.set_cached_values(
            values=y_values,
            cache_keys=y_times,
            value_key=value_key,
        )
        await plotting.plot(
            ctx,
            title=title,
            cache_value=value_key,
            chart=chart_location,
            own_yaxis=own_yaxis,
            mode="markers",
            line_shape=None,
        )
