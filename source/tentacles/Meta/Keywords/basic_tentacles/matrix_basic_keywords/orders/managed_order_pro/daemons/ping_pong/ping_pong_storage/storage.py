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

import asyncio
import octobot_services.interfaces.util as interfaces_util
import octobot_tentacles_manager.api as tentacles_manager_api
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.daemons.ping_pong.ping_pong_constants as ping_pong_constants
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.daemons.ping_pong.ping_pong_storage.group as ping_pong_group
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.daemons.ping_pong.ping_pong_storage.element as element

RETRY_GET_ENTRY_ORDER_ATTEMPTS_COUNT: int = 20
RETRY_GET_ENTRY_ORDER_WAITING_TIME: int = 5


def get_all_ping_pong_data_as_dict(exchange_manager) -> dict:
    ping_pong_storage: PingPongStorage = get_ping_pong_storage(exchange_manager)
    if ping_pong_storage:
        return {
            "exchange_name": exchange_manager.exchange_name,
            "data": ping_pong_storage.to_dict(),
        }
    else:
        return {}


def reset_all_ping_pong_data(exchange_manager):
    ping_pong_storage: PingPongStorage = get_ping_pong_storage(exchange_manager)
    if ping_pong_storage:
        ping_pong_storage.reset_ping_pong_storage()
    else:
        raise RuntimeError(
            "Failed to reset ping pong storage. Storage not initialized yet"
        )


async def init_ping_pong_storage(exchange_manager) -> None:
    trading_mode = exchange_manager.trading_modes[0]
    trading_mode.ping_pong_storage: PingPongStorage = PingPongStorage(exchange_manager)
    if not exchange_manager.is_backtesting:
        await trading_mode.ping_pong_storage.restore_ping_pong_storage()


def get_ping_pong_storage(exchange_manager):
    ping_pong_storage: PingPongStorage = exchange_manager.trading_modes[
        0
    ].ping_pong_storage
    return ping_pong_storage


class PingPongStorage:
    ping_pong_storage: dict = {}
    ping_pong_info_storage: dict = ping_pong_constants.PingPongConstants.START_INFO_DATA

    def __init__(self, exchange_manager):
        self.exchange_manager = exchange_manager

    def set_ping_pong_data(
        self,
        group_key: str,
        order_group_id: str,
        created_orders: list,
        calculated_entries: list,
    ):
        group_key_str = str(group_key)
        if group_key_str not in self.ping_pong_storage:
            self.ping_pong_storage[group_key_str] = {}
        if order_group_id in self.ping_pong_storage[group_key_str]:
            raise RuntimeError(
                "Failed to create order group as the order group id already exists"
            )
        self.ping_pong_storage[group_key_str][
            order_group_id
        ] = ping_pong_group.PingPongGroupData(
            ping_pong_info_storage=self,
            entry_orders=created_orders,
            calculated_entries=calculated_entries,
            order_group_id=order_group_id,
            group_key=group_key_str,
        )
        if not self.exchange_manager.is_backtesting:
            self.store_ping_pong_storage()

    # def log_replaced_entry_order(
    #     self,
    #     any_past_order_id: str,
    #     recreated_entry_order,
    # ):
    #     group_data, order_info = self.get_ping_pong_data_by_any_order_id(
    #         any_past_order_id
    #     )
    #     group_data.log_replaced_entry_order(
    #         self,
    #         grid_id=order_info[PingPongOrderToOrderGroupIdConstants.GRID_ID],
    #         recreated_entry_order=recreated_entry_order,
    #     )

    # def get_ping_pong_data_by_any_order_id(
    #     self, any_past_order_id: str
    # ) -> typing.Tuple[PingPongGroupData, dict]:
    #     order_info = self.get_order_to_order_group_id_info(any_past_order_id)
    #     return (
    #         self.get_ping_pong_data(
    #             group_key=order_info[PingPongOrderToOrderGroupIdConstants.GROUP_KEY],
    #             order_group_id=order_info[
    #                 PingPongOrderToOrderGroupIdConstants.ORDER_GROUP_ID
    #             ],
    #         ),
    #         order_info,
    #     )

    def get_ping_pong_data(
        self, group_key: str, order_group_id: str
    ) -> ping_pong_group.PingPongGroupData:
        return self.ping_pong_storage[group_key][order_group_id]

    def get_single_data_if_enabled(
        self, group_key: str, order_group_id: str, grid_id: str
    ) -> element.PingPongSingleData or None:
        group_data: ping_pong_group.PingPongGroupData = self.get_ping_pong_data(
            group_key=group_key, order_group_id=order_group_id
        )
        single_data: element.PingPongSingleData = group_data.get_grid_data(grid_id)
        if single_data.enabled and single_data.original_orders is not None:
            return single_data
        return None

    async def get_entry_order(
        self,
        triggered_order: dict,
        group_key: str,
        order_group_id: str,
        grid_id: str,
        retry_counter: int,
    ) -> element.PingPongSingleData or None:
        try:
            return self.get_single_data_if_enabled(
                group_key=group_key,
                order_group_id=order_group_id,
                grid_id=grid_id,
            )
        except Exception as error:
            if (
                retry_counter <= RETRY_GET_ENTRY_ORDER_ATTEMPTS_COUNT
                and not self.exchange_manager.is_backtesting
            ):
                retry_counter += 1
                await asyncio.sleep(RETRY_GET_ENTRY_ORDER_WAITING_TIME)
                return await self.get_entry_order(
                    triggered_order=triggered_order,
                    group_key=group_key,
                    order_group_id=order_group_id,
                    grid_id=grid_id,
                    retry_counter=retry_counter,
                )
            raise RuntimeError(
                f"Ping pong failed. Failed to get entry order. Entry id: g{group_key}-"
                f"og{order_group_id}-o{grid_id} / take profit: {triggered_order}"
            ) from error

    def to_dict(self):
        storage_dict = {}
        for (
            order_group_instance_id,
            order_group_instance,
        ) in self.ping_pong_storage.items():
            if order_group_instance_id not in storage_dict:
                storage_dict[order_group_instance_id] = {}
            for order_group_id, order_group in order_group_instance.items():
                storage_dict[order_group_instance_id][order_group_id] = (
                    order_group.to_dict() if order_group else {}
                )
        return storage_dict

    def generate_next_order_group_id(self):
        self.ping_pong_info_storage[
            ping_pong_constants.PingPongConstants.LAST_ORDER_CHAIN_ID
        ] += 1
        return str(
            self.ping_pong_info_storage[
                ping_pong_constants.PingPongConstants.LAST_ORDER_CHAIN_ID
            ]
        )

    async def restore_ping_pong_storage(self):
        orders_manager = self.exchange_manager.exchange_personal_data.orders_manager
        if not (
            orders_manager.are_exchange_orders_initialized
            and orders_manager.is_initialized
        ):
            await asyncio.sleep(5)
            return await self.restore_ping_pong_storage()
        storage_file_content = _restore_ping_pong_storage() or {}
        self.ping_pong_info_storage = storage_file_content.get(
            ping_pong_constants.PingPongConstants.PING_PONG_INFO_STORAGE,
            ping_pong_constants.PingPongConstants.START_INFO_DATA,
        )
        await self._restore_from_raw(
            storage_file_content.get(
                ping_pong_constants.PingPongConstants.PING_PONG_STORAGE, {}
            )
        )
        # store updated storage
        self.store_ping_pong_storage()

    async def _restore_from_raw(self, raw_ping_pong_storage):
        self.ping_pong_storage = {}
        for group_key, group in raw_ping_pong_storage.items():
            if group_key not in self.ping_pong_storage:
                self.ping_pong_storage[group_key] = {}
            for order_group_id, raw_group_instance in group.items():
                restored_group: ping_pong_group.PingPongGroupData = (
                    ping_pong_group.PingPongGroupData(
                        ping_pong_info_storage=self,
                        order_group_id=order_group_id,
                        group_key=group_key,
                        init_only=True,
                    )
                )
                await restored_group.restore_from_raw(raw_group_instance)
                self.ping_pong_storage[group_key][order_group_id] = restored_group

    def store_ping_pong_storage(self):
        storage_dict = self.to_dict()
        self._store_ping_pong_storage(storage_dict)

    def _store_ping_pong_storage(self, ping_pong_storage_dict: dict = None):
        storage_file_content = {
            ping_pong_constants.PingPongConstants.PING_PONG_INFO_STORAGE: self.ping_pong_info_storage,
            ping_pong_constants.PingPongConstants.PING_PONG_STORAGE: ping_pong_storage_dict,
        }
        _store_ping_pong_storage(storage_file_content)

    def reset_ping_pong_storage(self):
        self.ping_pong_storage = {}
        self.store_ping_pong_storage()

    @staticmethod
    def get_name():
        return "PingPongStorage"


def _restore_ping_pong_storage():
    return (
        tentacles_manager_api.get_tentacle_config(
            interfaces_util.get_edited_tentacles_config(),
            PingPongStorage,
        )
        or {}
    )


def _store_ping_pong_storage(ping_pong_storage):
    try:
        tentacles_manager_api.update_tentacle_config(
            interfaces_util.get_edited_tentacles_config(),
            PingPongStorage,
            ping_pong_storage,
            keep_existing=False,
        )
    except TypeError:
        tentacles_manager_api.update_tentacle_config(
            interfaces_util.get_edited_tentacles_config(),
            PingPongStorage,
            ping_pong_storage,
        )
