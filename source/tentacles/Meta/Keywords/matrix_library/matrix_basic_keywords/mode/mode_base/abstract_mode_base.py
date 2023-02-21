#  Drakkar-Software OctoBot
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
import time
import importlib

import async_channel.constants as channel_constants
import octobot_commons.logging as logging
import octobot_commons.enums as commons_enums
import octobot_commons.errors as commons_errors
import octobot_commons.constants as commons_constants
import octobot_commons.databases as databases
import octobot_trading.constants as trading_constants
import octobot_trading.errors as errors
import octobot_trading.modes.script_keywords.context_management as context_management
import octobot_trading.modes.modes_util as modes_util
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.exchange_channel as exchanges_channel
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords
import octobot_trading.modes.scripted_trading_mode.abstract_scripted_trading_mode as abstract_scripted_trading_mode
import tentacles.Meta.Keywords.matrix_library.matrix_basic_keywords.matrix_enums as matrix_enums

try:
    import tentacles.Meta.Keywords.matrix_library.matrix_pro_keywords.managed_order_pro.daemons.ping_pong.simple_ping_pong as simple_ping_pong
    import tentacles.Meta.Keywords.matrix_library.matrix_pro_keywords.managed_order_pro.daemons.ping_pong.ping_pong_storage.storage as ping_pong_storage_management
except (ImportError, ModuleNotFoundError):
    simple_ping_pong = None
    ping_pong_storage_management = None

# try:

# except (ImportError, ModuleNotFoundError):
# execute_real_time_strategy = None
PING_PONG_STORAGE_LOADING_TIMEOUT = 1000


class AbstractBaseMode(abstract_scripted_trading_mode.AbstractScriptedTradingMode):

    AVAILABLE_API_ACTIONS = [matrix_enums.TradingModeCommands.EXECUTE]

    last_calls_by_exchange_id_and_time_frame: dict = {}
    ALLOW_CUSTOM_TRIGGER_SOURCE = True
    if ping_pong_storage_management:
        ping_pong_storage: ping_pong_storage_management.PingPongStorage = None
    else:
        ping_pong_storage = None
    INITIALIZED_TRADING_PAIR_BY_BOT_ID = {}

    enable_ping_pong: bool = None
    enable_real_time_strategy: bool = None
    real_time_strategy_data = None

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        self._live_script = None
        self._backtesting_script = None
        self.timestamp = time.time()
        self.script_name = None

        if exchange_manager:
            # add config folder to importable files to import the user script
            tentacles_manager_api.import_user_tentacles_config_folder(
                self.exchange_manager.tentacles_setup_config
            )
        else:
            logging.get_logger(self.get_name()).error(
                "At least one exchange must be enabled to use MatrixTradingMode"
            )

    def get_mode_producer_classes(self) -> list:
        return [AbstractBaseModeProducer]

    async def user_commands_callback(self, bot_id, subject, action, data) -> None:
        # do not call super as reload_config is called by reload_scripts already
        # on RELOAD_CONFIG command
        self.logger.debug(f"Received {action} command")
        if action == matrix_enums.TradingModeCommands.EXECUTE:
            await self._manual_trigger(data)
            self.logger.debug(
                f"Triggered trading mode from {action} command with data: {data}"
            )
        elif action == matrix_enums.TradingModeCommands.ACTIVATE_REALTIME_STRATEGY:
            self.activate_realtime_strategy()
            self.logger.info("Real time strategy activated")
        elif action == matrix_enums.TradingModeCommands.DISABLE_REALTIME_STRATEGY:
            self.disable_realtime_strategy()
            self.logger.info("Real time strategy disabled")
        elif action == commons_enums.UserCommands.RELOAD_CONFIG.value:
            # also reload script on RELOAD_CONFIG
            self.logger.debug("Reloaded configuration")
            await self.reload_scripts()
        elif action == commons_enums.UserCommands.RELOAD_SCRIPT.value:
            await self.reload_scripts()
        elif action == commons_enums.UserCommands.CLEAR_PLOTTING_CACHE.value:
            await modes_util.clear_plotting_cache(self)
        elif action == commons_enums.UserCommands.CLEAR_SIMULATED_ORDERS_CACHE.value:
            await modes_util.clear_simulated_orders_cache(self)

    def disable_realtime_strategy(self):
        self.real_time_strategy_data.disable_strategies()

    def activate_realtime_strategy(self):
        self.real_time_strategy_data.activate_strategy()

    async def _manual_trigger(self, trigger_data):
        for producer in self.producers:
            for call_args_by_symbols in self.last_calls_by_exchange_id_and_time_frame[
                self.exchange_manager.id
            ].values():
                if self.symbol in call_args_by_symbols:
                    await producer.call_script(
                        *call_args_by_symbols[self.symbol],
                        action=matrix_enums.TradingModeCommands.EXECUTE,
                    )
                else:
                    self.logger.debug(
                        "Wont't call script as last_calls_by_exchange_id_and_time_frame "
                        f"is not initialized for {self.symbol}."
                    )

    async def reload_scripts(self):
        for is_live in (False, True):
            if (is_live and self.__class__.TRADING_SCRIPT_MODULE) or (
                not is_live and self.__class__.BACKTESTING_SCRIPT_MODULE
            ):
                module = (
                    self.__class__.TRADING_SCRIPT_MODULE
                    if is_live
                    else self.__class__.BACKTESTING_SCRIPT_MODULE
                )
                importlib.reload(module)
                self.register_script_module(module, live=is_live)
                # reload config
                await self.reload_config(self.exchange_manager.bot_id)
                if is_live:
                    # todo cancel and restart live tasks
                    await self.start_over_database()

    async def start_over_database(self, action: str or dict = None):
        await clear_plotting_cache(self)
        symbol_db = databases.RunDatabasesProvider.instance().get_symbol_db(
            self.bot_id, self.exchange_manager.exchange_name, self.symbol
        )
        symbol_db.set_initialized_flags(False)
        run_db = databases.RunDatabasesProvider.instance().get_run_db(self.bot_id)
        for producer in self.producers:
            for (
                time_frame,
                call_args_by_symbols,
            ) in self.last_calls_by_exchange_id_and_time_frame[
                self.exchange_manager.id
            ].items():
                if self.symbol in call_args_by_symbols:
                    await producer.init_user_inputs(False)
                    run_db.set_initialized_flags(False, (time_frame,))
                    await databases.CacheManager().close_cache(
                        commons_constants.UNPROVIDED_CACHE_IDENTIFIER,
                        reset_cache_db_ids=True,
                    )
                    await producer.call_script(
                        *call_args_by_symbols[self.symbol],
                        action=matrix_enums.TradingModeCommands.SAVE,
                    )
                    await run_db.flush()
                else:
                    self.logger.debug(
                        "Wont't call script as last_calls_by_exchange_id_and_time_frame "
                        f"is not initialized for {self.symbol}."
                    )

    def init_user_inputs(self, inputs: dict) -> None:
        if simple_ping_pong:
            self.enable_ping_pong = self.UI.user_input(
                "enable_ping_pong",
                commons_enums.UserInputTypes.BOOLEAN.value,
                False,
                registered_inputs=inputs,
                title="Enable ping pong capabilities",
                other_schema_values={
                    "description": "requires a restart after enabling - required to use "
                    "managed ping pong orders"
                },
                show_in_optimizer=False,
                show_in_summary=False,
                order=1000,
            )
        else:
            self.enable_ping_pong = False
        import tentacles.Meta.Keywords.matrix_library.matrix_pro_keywords.modes.real_time_strategy.execute_real_time_strategy as execute_real_time_strategy

        if execute_real_time_strategy:
            self.enable_real_time_strategy = self.UI.user_input(
                "enable_real_time_strategy",
                commons_enums.UserInputTypes.BOOLEAN.value,
                False,
                registered_inputs=inputs,
                title="Enable real time strategy",
                other_schema_values={
                    "description": "requires a restart after enabling - define a "
                    "strategy that is based on the real time price"
                },
                show_in_optimizer=False,
                show_in_summary=False,
                order=1000,
            )
            if self.real_time_strategy_data:
                self.real_time_strategy_data.clear_strategies_cache()
        else:
            self.real_time_strategy = False

    async def create_consumers(self) -> list:
        """
        Creates the instance of consumers listed in MODE_CONSUMER_CLASSES
        :return: the list of consumers created
        """
        consumers = await super().create_consumers()
        if self.enable_ping_pong:
            consumers.append(
                await exchanges_channel.get_chan(
                    trading_personal_data.OrdersChannel.get_name(),
                    self.exchange_manager.id,
                ).new_consumer(
                    self._order_callback,
                    symbol=self.symbol
                    if self.symbol
                    else channel_constants.CHANNEL_WILDCARD,
                )
            )
        if self.enable_real_time_strategy:
            import tentacles.Meta.Keywords.matrix_library.matrix_pro_keywords.modes.real_time_strategy.execute_real_time_strategy as execute_real_time_strategy

            self.real_time_strategy_data: execute_real_time_strategy.RealTimeStrategies = (
                execute_real_time_strategy.RealTimeStrategies()
            )
            if (
                matrix_enums.TradingModeCommands.ACTIVATE_REALTIME_STRATEGY
                not in self.AVAILABLE_API_ACTIONS
            ):
                self.AVAILABLE_API_ACTIONS = self.AVAILABLE_API_ACTIONS + [
                    matrix_enums.TradingModeCommands.ACTIVATE_REALTIME_STRATEGY,
                    matrix_enums.TradingModeCommands.DISABLE_REALTIME_STRATEGY,
                ]
            consumers.append(
                await exchanges_channel.get_chan(
                    trading_constants.MARK_PRICE_CHANNEL, self.exchange_manager.id
                ).new_consumer(
                    self._mark_price_callback,
                    symbol=self.symbol,
                )
            )
        return consumers

    async def _mark_price_callback(
        self,
        exchange: str,
        exchange_id: str,
        cryptocurrency: str,
        symbol: str,
        mark_price,
    ):
        await self.real_time_strategy_data.run_real_time_strategies(
            trading_mode=self,
            exchange=exchange,
            exchange_id=exchange_id,
            symbol=symbol,
            mark_price=mark_price,
        )

    async def _order_callback(
        self, exchange, exchange_id, cryptocurrency, symbol, order, is_new, is_from_bot
    ):
        await simple_ping_pong.play_ping_pong(
            self,
            exchange,
            exchange_id,
            cryptocurrency,
            symbol,
            order,
            is_new,
            is_from_bot,
        )

    def set_initialized_trading_pair_by_bot_id(self, symbol, time_frame, initialized):
        # todo migrate to event tree
        try:
            self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id][
                self.exchange_manager.exchange_name
            ][symbol][time_frame] = initialized
        except KeyError:
            if self.bot_id not in self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID:
                self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id] = {}
            if (
                self.exchange_manager.exchange_name
                not in self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id]
            ):
                self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id][
                    self.exchange_manager.exchange_name
                ] = {}
            if (
                symbol
                not in self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id][
                    self.exchange_manager.exchange_name
                ]
            ):
                self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id][
                    self.exchange_manager.exchange_name
                ][symbol] = {}
            if (
                time_frame
                not in self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id][
                    self.exchange_manager.exchange_name
                ][symbol]
            ):
                self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id][
                    self.exchange_manager.exchange_name
                ][symbol][time_frame] = initialized

    def get_initialized_trading_pair_by_bot_id(self, symbol, time_frame=None):
        try:
            if not time_frame:
                return self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id][
                    self.exchange_manager.exchange_name
                ][symbol]
            return self.__class__.INITIALIZED_TRADING_PAIR_BY_BOT_ID[self.bot_id][
                self.exchange_manager.exchange_name
            ][symbol][time_frame]
        except KeyError:
            return False


class AbstractBaseModeProducer(
    abstract_scripted_trading_mode.AbstractScriptedTradingModeProducer
):
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
            self.log_last_call_by_exchange_id(
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
                self.matrix_id,
                cryptocurrency,
                symbol,
                time_frame,
                commons_enums.ActivationTopics.FULL_CANDLES.value,
                trigger_time,
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
            self.log_last_call_by_exchange_id(
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
                self.matrix_id,
                cryptocurrency,
                symbol,
                time_frame,
                commons_enums.ActivationTopics.IN_CONSTRUCTION_CANDLES.value,
                kline[commons_enums.PriceIndexes.IND_PRICE_TIME.value],
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
        try:
            await self._pre_script_call(context, action)
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

    async def _pre_script_call(self, context, action: dict or str = None):
        pass

    def log_last_call_by_exchange_id(
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
        if (
            self.exchange_manager.id
            not in self.trading_mode.last_calls_by_exchange_id_and_time_frame
        ):
            self.trading_mode.last_calls_by_exchange_id_and_time_frame[
                self.exchange_manager.id
            ] = {}
        if (
            time_frame
            not in self.trading_mode.last_calls_by_exchange_id_and_time_frame[
                self.exchange_manager.id
            ]
        ):
            self.trading_mode.last_calls_by_exchange_id_and_time_frame[
                self.exchange_manager.id
            ][time_frame] = {}

        self.trading_mode.last_calls_by_exchange_id_and_time_frame[
            self.exchange_manager.id
        ][time_frame][symbol] = (
            matrix_id,
            cryptocurrency,
            symbol,
            time_frame,
            trigger_source,
            trigger_cache_timestamp,
            candle,
            kline,
        )

    async def start(self):
        await super().start()
        if not self.exchange_manager.is_backtesting and ping_pong_storage_management:
            try:
                await ping_pong_storage_management.init_ping_pong_storage(
                    self.exchange_manager
                )
            except Exception as error:
                logging.get_logger(self.trading_mode.get_name()).exception(
                    error, True, f"Failed to restore ping pong storage - error: {error}"
                )


# TODO remove when stock octobot is fixed
async def clear_plotting_cache(trading_mode):
    await basic_keywords.clear_symbol_plot_cache(
        databases.RunDatabasesProvider.instance().get_symbol_db(
            trading_mode.bot_id,
            trading_mode.exchange_manager.exchange_name,
            trading_mode.symbol,
        )
    )
