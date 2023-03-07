#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import octobot_commons.time_frame_manager as time_frame_manager
import octobot_commons.errors as commons_errors
import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords


async def set_trigger_time_frames(
    ctx, def_val=None, show_in_summary=True, show_in_optimizer=False, order=None
):
    available_timeframes = [
        tf.value
        for tf in time_frame_manager.sort_time_frames(
            ctx.exchange_manager.exchange_config.get_relevant_time_frames()
        )
    ]
    def_val = def_val or available_timeframes
    trigger_timeframes = await basic_keywords.user_input(
        ctx,
        "trading_mode_trigger_time_frames",
        input_type="multiple-options",
        def_val=def_val or [],
        title="Trading mode trigger time frames",
        options=available_timeframes,
        show_in_summary=show_in_summary,
        show_in_optimizer=show_in_optimizer,
        order=order,
    )
    return trigger_timeframes


def cancel_non_trigger_time_frames(ctx, trigger_timeframes):
    if ctx.time_frame not in trigger_timeframes:
        # ctx.time_frame == "1d" or
        # if isinstance(ctx.tentacle, evaluators.AbstractEvaluator):

        # For evaluators, make sure that undesired time frames are not in matrix anymore.
        # Otherwise a strategy might wait for their value before pushing its evaluation to trading modes
        # matrix.delete_tentacle_node(
        #     matrix_id=ctx.tentacle.matrix_id,
        #     tentacle_path=matrix.get_matrix_default_value_path(
        #         exchange_name=ctx.exchange_manager.exchange_name,
        #         tentacle_type=ctx.tentacle.evaluator_type.value,
        #         tentacle_name=ctx.tentacle.get_name(),
        #         cryptocurrency=ctx.cryptocurrency,
        #         symbol=ctx.symbol,
        #         time_frame=ctx.time_frame if ctx.time_frame else None,
        #     ),
        # )
        # if ctx.exchange_manager.is_backtesting:
        #     skip_runs.register_backtesting_timestamp_whitelist(ctx, [], append_to_whitelist=False)
        raise commons_errors.ExecutionAborted(
            f"Execution aborted: disallowed time frame: {ctx.time_frame}"
        )
