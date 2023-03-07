import time
import importlib

import async_channel.constants as channel_constants
import octobot_commons.logging as logging
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants
import octobot_commons.databases as databases
import octobot_trading.constants as trading_constants
import octobot_trading.modes.modes_util as modes_util
import octobot_trading.personal_data as trading_personal_data
import octobot_trading.exchange_channel as exchanges_channel
import octobot_tentacles_manager.api as tentacles_manager_api
import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords
import octobot_trading.modes.scripted_trading_mode.abstract_scripted_trading_mode as abstract_scripted_trading_mode
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.matrix_basic_keywords.matrix_enums as matrix_enums
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.basic_modes.mode_base.abstract_producer_base as abstract_producer_base


PING_PONG_STORAGE_LOADING_TIMEOUT = 1000


class AbstractBaseMode(abstract_scripted_trading_mode.AbstractScriptedTradingMode):
    ENABLE_PRO_FEATURES = True
    AVAILABLE_API_ACTIONS = [matrix_enums.TradingModeCommands.EXECUTE]

    ALLOW_CUSTOM_TRIGGER_SOURCE = True
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
        return [abstract_producer_base.AbstractBaseModeProducer]

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
            await self.reload_scripts()
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
            for (
                time_frame,
                call_args_by_symbols,
            ) in producer.last_calls_by_time_frame_and_symbol.items():
                if self.symbol in call_args_by_symbols:
                    return await producer.call_script(
                        *call_args_by_symbols[self.symbol],
                        action=matrix_enums.TradingModeCommands.EXECUTE,
                    )
                else:
                    self.logger.error(
                        f"Failed to execute manual as {self.symbol} is not initialized"
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
            ) in producer.last_calls_by_time_frame_and_symbol.items():
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
                    self.logger.error(
                        f"Failed to save trading mode as {self.symbol} "
                        "is not initialized"
                    )

    def init_user_inputs(self, inputs: dict) -> None:
        if self.ENABLE_PRO_FEATURES:
            try:
                import tentacles.Meta.Keywords.matrix_library.pro_tentacles.pro_keywords.orders.managed_order_pro.daemons.ping_pong.simple_ping_pong as simple_ping_pong
            except (ImportError, ModuleNotFoundError):
                simple_ping_pong = None
            if simple_ping_pong:
                self.enable_ping_pong = self.UI.user_input(
                    "enable_ping_pong",
                    commons_enums.UserInputTypes.BOOLEAN.value,
                    False,
                    registered_inputs=inputs,
                    title="Enable ping pong capabilities",
                    other_schema_values={
                        "description": "requires a restart after enabling - "
                        "required to use managed ping pong orders"
                    },
                    show_in_optimizer=False,
                    show_in_summary=False,
                    order=1000,
                )
            else:
                self.enable_ping_pong = False
            import tentacles.Meta.Keywords.matrix_library.pro_tentacles.pro_modes.real_time_strategy.execute_real_time_strategy as execute_real_time_strategy

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
            import tentacles.Meta.Keywords.matrix_library.pro_tentacles.pro_modes.real_time_strategy.execute_real_time_strategy as execute_real_time_strategy

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
        try:
            import tentacles.Meta.Keywords.matrix_library.pro_tentacles.pro_keywords.orders.managed_order_pro.daemons.ping_pong.simple_ping_pong as simple_ping_pong
        except (ImportError, ModuleNotFoundError):
            simple_ping_pong = None
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


# TODO remove when stock octobot is fixed
async def clear_plotting_cache(trading_mode):
    await basic_keywords.clear_symbol_plot_cache(
        databases.RunDatabasesProvider.instance().get_symbol_db(
            trading_mode.bot_id,
            trading_mode.exchange_manager.exchange_name,
            trading_mode.symbol,
        )
    )
