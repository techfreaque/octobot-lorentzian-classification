import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.databases as commons_databases
import octobot_evaluators.util as evaluators_util
from ....Trading.Mode.lorentzian_classification.classification import LorentzianClassificationScript


class LorentzianClassification(LorentzianClassificationScript):
    last_call: tuple = None

    async def evaluate(
        self,
        exchange: str,
        exchange_id: str,
        cryptocurrency: str,
        symbol: str,
        trigger_cache_timestamp: float,
        trigger_source: str,
        time_frame: str,
        candle: dict,
        inc_in_construction_data,
    ):
        self.last_call = (
            exchange,
            exchange_id,
            cryptocurrency,
            symbol,
            trigger_cache_timestamp,
            trigger_source,
            time_frame,
            candle,
            inc_in_construction_data,
        )
        context = evaluators_util.local_trading_context(
            self,
            symbol,
            time_frame,
            trigger_cache_timestamp,
            cryptocurrency=cryptocurrency,
            exchange=exchange,
            exchange_id=exchange_id,
            trigger_source=trigger_source,
            trigger_value=candle,
        )
        await self.evaluate_lorentzian_classification(
            ctx=context,
            exchange=exchange,
            exchange_id=exchange_id,
            cryptocurrency=cryptocurrency,
            symbol=symbol,
            time_frame=time_frame,
            candle=candle,
            inc_in_construction_data=inc_in_construction_data,
        )

    async def ohlcv_callback(
        self,
        exchange: str,
        exchange_id: str,
        cryptocurrency: str,
        symbol: str,
        time_frame,
        candle,
        inc_in_construction_data,
    ):
        # add a full candle to time to get the real time
        trigger_time = (
            candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value]
            + commons_enums.TimeFramesMinutes[commons_enums.TimeFrames(time_frame)]
            * commons_constants.MINUTE_TO_SECONDS
        )
        await self.evaluate(
            exchange,
            exchange_id,
            cryptocurrency,
            symbol,
            trigger_time,
            commons_enums.TriggerSource.OHLCV.value,
            time_frame=time_frame,
            candle=candle,
            inc_in_construction_data=inc_in_construction_data,
        )

    async def user_commands_callback(self, bot_id, subject, action, data) -> None:
        self.logger.debug(f"Received {action} command")
        if action in (
            commons_enums.UserCommands.RELOAD_SCRIPT.value,
            commons_enums.UserCommands.RELOAD_CONFIG.value,
        ):
            await self._reload_evaluator(bot_id)

    async def _reload_evaluator(self, bot_id):
        if self.last_call:
            # recall evaluator with for are_data_initialized to false to re-write initial data
            run_data_db, symbol_db = self._get_run_and_symbol_dbs()
            time_frames = (
                None if self.get_is_time_frame_wildcard() else (self.time_frame.value,)
            )
            run_data_db.set_initialized_flags(False)
            symbol_db.set_initialized_flags(False, time_frames)
            self._has_script_been_called_once = False
            try:
                await self.evaluate(*self.last_call)
            finally:
                await run_data_db.flush()
                run_data_db.set_initialized_flags(True)
                await symbol_db.flush()
                symbol_db.set_initialized_flags(True, time_frames)
        else:
            self.logger.warning(
                "Not able to reload as last candle call is not initialized"
            )

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not symbol dependant else False
        """
        return False

    @classmethod
    def get_is_time_frame_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not time_frame dependant else False
        """
        return False

    def _get_run_and_symbol_dbs(self):
        try:
            import octobot_trading.api as trading_api

            exchange_manager = (
                trading_api.get_exchange_manager_from_exchange_name_and_id(
                    self.exchange_name,
                    trading_api.get_exchange_id_from_matrix_id(
                        self.exchange_name, self.matrix_id
                    ),
                )
            )
            bot_id = trading_api.get_bot_id(exchange_manager)
            provider = commons_databases.RunDatabasesProvider.instance()
            return provider.get_run_db(bot_id), provider.get_symbol_db(
                bot_id, self.exchange_name, self.symbol
            )
        except ImportError:
            self.logger.error("required OctoBot-trading to get a trading mode writer")
            raise
