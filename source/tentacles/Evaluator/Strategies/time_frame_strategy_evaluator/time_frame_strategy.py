#  Drakkar-Software OctoBot-Tentacles
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
import octobot_commons.constants as common_constants
import octobot_commons.enums as common_enums
import octobot_evaluators.evaluators as evaluators
import octobot_evaluators.constants as constants


class TimeFrameStrategyEvaluator(evaluators.StrategyEvaluator):
    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the tentacle,
        should define all the tentacle's user inputs unless
        those are defined somewhere else.
        """
        self.UI.user_input(
            constants.STRATEGIES_REQUIRED_TIME_FRAME,
            common_enums.UserInputTypes.MULTIPLE_OPTIONS,
            [common_enums.TimeFrames.ONE_HOUR.value],
            inputs,
            options=[tf.value for tf in common_enums.TimeFrames],
            title="loaded time frames (requires a restart)",
            other_schema_values={
                "description": "The time frames that can be accessed by the trading mode"
            },
        )
        self.UI.user_input(
            common_constants.CONFIG_TENTACLES_REQUIRED_CANDLES_COUNT,
            common_enums.UserInputTypes.INT,
            2000,
            inputs,
            min_val=200,
            title="Amount of historical live candles (requires a restart of Octobot)",
            other_schema_values={
                "description": "The number of historical bars you see on the chart. "
                "And also how much historical data your trading mode gets for"
                " each execution on each bar. "
                "The lower this value is, the faster each bar will get executed!"
            },
        )
        # # TODO replace with common_constants.CONFIG_TENTACLES_BACKTESTING_REQUIRED_CANDLES_COUNT
        # self.specific_config["backtesting_required_candles_count"] = 200

    def get_full_cycle_evaluator_types(self) -> tuple:
        return []

    async def matrix_callback(
        self,
        matrix_id,
        evaluator_name,
        evaluator_type,
        eval_note,
        eval_note_type,
        exchange_name,
        cryptocurrency,
        symbol,
        time_frame,
    ):
        self.eval_note = eval_note
        await self.strategy_completed(cryptocurrency, symbol, time_frame=time_frame)
