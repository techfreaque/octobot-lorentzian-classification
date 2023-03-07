import typing
import octobot_commons.enums as commons_enums
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_trading.modes.script_keywords.basic_keywords.user_inputs as user_inputs
import octobot_trading.api.symbol_data as symbol_data
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.basic_modes.mode_base.abstract_producer_base as abstract_producer_base
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.basic_modes.mode_base.producer_base as producer_base
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.matrix_basic_keywords.matrix_enums as matrix_enums
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.basic_modes.spot_master.spot_master_enums as spot_master_enums
import tentacles.Meta.Keywords.scripting_library.data.writing.plotting as plotting


class SpotMaster3000ModeSettings(
    abstract_producer_base.AbstractBaseModeProducer,
    producer_base.MatrixProducerBase,
):
    target_settings: dict = {}
    coins_to_trade: typing.List[str] = []
    ref_market: str = None
    threshold_to_sell: float = None
    threshold_to_buy: float = None
    step_to_sell: float = None
    step_to_buy: float = None
    max_buffer_allocation: float = None
    min_buffer_allocation: float = None
    limit_buy_offset: float = None
    limit_sell_offset: float = None
    limit_max_age_in_bars: int = None
    spot_master_name = "spot_master_3000"
    order_type = None
    available_coins: typing.List[str] = []
    available_symbols: typing.List[str] = []
    round_orders: bool = None
    round_orders_max_value: float = None

    enable_plot_portfolio_p: bool = None
    enable_plot_portfolio_ref: bool = None
    live_plotting_modes: typing.List[str] = [
        matrix_enums.LivePlottingModes.DISABLE_PLOTTING.value,
        matrix_enums.LivePlottingModes.PLOT_RECORDING_MODE.value,
    ]
    live_plotting_mode: str = matrix_enums.LivePlottingModes.PLOT_RECORDING_MODE.value

    def __init__(self, channel, config, trading_mode, exchange_manager):
        abstract_producer_base.AbstractBaseModeProducer.__init__(
            self, channel, config, trading_mode, exchange_manager
        )
        producer_base.MatrixProducerBase.__init__(
            self, channel, config, trading_mode, exchange_manager
        )

    async def init_spot_master_settings(self, ctx) -> None:
        self.set_available_coins_and_symbols()
        await user_inputs.user_input(
            self.ctx,
            self.spot_master_name,
            commons_enums.UserInputTypes.OBJECT,
            def_val=None,
            title="SpotMaster 3000 settings",
            editor_options={
                "grid_columns": 12,
            },
            other_schema_values={
                "description": "If you have questions, issues, etc, let me know here: "
                "https://github.com/techfreaque/octobot-spot-master-3000",
            },
            show_in_summary=False,
        )
        self.coins_to_trade = await user_inputs.user_input(
            self.ctx,
            "selected_coins",
            commons_enums.UserInputTypes.MULTIPLE_OPTIONS,
            def_val=self.available_coins,
            options=self.available_coins,
            title="Select the coins to hold/trade",
            parent_input_name=self.spot_master_name,
            editor_options={
                "grid_columns": 12,
            },
            other_schema_values={
                "description": "The reference market should be selected and "
                "make sure the allocation for each coin adds up to 100%. ",
            },
        )
        await self.init_balancing_settings()
        await self.init_coin_settings()

    def set_available_coins_and_symbols(self) -> None:
        coins: set = set()
        self.available_symbols: typing.List[str] = symbol_data.get_config_symbols(
            self.ctx.exchange_manager.config, True
        )
        for symbol in self.available_symbols:
            symbol_obj = symbol_util.parse_symbol(symbol)
            coins.add(symbol_obj.quote)
            coins.add(symbol_obj.base)
        self.available_coins = list(coins)

    async def init_balancing_settings(self) -> None:
        await self.init_order_type_settings()
        self.threshold_to_sell = await user_inputs.user_input(
            self.ctx,
            "threshold_to_sell",
            commons_enums.UserInputTypes.FLOAT,
            def_val=1,
            title="Threshold to sell in %",
            parent_input_name=self.spot_master_name,
            other_schema_values={
                "grid_columns": 4,
                "description": "Whenever a asset reaches the allocation % + "
                "the threshold %, it will start to sell",
            },
        )
        self.threshold_to_buy = await user_inputs.user_input(
            self.ctx,
            "threshold_to_buy",
            commons_enums.UserInputTypes.FLOAT,
            def_val=1,
            title="Threshold to buy in %",
            parent_input_name=self.spot_master_name,
            other_schema_values={
                "grid_columns": 4,
                "description": "Whenever a asset reaches the allocation % + "
                "the threshold %, it will start to buy",
            },
        )
        self.step_to_sell = await user_inputs.user_input(
            self.ctx,
            "step_to_sell",
            commons_enums.UserInputTypes.FLOAT,
            def_val=1,
            title="Maximum size to sell per coin and candle in %",
            parent_input_name=self.spot_master_name,
            other_schema_values={
                "grid_columns": 4,
                "description": "Maximum amount to sell in percent, based on total "
                "portfolio value, for each coin and candle.",
            },
        )
        self.step_to_buy = await user_inputs.user_input(
            self.ctx,
            "step_to_buy",
            commons_enums.UserInputTypes.FLOAT,
            def_val=1,
            title="Maximum size to buy per coin and candle in %",
            parent_input_name=self.spot_master_name,
            other_schema_values={
                "grid_columns": 4,
                "description": "Maximum amount to buy in percent, based on total "
                "portfolio value, for each coin and candle.",
            },
        )
        self.max_buffer_allocation = await user_inputs.user_input(
            self.ctx,
            "max_buffer_allocation",
            commons_enums.UserInputTypes.FLOAT,
            def_val=5,
            title="Maximum allocation buffer in % (allocation + max_allocation)",
            parent_input_name=self.spot_master_name,
            other_schema_values={
                "grid_columns": 4,
                "description": "If a asset allocation is currently higher as the "
                "defined allocation % + maximum allocation buffer %. It will force "
                "sell, so you end up with the defined allocation % + "
                "maximum allocation buffer %.",
            },
        )
        self.min_buffer_allocation = await user_inputs.user_input(
            self.ctx,
            "min_buffer_allocation",
            commons_enums.UserInputTypes.FLOAT,
            def_val=5,
            title="Minimum allocation buffer in % (allocation - min_allocation)",
            parent_input_name=self.spot_master_name,
            other_schema_values={
                "grid_columns": 4,
                "description": "If a asset allocation is currently lower as the "
                "defined allocation % - minmum allocation buffer %. It will force "
                "buy, so you end up with the defined allocation % - "
                "minimum allocation buffer %.",
            },
        )

    async def init_coin_settings(self) -> None:
        self.target_settings = {}
        for coin in self.coins_to_trade:
            coin_selector_allocation_name = f"allocation_for_{coin}"
            await user_inputs.user_input(
                self.ctx,
                coin_selector_allocation_name,
                commons_enums.UserInputTypes.OBJECT,
                def_val=None,
                title=f"Settings for {coin}",
                other_schema_values={
                    "grid_columns": 4,
                },
                show_in_summary=False,
            )
            self.target_settings[coin] = {
                "allocation": await user_inputs.user_input(
                    self.ctx,
                    f"allocation_{coin}",
                    commons_enums.UserInputTypes.FLOAT,
                    def_val=100 / len(self.coins_to_trade),
                    options=self.available_coins,
                    title="Select the optimal allocation in %",
                    parent_input_name=coin_selector_allocation_name,
                    other_schema_values={
                        "grid_columns": 4,
                        "description": "Define the optimal amount in percent "
                        f"to hold of {coin}",
                    },
                ),
            }

    async def init_order_type_settings(self) -> None:
        self.order_type = await user_inputs.user_input(
            self.ctx,
            "order_type",
            commons_enums.UserInputTypes.OPTIONS,
            def_val=spot_master_enums.SpotMasterOrderTypes.MARKET.value,
            title="Order type",
            options=[
                spot_master_enums.SpotMasterOrderTypes.MARKET.value,
                spot_master_enums.SpotMasterOrderTypes.LIMIT.value,
            ],
            parent_input_name=self.spot_master_name,
            other_schema_values={
                "grid_columns": 4,
                "description": "Market orders will get filled emidiatly, "
                "but have higher fees. While limit orders might not get filled, "
                "but the fees are cheaper and you can place the order "
                "below/above the price.",
            },
        )
        if self.order_type == spot_master_enums.SpotMasterOrderTypes.LIMIT.value:
            self.limit_buy_offset = await user_inputs.user_input(
                self.ctx,
                "limit_buy_offset",
                commons_enums.UserInputTypes.FLOAT,
                def_val=0.5,
                title="Distance in % from current price to buy limit orders",
                parent_input_name=self.spot_master_name,
                other_schema_values={
                    "grid_columns": 4,
                    "description": "Whenever a rebalancing gets triggered it will "
                    "place the buy order X % below the current price",
                },
            )
            self.limit_sell_offset = await user_inputs.user_input(
                self.ctx,
                "limit_sell_offset",
                commons_enums.UserInputTypes.FLOAT,
                def_val=0.5,
                title="Distance in % from current price to sell limit orders",
                parent_input_name=self.spot_master_name,
                other_schema_values={
                    "grid_columns": 4,
                    "description": "Whenever a rebalancing gets triggered it will "
                    "place the sell order X % above the current price",
                },
            )
            self.limit_max_age_in_bars = await user_inputs.user_input(
                self.ctx,
                "limit_max_age",
                commons_enums.UserInputTypes.INT,
                def_val=3,
                min_val=1,
                title="Maximum bars to wait for a limit order to get filled",
                parent_input_name=self.spot_master_name,
                other_schema_values={
                    "grid_columns": 4,
                    "description": "This is currently not supported on stock OctoBot. "
                    "If the order is still unfilled after the time is"
                    "passed, the order will get cancelled and the balance "
                    "will be available for rebalancing again.",
                },
            )
        self.round_orders = await user_inputs.user_input(
            self.ctx,
            "round_orders",
            commons_enums.UserInputTypes.BOOLEAN,
            def_val=False,
            title="Enable rounding up to minimum order value",
            parent_input_name=self.spot_master_name,
            other_schema_values={
                "grid_columns": 4,
                "description": "This is only helpful for small balance accounts, if "
                "enabled it will round up buy/sell orders to the minimum order value "
                "required by the exchange.",
            },
        )
        if self.round_orders:
            self.round_orders_max_value = await user_inputs.user_input(
                self.ctx,
                "round_orders_max_value",
                commons_enums.UserInputTypes.FLOAT,
                def_val=50,
                min_val=0,
                max_val=100,
                title="% of the minimum order value to round up order",
                parent_input_name=self.spot_master_name,
                other_schema_values={
                    "grid_columns": 4,
                    "description": "For example if the min value to open a order is "
                    "10 USDT and you have this setting to 40. It will round up orders"
                    " with value bigger than 4 USDT up to 10 USDT.",
                },
            )

    async def init_plot_portfolio(self) -> None:
        self.enable_plot_portfolio_p = await user_inputs.user_input(
            self.ctx,
            "plot_portfolio_p",
            "boolean",
            def_val=True,
            title="Plot portfolio in %",
            show_in_summary=False,
            show_in_optimizer=False,
            parent_input_name=self.plot_settings_name,
        )
        self.enable_plot_portfolio_ref = await user_inputs.user_input(
            self.ctx,
            "plot_portfolio_ref",
            "boolean",
            def_val=True,
            title=f"Plot portfolio in {self.ref_market}",
            show_in_summary=False,
            show_in_optimizer=False,
            parent_input_name=self.plot_settings_name,
        )

    async def plot_portfolio(self) -> None:
        if plotting:
            if self.enable_plot_portfolio_ref or self.enable_plot_portfolio_p:
                key = "b-" if self.ctx.exchange_manager.is_backtesting else "l-"
                if self.enable_plot_portfolio_ref:
                    for coin, _portfolio in self.target_portfolio.items():
                        value_key = key + "cb-" + coin
                        await self.ctx.set_cached_value(
                            value=float(_portfolio.current_value), value_key=value_key
                        )
                        await plotting.plot(
                            self.ctx,
                            f"Current {coin} holdings (in {self.ref_market})",
                            cache_value=value_key,
                            chart="sub-chart",
                            color="blue",
                            shift_to_open_candle_time=False,
                            mode="markers",
                        )
                if self.enable_plot_portfolio_p:
                    for coin, _portfolio in self.target_portfolio.items():
                        value_key = key + "cp-" + coin
                        await self.ctx.set_cached_value(
                            value=float(_portfolio.current_percent * 100),
                            value_key=value_key,
                        )
                        await plotting.plot(
                            self.ctx,
                            f"Current {coin} holdings (in %)",
                            cache_value=value_key,
                            chart="sub-chart",
                            color="blue",
                            shift_to_open_candle_time=False,
                            mode="markers",
                        )

    def _try_converting_with_multiple_pairs(self, currency, quantity):
        # try with two pairs
        # for example: BTC/ETH      ->    BTC/USDT
        # first covert ETH -> BTC and then BTC -> USDT
        for symbol in symbol_data.get_config_symbols(
            self.portfolio_manager.exchange_manager.config, True
        ):
            if symbol.startswith(currency):
                first_ref_market = symbol_util.parse_symbol(symbol).quote
                second_symbol = (
                    f"{first_ref_market}/{self.portfolio_manager.reference_market}"
                )
                if (
                    all(
                        self.portfolio_manager.exchange_manager.symbol_exists(s)
                        for s in (symbol, second_symbol)
                    )
                    and currency not in self.missing_currency_data_in_exchange
                ):
                    if first_ref_market_value := (
                        self.convert_currency_value_using_last_prices(
                            quantity, currency, first_ref_market
                        )
                    ):
                        if ref_market_value := (
                            self.convert_currency_value_using_last_prices(
                                first_ref_market_value,
                                first_ref_market,
                                self.portfolio_manager.reference_market,
                            )
                        ):
                            return ref_market_value
