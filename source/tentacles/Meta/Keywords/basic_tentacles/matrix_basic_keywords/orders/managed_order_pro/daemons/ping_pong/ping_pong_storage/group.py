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
from tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.daemons.ping_pong import (
    ping_pong_constants,
)
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.daemons.ping_pong.ping_pong_storage.element as element


class PingPongGroupData:
    group_data: typing.Dict[str, element.PingPongSingleData] = {}

    def __init__(
        self,
        ping_pong_info_storage,
        group_key: str,
        order_group_id: str,
        entry_orders: list = None,
        calculated_entries: list = None,
        init_only: bool = False,
    ):
        self.ping_pong_info_storage = ping_pong_info_storage
        self.order_group_id: str = order_group_id
        self.group_key: str = group_key
        if not init_only:
            for grid_id, order in enumerate(entry_orders):
                self.set_grid_data(
                    grid_id=str(grid_id),
                    order=order,
                    calculated_entry=calculated_entries[grid_id],
                )

    async def restore_from_raw(self, raw_group_instance) -> None:
        for grid_id, raw_grid in raw_group_instance.items():
            self.group_data[grid_id] = element.PingPongSingleData(
                ping_pong_storage=self.ping_pong_info_storage,
                grid_id=grid_id,
                calculated_entry=raw_grid[
                    ping_pong_constants.PingPongSingleDataColumns.CALCULATED_ENTRY
                ],
                order_group_id=self.order_group_id,
                group_key=self.group_key,
                init_only=True,
            )
            await self.group_data[grid_id].restore_from_raw(raw_grid)

    def set_grid_data(self, grid_id, order, calculated_entry) -> None:
        self.group_data[grid_id] = element.PingPongSingleData(
            ping_pong_storage=self.ping_pong_info_storage,
            grid_id=grid_id,
            entry_order=order,
            calculated_entry=calculated_entry,
            order_group_id=self.order_group_id,
            group_key=self.group_key,
        )

    def get_grid_data(self, grid_id) -> element.PingPongSingleData:
        return self.group_data[str(grid_id)]

    # def log_replaced_entry_order(
    #     self,
    #     grid_id: str,
    #     recreated_entry_order,
    # ):
    #     self.get_grid_data(grid_id).log_replaced_entry_order(recreated_entry_order)

    # def get_last_entry_order(self, grid_id) -> PingPongSingleData:
    #     return self.get_grid_data(grid_id).get_last_entry_order()

    # def get_single_data_if_enabled(self, grid_id) -> element.PingPongSingleData or None:
    #     single_data: element.PingPongSingleData = self.get_grid_data(grid_id)
    #     if (
    #         self.order_group_settings.ping_pong.ping_pong_mode_enabled
    #         and single_data.enabled
    #     ):
    #         return single_data
    #     return None

    # def get_original_calculated_entry_price(self, grid_id):
    #     return self.get_grid_data(grid_id).get_calculated_entry()

    def to_dict(self):
        grid_dict = {}
        for grid_id, this_group_data in self.group_data.items():
            grid_dict[grid_id] = this_group_data.to_dict()
        return grid_dict
