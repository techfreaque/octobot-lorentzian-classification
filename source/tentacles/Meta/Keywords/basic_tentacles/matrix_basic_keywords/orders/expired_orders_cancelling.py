import octobot_commons.enums as commons_enums
import tentacles.Meta.Keywords.scripting_library.orders.cancelling as cancelling


async def cancel_expired_orders_for_this_candle(
    ctx,
    limit_max_age_in_bars: int,
    symbol: str = None,
    time_frame: str = None,
    tag: str = None,
):
    until = int(
        ctx.trigger_cache_timestamp
        - (
            commons_enums.TimeFramesMinutes[
                commons_enums.TimeFrames(time_frame or ctx.time_frame)
            ]
            * limit_max_age_in_bars
            * 60
        )
    )
    await cancelling.cancel_orders(
        ctx, symbol=symbol or ctx.symbol, until=until, tag=tag
    )
