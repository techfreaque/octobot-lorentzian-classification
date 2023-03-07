import decimal
from math import ceil
import time
import typing

import octobot_commons.enums as commons_enums
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_commons.errors as commons_errors

import octobot_trading.api.portfolio as portfolio
import octobot_trading.enums as trading_enums
import octobot_trading.modes.script_keywords.context_management as context_management

import tentacles.Meta.Keywords.scripting_library.orders.cancelling as cancelling
import tentacles.Meta.Keywords.scripting_library.orders.order_types as order_types

import tentacles.Meta.Keywords.matrix_library.basic_tentacles.matrix_basic_keywords.data.public_exchange_data as public_exchange_data
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.basic_modes.spot_master.spot_master_enums as spot_master_enums
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.basic_modes.spot_master.spot_master_3000_trading_mode_settings as spot_master_3000_trading_mode_settings
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.basic_modes.spot_master.asset as asset


class SpotMaster3000Making(
    spot_master_3000_trading_mode_settings.SpotMaster3000ModeSettings
):
    target_settings: dict = {}
    coins_to_trade: list = []
    open_orders: list = []
    ctx: context_management.Context = None
    currencies_values: dict = {}
    target_portfolio: typing.Dict[str, asset.TargetAsset] = {}
    portfolio: dict = {}
    total_value: decimal.Decimal = None
    ref_market: str = None
    ref_market_asset: str = None
    orders_to_execute: typing.Dict[str, asset.TargetAsset] = []
    threshold_to_sell: float = None
    threshold_to_buy: float = None
    step_to_sell: float = None
    step_to_buy: float = None
    max_buffer_allocation: float = None
    min_buffer_allocation: float = None
    limit_buy_offset: float = None
    limit_sell_offset: float = None
    order_type: str = None
    spot_master_name = "spot_master_3000"
    enable_plot_portfolio_p: bool = None
    enable_plot_portfolio_ref: bool = None

    async def execute_rebalancing_strategy(
        self, ctx: context_management.Context
    ) -> None:
        self.ctx = None
        self.ctx = ctx
        try:
            await self.handle_trigger_time_frame()
        except commons_errors.ExecutionAborted:
            return
        await self.init_spot_master_settings(ctx)
        if self.initialize_portfolio_values():
            self.allow_trading_only_on_execution(ctx)
            await self.calculate_target_portfolio()
            if self.ctx.enable_trading:
                await self.execute_orders()
        await self.init_plot_settings()
        await self.init_plot_portfolio()
        if self.enable_plot:
            await self.plot_portfolio()
            try:
                import tentacles.Meta.Keywords.matrix_library.pro_tentacles.trade_analysis.trade_analysis_activation as trade_analysis_activation
            except (ImportError, ModuleNotFoundError):
                trade_analysis_activation = None

            if trade_analysis_activation:
                await trade_analysis_activation.handle_trade_analysis_for_current_candle(
                    ctx, self.plot_settings_name
                )

    async def execute_orders(self) -> None:
        for order_to_execute in self.orders_to_execute.values():
            if order_to_execute.symbol == self.ctx.symbol:
                # available_amount, amount = self.get_available_amount(order_to_execute)
                if (
                    self.order_type
                    == spot_master_enums.SpotMasterOrderTypes.LIMIT.value
                ):
                    if amount := self.round_up_order_amount_if_enabled(
                        available_amount=order_to_execute.available_amount,
                        order_amount=order_to_execute.order_amount_available,
                        order_price=order_to_execute.order_execute_price,
                        symbol=order_to_execute.symbol,
                        order_side=order_to_execute.change_side,
                    ):
                        await order_types.limit(
                            self.ctx,
                            side=order_to_execute.change_side,
                            amount=amount,
                            offset=f"@{order_to_execute.order_execute_price}",
                        )
                elif (
                    self.order_type
                    == spot_master_enums.SpotMasterOrderTypes.MARKET.value
                ):
                    if amount := self.round_up_order_amount_if_enabled(
                        available_amount=order_to_execute.available_amount,
                        order_amount=order_to_execute.order_amount_available,
                        order_price=order_to_execute.asset_value,
                        symbol=order_to_execute.symbol,
                        order_side=order_to_execute.change_side,
                    ):
                        await order_types.market(
                            self.ctx,
                            side=order_to_execute.change_side,
                            amount=amount,
                        )

    def initialize_portfolio_values(self) -> bool:
        self.portfolio = portfolio.get_portfolio(self.ctx.exchange_manager)
        self.total_value = (
            self.ctx.exchange_manager.exchange_personal_data.portfolio_manager.portfolio_value_holder.portfolio_current_value
        )
        if self.total_value == decimal.Decimal("0"):
            self.ctx.logger.debug(
                "Portfolio Value is not initialized or 0, "
                f"this {self.ctx.symbol} candle will be skipped. "
                "This is normal if OctoBot just started"
            )
            return False
        return True

    async def calculate_target_portfolio(self) -> None:
        self.ref_market = self.ctx.top_level_tentacle.config["trading"][
            "reference-market"
        ]
        self.target_portfolio = {}
        self.orders_to_execute = {}
        if self.ctx.enable_trading:
            await self.cancel_expired_orders()
        await self.load_orders()
        for coin, settings in self.target_settings.items():
            if not self.ctx.symbol.startswith(coin):
                continue
            available_symbols: list = self.get_available_symbols(coin)
            _asset: asset.TargetAsset = None
            if not available_symbols:
                if not (
                    _asset := self.calculate_reference_market_asset(settings, coin)
                ):
                    # should never happen
                    self.ctx.logger.error(f"No trading pair available for {coin}")
                    continue
            else:
                order_to_execute, _asset = await self.calculate_asset(
                    settings,
                    coin,
                    available_symbols,
                )
                if order_to_execute:
                    self.orders_to_execute[coin] = order_to_execute
            if _asset:
                self.target_portfolio[coin] = _asset

    async def calculate_asset(
        self, settings, coin, available_symbols
    ) -> asset.TargetAsset or None:
        """
        it computes the TargetAsset for all available symbols
        and pickes the one with most available percent of portfolio to execute trades on
        """
        potential_order: asset.TargetAsset = None
        _asset: asset.TargetAsset = None
        for symbol in available_symbols:
            parsed_symbol: str = symbol_util.parse_symbol(symbol)
            this_ref_market: str = parsed_symbol.quote
            converted_total_value: decimal.Decimal = None
            open_order_size: decimal.Decimal = decimal.Decimal("0")
            if this_ref_market != self.ref_market:
                conversion_symbol = f"{this_ref_market}/{self.ref_market}"
                conversion_symbol_inverse: list = f"{self.ref_market}/{this_ref_market}"
                conversion_value: float = None
                available_symbol = None
                for available_symbol in (conversion_symbol, conversion_symbol_inverse):
                    if value := await self.get_asset_value(available_symbol):
                        conversion_value = value
                        break
                if not conversion_value:
                    if self.ctx.exchange_manager.is_backtesting:
                        return None, None
                    raise RuntimeError(
                        f"Not able to determine value for {parsed_symbol.base} using "
                        f"{available_symbol} - this candle for {self.ctx.symbol} "
                        "will be skipped"
                    )
                if available_symbol == conversion_symbol:
                    converted_total_value = self.total_value / decimal.Decimal(
                        str(conversion_value)
                    )
                else:
                    converted_total_value = self.total_value * decimal.Decimal(
                        str(conversion_value)
                    )
            open_order_size = self.get_open_order_quantity(symbol)
            if not (asset_value := await self.get_asset_value(symbol)):
                if coin in self.ctx.symbol:
                    self.ctx.logger.debug(
                        f"Not able to determine asset value for {coin} with {symbol} "
                        f"- this candle for {self.ctx.symbol} will be skipped"
                    )
                return None, None
            _asset = asset.TargetAsset(
                total_value=converted_total_value or self.total_value,
                target_percent=settings["allocation"],
                portfolio=self.portfolio,
                asset_value=asset_value,
                threshold_to_sell=self.threshold_to_sell,
                threshold_to_buy=self.threshold_to_buy,
                step_to_sell=self.step_to_sell,
                step_to_buy=self.step_to_buy,
                max_buffer_allocation=self.max_buffer_allocation,
                min_buffer_allocation=self.min_buffer_allocation,
                is_ref_market=False,
                coin=coin,
                limit_buy_offset=self.limit_buy_offset,
                limit_sell_offset=self.limit_sell_offset,
                order_type=self.order_type,
                symbol=symbol,
                ref_market=this_ref_market,
                open_order_size=open_order_size,
            )
            if potential_order:
                # TODO use ref market that is closer to optimal %
                if _asset.change_side == "buy":
                    # use ref market with more available funds
                    if (
                        _asset.available_ref_market_in_currency
                        > potential_order.available_ref_market_in_currency
                    ):
                        potential_order = _asset
                # TODO use ref market that has more difference to optimal %
                elif _asset.change_side == "sell":
                    # use ref market with less available funds
                    if (
                        _asset.available_ref_market_in_currency
                        < potential_order.available_ref_market_in_currency
                    ):
                        potential_order = _asset
            else:
                potential_order = _asset
        _asset = potential_order or _asset
        if not (
            potential_order.should_change and potential_order.symbol == self.ctx.symbol
        ):
            potential_order = None
        return potential_order, _asset

    def calculate_reference_market_asset(
        self, settings, coin
    ) -> asset.TargetAsset or None:
        open_order_size: decimal.Decimal = decimal.Decimal("0")  # TODO
        if self.ref_market == coin:
            symbol: str = coin
            this_ref_market: str = coin
            asset_value: float = 1
            return asset.TargetAsset(
                total_value=self.total_value,
                target_percent=settings["allocation"],
                portfolio=self.portfolio,
                asset_value=asset_value,
                threshold_to_sell=self.threshold_to_sell,
                threshold_to_buy=self.threshold_to_buy,
                step_to_sell=self.step_to_sell,
                step_to_buy=self.step_to_buy,
                max_buffer_allocation=self.max_buffer_allocation,
                min_buffer_allocation=self.min_buffer_allocation,
                is_ref_market=True,
                coin=coin,
                limit_buy_offset=self.limit_buy_offset,
                limit_sell_offset=self.limit_sell_offset,
                order_type=self.order_type,
                symbol=symbol,
                ref_market=this_ref_market,
                open_order_size=open_order_size,
            )

    async def load_orders(self):
        self.open_orders = self.exchange_manager.exchange_personal_data.orders_manager.get_open_orders(
            # symbol=self.ctx.symbol
        )

    async def cancel_expired_orders(self):
        if spot_master_enums.SpotMasterOrderTypes.LIMIT.value == self.order_type:
            until = int(
                time.time()
                - (
                    commons_enums.TimeFramesMinutes[
                        commons_enums.TimeFrames(self.ctx.time_frame)
                    ]
                    * self.limit_max_age_in_bars
                    * 60
                )
            )
            try:
                await cancelling.cancel_orders(
                    self.ctx, symbol=self.ctx.symbol, until=until
                )
            except TypeError:
                # TODO remove
                self.ctx.logger.error(
                    "Not able to cancel epxired orders as this is currently not "
                    "possible on stock OctoBot. You need to manage order "
                    "cancelling by yourself"
                )

    def get_open_order_quantity(self, symbol: str):
        open_order_size: decimal.Decimal = decimal.Decimal("0")
        if self.open_orders:
            for order in self.open_orders:
                if order.currency in symbol:
                    if order.side == trading_enums.TradeOrderSide.BUY:
                        open_order_size += order.origin_quantity
                    else:
                        open_order_size -= order.origin_quantity
        return open_order_size

    async def get_asset_value(self, symbol: str) -> bool or float:
        try:
            return await public_exchange_data.get_current_candle(
                self, "close", symbol=symbol
            )
        except (ValueError, KeyError):
            if not self.ctx.exchange_manager.is_backtesting and self.ctx.enable_trading:
                self.ctx.logger.error(
                    f" Price missing for the candle, this is normal if "
                    "you just started octobot"
                    f"(time: {self.ctx.trigger_cache_timestamp}, "
                    f"{symbol}, {self.ctx.time_frame})"
                )
            return False

    def get_available_symbols(self, coin: str) -> list:
        return list(
            filter(lambda symbol: symbol.startswith(coin), self.available_symbols)
        )

    def round_up_order_amount_if_enabled(
        self,
        available_amount: decimal.Decimal,
        order_amount: decimal.Decimal,
        order_price: decimal.Decimal,
        symbol: str,
        order_side: str,
    ) -> decimal.Decimal:
        if self.round_orders:
            (
                min_value,
                fixed_min_value,
                minimum_amount,
            ) = self.get_rounded_min_amount_and_value(symbol, order_price)
            if (original_order_value := order_amount * order_price) <= fixed_min_value:
                if not self._check_if_available_funds(
                    available_amount,
                    minimum_amount,
                    symbol,
                    order_side,
                    order_price,
                    min_value,
                ) or self._round_down_order_amount(
                    min_value, original_order_value, symbol, order_side
                ):
                    return decimal.Decimal("0")
                return self._round_up_order_amount(
                    min_value, original_order_value, symbol, order_side, minimum_amount
                )
            # dont round
        return order_amount

    def get_rounded_min_amount_and_value(self, symbol, order_price):
        market_status = self.ctx.exchange_manager.exchange.get_market_status(
            symbol, with_fixer=False
        )
        min_value = decimal.Decimal(str(market_status["limits"]["cost"]["min"] or 0))
        minimum_amount = decimal.Decimal(
            str(
                float_round(
                    # add 10% to prevent rounding issue
                    (min_value / order_price) * decimal.Decimal(str(1.1)),
                    market_status["precision"]["amount"],
                )
            )
        )
        fixed_min_value = minimum_amount * order_price
        return min_value, fixed_min_value, minimum_amount

    def _check_if_available_funds(
        self,
        available_amount,
        minimum_amount,
        symbol,
        order_side,
        order_price,
        min_value,
    ):
        if available_amount < minimum_amount:
            # not enough funds
            self.ctx.logger.warning(
                f"Not enough available funds to open order ({symbol} | "
                f"{order_side} | available value: {available_amount*order_price} "
                f"{self.get_ref_market_from_symbol(symbol)} | required value: "
                f"{min_value} {self.get_ref_market_from_symbol(symbol)}) "
            )
            return False
        return True

    def _round_up_order_amount(
        self, min_value, original_order_value, symbol, order_side, minimum_amount
    ) -> decimal.Decimal:
        # round up
        self.ctx.logger.info(
            f"Rounding up the order value ({symbol} | {order_side} | order value: "
            f"{original_order_value} {self.get_ref_market_from_symbol(symbol)} | "
            f"rounded value: {min_value} {self.get_ref_market_from_symbol(symbol)}) "
        )
        return minimum_amount

    def _round_down_order_amount(
        self, min_value, original_order_value, symbol, order_side
    ) -> bool:
        if (
            round_orders_max_value := (
                decimal.Decimal(str(self.round_orders_max_value / 100)) * min_value
            )
        ) > original_order_value:
            # round down
            self.ctx.logger.warning(
                f"Order less then minimum value to round up ({symbol} | "
                f"{order_side} | order value: {original_order_value} | "
                f"min value to round up: {round_orders_max_value}) "
            )
            return True
        return False

    def get_ref_market_from_symbol(self, symbol) -> str:
        return symbol_util.parse_symbol(symbol).quote


def float_round(num, places=0, direction=ceil):
    return direction(num * (10**places)) / float(10**places)
