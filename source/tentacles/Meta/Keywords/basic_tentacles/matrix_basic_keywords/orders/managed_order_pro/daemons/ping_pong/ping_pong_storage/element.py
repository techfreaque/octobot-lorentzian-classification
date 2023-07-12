# a42.ch CONFIDENTIAL
# __________________
#
#  [2021] - [∞] a42.ch Incorporated
#  All Rights Reserved.
#
# NOTICE:  All information contained herein is, and remains
# the property of a42.ch Incorporated and its suppliers,
# if any.  The intellectual and technical concepts contained
# herein are proprietary to a42.ch Incorporated
# and its suppliers and may be covered by U.S. and Foreign Patents,
# patents in process, and are protected by trade secret or copyright law.
# Dissemination of this information or reproduction of this material
# is strictly forbidden unless prior written permission is obtained
# from a42.ch Incorporated.
#
# If you want to use any code for commercial purposes,
# or you want your own custom solution,
# please contact me at max@a42.ch

import typing
import octobot_trading.enums as trading_enums
import octobot_commons.logging.logging_util as logging_util
from octobot_trading.personal_data.orders.order import Order
from octobot_trading.personal_data.orders.orders_manager import OrdersManager
from tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords import matrix_enums
from tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.matrix_enums import (
    PriceDataSources,
)
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.tools.utilities as utilities
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.daemons.ping_pong.ping_pong_constants as ping_pong_constants
import tentacles.Meta.Keywords.scripting_library.orders.order_types.create_order as create_order


class PingPongSingleData:
    grid_id: str = None
    calculated_entry: float = None
    entry_counter: int = None
    original_orders = None
    all_recreated_entry_orders: list = None
    last_order = None
    is_first_entry: bool = None
    ping_pong_active: bool = None
    enabled: bool = None

    order_group_id: str = None
    group_key: str = None

    def __init__(
        self,
        ping_pong_storage,
        grid_id: str,
        order_group_id: str,
        group_key: str,
        calculated_entry: float,
        entry_order=None,
        init_only: bool = False,
    ):
        self.enabled = True
        self.grid_id = grid_id
        self.ping_pong_storage = ping_pong_storage
        self.order_group_id = order_group_id
        self.group_key = group_key
        self.calculated_entry = float(str(calculated_entry))
        self.all_recreated_entry_orders = []
        if not init_only:
            self.entry_counter = 1 if entry_order else 0
            self.is_first_entry = True
            self.last_order = self.original_orders
            try:
                self.ping_pong_active = bool(
                    entry_order.status != trading_enums.OrderStatus.REJECTED
                )
                if self.ping_pong_active:
                    self.original_orders = self._format_entry_order(entry_order)
            except AttributeError:
                t = 1
                pass

    def log_replaced_entry_order(
        self,
        recreated_entry_order,
    ) -> typing.List[str]:
        self.is_first_entry: bool = False
        self.last_order = self._format_entry_order(recreated_entry_order)
        self.all_recreated_entry_orders.append(self.last_order)
        if not self.ping_pong_storage.exchange_manager.is_backtesting:
            try:
                self.ping_pong_storage.store_ping_pong_storage()
            except Exception as error:
                logging_util.get_logger("PingPongStorage").exception(
                    error, True, "Failed to permanently store ping pong storage"
                )

    def _format_entry_order(self, entry_order):
        if not entry_order:
            return {ping_pong_constants.PingPongSingleDataColumns.ENTRY_ORDER: {}}
        if isinstance(entry_order, dict):
            return {
                ping_pong_constants.PingPongSingleDataColumns.ENTRY_ORDER: entry_order
            }
        return {
            ping_pong_constants.PingPongSingleDataColumns.EXIT_ORDERS: [
                (exit_order if exit_order else {})
                for exit_order in entry_order.chained_orders
            ],
            ping_pong_constants.PingPongSingleDataColumns.ENTRY_ORDER: entry_order,
        }

    async def restore_from_raw(self, raw_grid):
        orders_manager: OrdersManager = (
            self.ping_pong_storage.exchange_manager.exchange_personal_data.orders_manager
        )
        self.last_order = raw_grid[
            ping_pong_constants.PingPongSingleDataColumns.LAST_ORDER
        ]
        self.ping_pong_active = raw_grid[
            ping_pong_constants.PingPongSingleDataColumns.PING_PONG_ACTIVE
        ]
        self.entry_counter = raw_grid[
            ping_pong_constants.PingPongSingleDataColumns.ENTRY_COUNTER
        ]
        self.original_orders = raw_grid[
            ping_pong_constants.PingPongSingleDataColumns.ORIGINAL_ENTRY_ORDER
        ]
        self.is_first_entry = raw_grid[
            ping_pong_constants.PingPongSingleDataColumns.IS_FIRST_ENTRY
        ]
        self.all_recreated_entry_orders = raw_grid[
            ping_pong_constants.PingPongSingleDataColumns.ALL_RECREATED_ENTRY_ORDERS
        ]

        if self.ping_pong_active:
            if (
                self.last_order[
                    ping_pong_constants.PingPongSingleDataColumns.ENTRY_ORDER
                ]["status"]
                == PriceDataSources.OPEN.value
            ):
                try:
                    last_entry: Order = orders_manager.get_open_orders(
                        symbol=self.last_order["entry_orders"]["symbol"],
                        tag=self.last_order["entry_orders"]["tag"],
                    )[0]
                    take_profit_tag = None
                    take_profit_price = None
                    stop_loss_tag = None
                    stop_loss_price = None
                    # for exit_order in self.last_order[
                    #     ping_pong_constants.PingPongSingleDataColumns.EXIT_ORDERS
                    # ]:
                    #     if is_take_profit(exit_order["type"]):
                    #         take_profit_tag = exit_order["tag"]
                    #         take_profit_price = decimal.Decimal(
                    #             str(exit_order["price"])
                    #         )
                    #     elif is_stop_loss(exit_order["type"]):
                    #         stop_loss_tag = exit_order["tag"]
                    #         stop_loss_price = decimal.Decimal(str(exit_order["price"]))
                    # await self.recreate_chained_exits(
                    #     entry_order=last_entry,
                    #     take_profit_tag=take_profit_tag,
                    #     take_profit_price=take_profit_price,
                    #     stop_loss_tag=stop_loss_tag,
                    #     stop_loss_price=stop_loss_price,
                    # )
                    self.last_order = self._format_entry_order(last_entry)
                except IndexError:
                    self.ping_pong_active = False
                    self.last_order["entry_orders"]["status"] = "closed"
            else:
                try:
                    last_exits = []
                    for order in self.last_order["exit_orders"]:
                        last_exits += orders_manager.get_open_orders(
                            symbol=order["symbol"],
                            tag=order["tag"],
                        )
                    self.last_order["exit_orders"] = last_exits
                except IndexError:
                    self.ping_pong_active = False
                    for order in self.last_order["exit_orders"].values():
                        order["status"] = "closed"

    async def recreate_chained_exits(
        self,
        entry_order,
        stop_loss_tag,
        stop_loss_price,
        take_profit_tag,
        take_profit_price,
    ):
        fees_currency_side, symbol_market = utilities.get_pre_order_data(
            self.ping_pong_storage.exchange_manager, entry_order.symbol
        )
        await create_order.bundle_stop_loss_and_take_profit(
            context=utilities.get_nano_context(
                exchange_manager=self.ping_pong_storage.exchange_manager,
                symbol=entry_order.symbol,
            ),
            symbol_market=symbol_market,
            fees_currency_side=fees_currency_side,
            order=entry_order,
            quantity=entry_order.origin_quantity,
            main_order_group=entry_order.order_group,
            stop_loss_tag=stop_loss_tag,
            stop_loss_type=None,
            stop_loss_price=stop_loss_price,
            stop_loss_group=None,
            take_profit_tag=take_profit_tag,
            take_profit_type=None,
            take_profit_price=take_profit_price,
            take_profit_group=None,
            order_pf_percent=None,
            order_position_percent=None,
        )
        return entry_order.chained_orders

    def get_to_replace_order_details(self):
        self.entry_counter += 1
        tag_suffix = f"{matrix_enums.TAG_SEPERATOR}{self.entry_counter}"
        entry_order = self.original_orders[
            ping_pong_constants.PingPongSingleDataColumns.ENTRY_ORDER
        ]
        if isinstance(entry_order, dict):
            data = {
                ping_pong_constants.PingPongOrderColumns.SIDE.value: entry_order[
                    "side"
                ],
                ping_pong_constants.PingPongOrderColumns.AMOUNT.value: entry_order[
                    "amount"
                ],
                ping_pong_constants.PingPongOrderColumns.ENTRY_PRICE.value: self.calculated_entry,
                ping_pong_constants.PingPongOrderColumns.ENTRY_TAG.value: (
                    entry_order["tag"] + tag_suffix
                ),
            }
        else:
            data = {
                ping_pong_constants.PingPongOrderColumns.SIDE.value: entry_order.side.value,
                ping_pong_constants.PingPongOrderColumns.AMOUNT.value: entry_order.origin_quantity,
                ping_pong_constants.PingPongOrderColumns.ENTRY_PRICE.value: self.calculated_entry,
                ping_pong_constants.PingPongOrderColumns.ENTRY_TAG.value: (
                    entry_order.tag + tag_suffix
                ),
            }
        exit_orders = self.original_orders[
            ping_pong_constants.PingPongSingleDataColumns.EXIT_ORDERS
        ]
        for order in exit_orders:
            if isinstance(order, dict):
                if is_take_profit(order["type"]):
                    data[
                        ping_pong_constants.PingPongOrderColumns.TAKE_PROFIT_PRICE.value
                    ] = order["price"]
                    data[
                        ping_pong_constants.PingPongOrderColumns.TAKE_PROFIT_TAG.value
                    ] = (order["tag"] + tag_suffix)
                elif is_stop_loss(order["type"]):
                    data[
                        ping_pong_constants.PingPongOrderColumns.STOP_LOSS_PRICE.value
                    ] = order["price"]
                    data[
                        ping_pong_constants.PingPongOrderColumns.STOP_LOSS_TAG.value
                    ] = (order["tag"] + tag_suffix)
            else:
                if is_take_profit(order.order_type):
                    data[
                        ping_pong_constants.PingPongOrderColumns.TAKE_PROFIT_PRICE.value
                    ] = order.origin_price
                    data[
                        ping_pong_constants.PingPongOrderColumns.TAKE_PROFIT_TAG.value
                    ] = (order.tag + tag_suffix)
                elif is_stop_loss(order.order_type):
                    data[
                        ping_pong_constants.PingPongOrderColumns.STOP_LOSS_PRICE.value
                    ] = (order.origin_stop_price or order.origin_price)
                    data[
                        ping_pong_constants.PingPongOrderColumns.STOP_LOSS_TAG.value
                    ] = (order.tag + tag_suffix)
        return data

    def get_last_entry_order(self):
        return self.last_order

    def get_calculated_entry(self):
        return self.calculated_entry

    def to_dict(self):
        return {
            ping_pong_constants.PingPongSingleDataColumns.GRID_ID: self.grid_id,
            ping_pong_constants.PingPongSingleDataColumns.CALCULATED_ENTRY: self.calculated_entry,
            ping_pong_constants.PingPongSingleDataColumns.ENTRY_COUNTER: self.entry_counter,
            ping_pong_constants.PingPongSingleDataColumns.ORIGINAL_ENTRY_ORDER: convert_order_object_to_dict(
                self.original_orders
            ),
            ping_pong_constants.PingPongSingleDataColumns.ALL_RECREATED_ENTRY_ORDERS: [
                convert_order_object_to_dict(recreated_order)
                for recreated_order in self.all_recreated_entry_orders
            ],
            ping_pong_constants.PingPongSingleDataColumns.LAST_ORDER: convert_order_object_to_dict(
                self.last_order
            ),
            ping_pong_constants.PingPongSingleDataColumns.IS_FIRST_ENTRY: self.is_first_entry,
            ping_pong_constants.PingPongSingleDataColumns.PING_PONG_ACTIVE: self.ping_pong_active,
        }


def convert_order_object_to_dict(orders_dict: dict):
    if not orders_dict or not orders_dict.get("entry_orders"):
        return {
            ping_pong_constants.PingPongSingleDataColumns.ENTRY_ORDER: {},
            ping_pong_constants.PingPongSingleDataColumns.EXIT_ORDERS: {},
        }
    data = {}
    if isinstance(orders_dict["entry_orders"], dict):
        data[ping_pong_constants.PingPongSingleDataColumns.ENTRY_ORDER] = orders_dict[
            "entry_orders"
        ]
    else:
        data[ping_pong_constants.PingPongSingleDataColumns.ENTRY_ORDER] = order_to_dict(
            orders_dict["entry_orders"]
        )
    data[ping_pong_constants.PingPongSingleDataColumns.EXIT_ORDERS] = []

    for order in orders_dict.get("exit_orders", []):
        if isinstance(order, dict):
            data[ping_pong_constants.PingPongSingleDataColumns.EXIT_ORDERS].append(
                order
            )
        else:
            data[ping_pong_constants.PingPongSingleDataColumns.EXIT_ORDERS].append(
                order_to_dict(order)
            )
    return data


def is_stop_loss(order_type: str):
    return order_type in (
        trading_enums.TraderOrderType.STOP_LOSS,
        trading_enums.TraderOrderType.STOP_LOSS_LIMIT,
        trading_enums.TraderOrderType.STOP_LOSS.value,
        trading_enums.TraderOrderType.STOP_LOSS_LIMIT.value,
    )


def is_take_profit(order_type: str):
    return order_type in (
        trading_enums.TraderOrderType.SELL_LIMIT,
        trading_enums.TraderOrderType.BUY_LIMIT,
        trading_enums.TraderOrderType.SELL_LIMIT.value,
        trading_enums.TraderOrderType.BUY_LIMIT.value,
        trading_enums.TradeOrderType.LIMIT.value,
        trading_enums.TradeOrderType.LIMIT,
    )


def order_to_dict(order):
    order_dict = order.to_dict()
    fees = order_dict[trading_enums.ExchangeConstantsOrderColumns.FEE.value]
    if fees:
        fees[trading_enums.ExchangeConstantsOrderColumns.COST.value] = float(
            str(fees.get(trading_enums.ExchangeConstantsOrderColumns.COST.value) or 0)
        )
    order_dict[trading_enums.ExchangeConstantsOrderColumns.PRICE.value] = float(
        str(order_dict[trading_enums.ExchangeConstantsOrderColumns.PRICE.value])
    )
    order_dict[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value] = float(
        str(order_dict[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value])
    )
    order_dict[trading_enums.ExchangeConstantsOrderColumns.COST.value] = float(
        str(order_dict[trading_enums.ExchangeConstantsOrderColumns.COST.value])
    )
    order_dict[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value] = float(
        str(order_dict[trading_enums.ExchangeConstantsOrderColumns.AMOUNT.value])
    )
    order_dict[trading_enums.ExchangeConstantsOrderColumns.FILLED.value] = float(
        str(order_dict[trading_enums.ExchangeConstantsOrderColumns.FILLED.value])
    )
    return order_dict
