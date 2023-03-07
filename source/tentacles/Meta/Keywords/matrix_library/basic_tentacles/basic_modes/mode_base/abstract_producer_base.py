import octobot_commons.logging as logging
import octobot_commons.enums as commons_enums
import octobot_commons.errors as commons_errors
import octobot_commons.constants as commons_constants
import octobot_commons.databases as databases
import octobot_trading.errors as errors
import octobot_trading.util as util
import octobot_trading.modes.script_keywords.basic_keywords.user_inputs as user_inputs
import octobot_trading.modes.script_keywords.context_management as context_management
import octobot_trading.modes.scripted_trading_mode.abstract_scripted_trading_mode as abstract_scripted_trading_mode
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.matrix_basic_keywords.matrix_enums as matrix_enums


class AbstractBaseModeProducer(
    abstract_scripted_trading_mode.AbstractScriptedTradingModeProducer
):
    ctx: context_management.Context = None
    last_calls_by_time_frame_and_symbol: dict = {}

    def __init__(self, channel, config, trading_mode, exchange_manager):
        super(AbstractBaseModeProducer, self).__init__(
            channel, config, trading_mode, exchange_manager
        )

    async def ohlcv_callback(
        self,
        exchange: str,
        exchange_id: str,
        cryptocurrency: str,
        symbol: str,
        time_frame: str,
        candle: dict,
        init_call: bool = False,
    ):
        async with self.trading_mode_trigger(), self.trading_mode.remote_signal_publisher(
            symbol
        ):
            # add a full candle to time to get the real time
            trigger_time = (
                candle[commons_enums.PriceIndexes.IND_PRICE_TIME.value]
                + commons_enums.TimeFramesMinutes[commons_enums.TimeFrames(time_frame)]
                * commons_constants.MINUTE_TO_SECONDS
            )
            self.log_last_call_by_time_frame_and_symbol(
                matrix_id=self.matrix_id,
                cryptocurrency=cryptocurrency,
                symbol=symbol,
                time_frame=time_frame,
                trigger_source=commons_enums.ActivationTopics.FULL_CANDLES.value,
                trigger_cache_timestamp=trigger_time,
                candle=candle,
                kline=None,
            )
            await self.call_script(
                matrix_id=self.matrix_id,
                cryptocurrency=cryptocurrency,
                symbol=symbol,
                time_frame=time_frame,
                trigger_source=commons_enums.ActivationTopics.FULL_CANDLES.value,
                trigger_cache_timestamp=trigger_time,
                candle=candle,
                action=matrix_enums.TradingModeCommands.INIT_CALL
                if init_call
                else matrix_enums.TradingModeCommands.OHLC_CALLBACK,
                init_call=init_call,
            )

    async def kline_callback(
        self,
        exchange: str,
        exchange_id: str,
        cryptocurrency: str,
        symbol: str,
        time_frame,
        kline: dict,
    ):
        async with self.trading_mode_trigger(), self.trading_mode.remote_signal_publisher(
            symbol
        ):
            self.log_last_call_by_time_frame_and_symbol(
                matrix_id=self.matrix_id,
                cryptocurrency=cryptocurrency,
                symbol=symbol,
                time_frame=time_frame,
                trigger_source=commons_enums.ActivationTopics.IN_CONSTRUCTION_CANDLES.value,
                trigger_cache_timestamp=kline[
                    commons_enums.PriceIndexes.IND_PRICE_TIME.value
                ],
                candle=None,
                kline=kline,
            )
            await self.call_script(
                matrix_id=self.matrix_id,
                cryptocurrency=cryptocurrency,
                symbol=symbol,
                time_frame=time_frame,
                trigger_source=commons_enums.ActivationTopics.IN_CONSTRUCTION_CANDLES.value,
                trigger_cache_timestamp=kline[
                    commons_enums.PriceIndexes.IND_PRICE_TIME.value
                ],
                action=matrix_enums.TradingModeCommands.KLINE_CALLBACK,
                kline=kline,
            )

    async def call_script(
        self,
        matrix_id: str,
        cryptocurrency: str,
        symbol: str,
        time_frame: str,
        trigger_source: str,
        trigger_cache_timestamp: float,
        candle: dict = None,
        kline: dict = None,
        init_call: bool = False,
        action: str or dict = None,
    ):
        context = context_management.get_full_context(
            self.trading_mode,
            matrix_id,
            cryptocurrency,
            symbol,
            time_frame,
            trigger_source,
            trigger_cache_timestamp,
            candle,
            kline,
            init_call=init_call,
        )
        context.matrix_id = matrix_id
        context.cryptocurrency = cryptocurrency
        context.symbol = symbol
        context.time_frame = time_frame
        initialized = True
        run_data_writer = databases.RunDatabasesProvider.instance().get_run_db(
            self.exchange_manager.bot_id
        )
        self.ctx = context
        try:
            await self.make_strategy(context, action)
            if (
                hasattr(self.trading_mode, "TRADING_SCRIPT_MODULE")
                and self.trading_mode.TRADING_SCRIPT_MODULE
            ):
                await self.trading_mode.get_script(live=True)(context)
        except errors.UnreachableExchange:
            raise
        except (commons_errors.MissingDataError, commons_errors.ExecutionAborted) as e:
            self.logger.debug(f"Script execution aborted: {e}")
            initialized = run_data_writer.are_data_initialized
        except Exception as e:
            self.logger.exception(e, True, f"Error when running script: {e}")
        finally:
            if not self.exchange_manager.is_backtesting:

                if context.has_cache(context.symbol, context.time_frame):
                    await context.get_cache().flush()
                for symbol in self.exchange_manager.exchange_config.traded_symbol_pairs:
                    await databases.RunDatabasesProvider.instance().get_symbol_db(
                        self.exchange_manager.bot_id,
                        self.exchange_manager.exchange_name,
                        symbol,
                    ).flush()
            run_data_writer.set_initialized_flags(initialized)
            databases.RunDatabasesProvider.instance().get_symbol_db(
                self.exchange_manager.bot_id, self.exchange_name, symbol
            ).set_initialized_flags(initialized, (time_frame,))

    async def make_strategy(self, context, action: dict or str = None):
        pass

    def log_last_call_by_time_frame_and_symbol(
        self,
        matrix_id,
        cryptocurrency,
        symbol,
        time_frame,
        trigger_source,
        trigger_cache_timestamp,
        candle,
        kline,
    ):
        if time_frame not in self.last_calls_by_time_frame_and_symbol:
            self.last_calls_by_time_frame_and_symbol[time_frame] = {}
        self.last_calls_by_time_frame_and_symbol[time_frame][symbol] = (
            matrix_id,
            cryptocurrency,
            symbol,
            time_frame,
            trigger_source,
            trigger_cache_timestamp,
            candle,
            kline,
        )

    async def _register_and_apply_required_user_inputs(self, context):
        if self.trading_mode.ALLOW_CUSTOM_TRIGGER_SOURCE:
            # register activating topics user input
            activation_topic_values = [
                commons_enums.ActivationTopics.FULL_CANDLES.value,
                # commons_enums.ActivationTopics.IN_CONSTRUCTION_CANDLES.value,
            ]
            await user_inputs.get_activation_topics(
                context,
                commons_enums.ActivationTopics.FULL_CANDLES.value,
                activation_topic_values,
            )
        if context.exchange_manager.is_future:
            await util.wait_for_topic_init(
                self.exchange_manager,
                self.CONFIG_INIT_TIMEOUT,
                commons_enums.InitializationEventExchangeTopics.CONTRACTS.value,
            )

    async def start(self):
        await super().start()
        try:
            import tentacles.Meta.Keywords.matrix_library.pro_tentacles.pro_keywords.orders.managed_order_pro.daemons.ping_pong.ping_pong_storage.storage as ping_pong_storage_management
        except (ImportError, ModuleNotFoundError):
            ping_pong_storage_management = None
        if not self.exchange_manager.is_backtesting and ping_pong_storage_management:
            try:
                await ping_pong_storage_management.init_ping_pong_storage(
                    self.exchange_manager
                )
            except Exception as error:
                logging.get_logger(self.trading_mode.get_name()).exception(
                    error, True, f"Failed to restore ping pong storage - error: {error}"
                )
