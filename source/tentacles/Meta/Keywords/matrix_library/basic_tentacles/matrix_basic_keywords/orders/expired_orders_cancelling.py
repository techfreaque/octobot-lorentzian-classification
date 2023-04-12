import time

import octobot_commons.enums as commons_enums
import tentacles.Meta.Keywords.scripting_library.orders.cancelling as cancelling


async def cancel_expired_orders_for_this_candle(
    ctx, limit_max_age_in_bars: int, symbol: str = None, time_frame: str = None
):
    until = int(
        time.time()
        - (
            commons_enums.TimeFramesMinutes[
                commons_enums.TimeFrames(time_frame or ctx.time_frame)
            ]
            * limit_max_age_in_bars
            * 60
        )
    )
    try:
        await cancelling.cancel_orders(ctx, symbol=symbol or ctx.symbol, until=until)
    except TypeError:
        # TODO remove
        ctx.logger.error(
            "Not able to cancel epxired orders as this is currently not "
            "possible on stock OctoBot. You need to manage order "
            "cancelling by yourself"
        )
