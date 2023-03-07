import decimal
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.basic_modes.spot_master.spot_master_enums as spot_master_enums


class TargetAsset:
    should_change: bool = False
    change_side: str = None
    order_percent: decimal.Decimal = None
    order_value: decimal.Decimal = None
    order_amount: decimal.Decimal = None
    order_amount_available: decimal.Decimal = None
    available_amount: decimal.Decimal = 0
    order_execute_price: decimal.Decimal = None

    def __init__(
        self,
        total_value: decimal.Decimal,
        target_percent: decimal.Decimal,
        portfolio: dict,
        asset_value: decimal.Decimal,
        threshold_to_sell: decimal.Decimal,
        threshold_to_buy: decimal.Decimal,
        step_to_sell: decimal.Decimal,
        step_to_buy: decimal.Decimal,
        max_buffer_allocation: decimal.Decimal,
        min_buffer_allocation: decimal.Decimal,
        limit_buy_offset: decimal.Decimal,
        limit_sell_offset: decimal.Decimal,
        coin: str,
        ref_market: str,
        symbol: str,
        order_type: str,
        open_order_size: decimal.Decimal,
        is_ref_market: bool = False,
    ):
        self.portfolio: dict = portfolio
        self.open_order_size: decimal.Decimal = open_order_size
        self.coin: str = coin
        self.order_type: str = order_type
        self.max_buffer_allocation: decimal.Decimal = convert_percent_to_decimal(
            max_buffer_allocation
        )
        self.min_buffer_allocation: decimal.Decimal = convert_percent_to_decimal(
            min_buffer_allocation
        )
        self.symbol: str = symbol
        self.ref_market: str = ref_market
        self.is_ref_market: str = is_ref_market
        self.asset_value: decimal.Decimal = decimal.Decimal(str(asset_value))
        try:
            self.available_ref_market_in_currency: decimal.Decimal = (
                portfolio[ref_market].available / self.asset_value
            )
        except KeyError:
            self.available_ref_market_in_currency: decimal.Decimal = decimal.Decimal(
                "0"
            )
        try:
            self.current_amount = portfolio[coin].total
        except KeyError:
            self.current_amount = decimal.Decimal("0")
        self.portfolio_value: decimal.Decimal = total_value
        self.target_percent: decimal.Decimal = convert_percent_to_decimal(
            target_percent
        )
        self.target_value: decimal.Decimal = convert_percent_to_value(
            self.target_percent, self.portfolio_value
        )
        self.target_amount: decimal.Decimal = convert_value_to_amount(
            self.target_value, self.asset_value
        )
        self.current_value: decimal.Decimal = convert_amount_to_value(
            self.current_amount, self.asset_value
        )
        self.current_percent: decimal.Decimal = convert_value_to_percent(
            self.portfolio_value, self.current_value
        )
        self.current_amount_if_orders_filled: decimal.Decimal = (
            open_order_size + self.current_amount
        )
        self.current_value_if_orders_filled: decimal.Decimal = convert_amount_to_value(
            self.current_amount_if_orders_filled, self.asset_value
        )
        self.current_percent_if_orders_filled: decimal.Decimal = (
            convert_value_to_percent(
                self.portfolio_value, self.current_value_if_orders_filled
            )
        )

        self.min_buffer_distance_to_current_percent: decimal.Decimal = (
            self.target_percent
            - self.current_percent_if_orders_filled
            - self.min_buffer_allocation
        )
        self.max_buffer_distance_to_current_percent: decimal.Decimal = (
            self.target_percent
            + self.min_buffer_allocation
            - self.current_percent_if_orders_filled
        )
        self.difference_amount: decimal.Decimal = (
            self.target_amount - self.current_amount_if_orders_filled
        )
        self.difference_value: decimal.Decimal = (
            self.target_value - self.current_value_if_orders_filled
        )
        self.difference_percent: decimal.Decimal = (
            self.target_percent - self.current_percent_if_orders_filled
        )
        self.threshold_to_sell: decimal.Decimal = convert_percent_to_decimal(
            threshold_to_sell
        )
        self.threshold_to_buy: decimal.Decimal = convert_percent_to_decimal(
            threshold_to_buy
        )
        self.step_to_sell: decimal.Decimal = convert_percent_to_decimal(step_to_sell)
        self.step_to_buy: decimal.Decimal = convert_percent_to_decimal(step_to_buy)
        self.limit_buy_offset: decimal.Decimal = (
            convert_percent_to_decimal(limit_buy_offset) if limit_buy_offset else None
        )
        self.limit_sell_offset: decimal.Decimal = (
            convert_percent_to_decimal(limit_sell_offset) if limit_sell_offset else None
        )
        self.check_if_should_change()

    def check_if_should_change(self) -> None:
        if self.difference_percent < 0 and 0 >= self.open_order_size:
            if self.difference_percent < -(self.threshold_to_sell):
                self.prepare_sell_order()

        elif self.difference_percent > 0 and 0 <= self.open_order_size:
            if self.difference_percent > (self.threshold_to_buy):
                self.prepare_buy_order()

    def set_available_order_amount(self) -> None:
        self.order_amount_available = self.order_amount
        try:
            if self.change_side == "sell":
                self.available_amount = self.portfolio[self.coin].available
            else:
                self.available_amount = (
                    self.portfolio[self.ref_market].available / self.asset_value
                )
        except KeyError:
            self.available_amount = decimal.Decimal("0")
        if self.available_amount < self.order_amount:
            self.order_amount_available = self.available_amount

    def prepare_sell_order(self) -> None:
        self.should_change = True
        self.change_side = "sell"
        if -self.difference_percent > self.step_to_sell:
            if -self.max_buffer_distance_to_current_percent > self.step_to_sell:
                self.order_percent = -self.max_buffer_distance_to_current_percent
            else:
                self.order_percent = self.step_to_sell
        else:
            self.order_percent = -self.difference_percent
        self.order_value = convert_percent_to_value(
            self.order_percent, self.portfolio_value
        )
        self.order_amount = convert_value_to_amount(self.order_value, self.asset_value)
        if self.order_type == spot_master_enums.SpotMasterOrderTypes.LIMIT.value:
            self.order_execute_price = self.asset_value * (1 + self.limit_sell_offset)
        self.set_available_order_amount()

    def prepare_buy_order(self) -> None:
        self.should_change = True
        self.change_side = "buy"
        if self.difference_percent > self.step_to_buy:
            if self.min_buffer_distance_to_current_percent > self.step_to_buy:
                self.order_percent = self.min_buffer_distance_to_current_percent
            else:
                self.order_percent = self.step_to_buy
        else:
            self.order_percent = self.difference_percent
        self.order_value = convert_percent_to_value(
            self.order_percent, self.portfolio_value
        )
        self.order_amount = convert_value_to_amount(self.order_value, self.asset_value)
        if self.order_type == spot_master_enums.SpotMasterOrderTypes.LIMIT.value:
            self.order_execute_price = self.asset_value * (1 - self.limit_buy_offset)
        self.set_available_order_amount()


def convert_percent_to_decimal(percent) -> decimal.Decimal:
    return decimal.Decimal(str(percent)) / 100


def convert_percent_to_value(percent, value) -> decimal.Decimal:
    return percent * value


def convert_value_to_percent(total_value, value) -> decimal.Decimal:
    return value / total_value if value else decimal.Decimal("0")


def convert_value_to_amount(value, asset_value) -> decimal.Decimal:
    return value / asset_value


def convert_amount_to_value(amount, asset_value) -> decimal.Decimal:
    return amount * asset_value
