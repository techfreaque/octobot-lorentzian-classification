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

import decimal
import typing
import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.order_settings_group as order_settings_group
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_public_data as exchange_public_data


class ManagedOrdersSettings:
    def __init__(self):
        super().__init__()
        self.maker = None

        self.initialized: bool = False
        self.managed_order_active: bool = False

        self.market_fee: decimal.Decimal = None
        self.limit_fee: decimal.Decimal = None

        self.enable_alerts: bool = None
        self.recreate_exits: bool = None
        self.adapt_live_exits: bool = None
        self.amount_of_order_groups: int = None

        self.order_tag_prefix: str = "Managed order"
        self.user_input_name_prefix: str = "managed_order_"

        self.leverage: int = None

        self.order_groups: typing.Dict[
            order_settings_group.ManagedOrderSettingsOrderGroup
        ] = {}
        self.managed_order_id: int = None

    async def initialize(
        self,
        maker,
        parent_user_input_name: str,
        # managed_order_id: int = 1,
        order_tag_prefix: str = "Managed order",
        unique_name_prefix: str = "1",
        enable_position_size_settings: bool = True,
        enable_stop_loss_settings: bool = True,
        enable_trailing_stop_settings: bool = False,
        enable_take_profit_settings: bool = True,
    ):
        maker.initialized_managed_order_settings[unique_name_prefix] = self
        self.order_tag_prefix = order_tag_prefix
        # self.managed_order_id = managed_order_id
        fees = exchange_public_data.symbol_fees(maker.ctx)
        self.market_fee = decimal.Decimal(str(fees["taker"]))
        self.limit_fee = decimal.Decimal(str(fees["maker"]))
        self.amount_of_order_groups = await basic_keywords.user_input(
            maker.ctx,
            f"{unique_name_prefix}_order_groups",
            "int",
            1,
            min_val=1,
            title="Amount of entry / exit order groups",
            parent_input_name=parent_user_input_name,
        )
        self.order_groups = {}
        if maker.ctx.exchange_manager.is_future:
            self.leverage = await basic_keywords.user_input(
                maker.ctx,
                f"{unique_name_prefix}_leverage",
                "int",
                1,
                min_val=1,
                title="Leverage",
                parent_input_name=parent_user_input_name,
                other_schema_values={
                    "description": "Warning, leverage shouldnt be change when an position "
                    "is open on any pair that uses this order group",
                },
            )
            # TODO make sure pairs are not affecting each other
            # await basic_keywords.set_leverage(
            #         maker.ctx, self.leverage, symbol=maker.ctx.symbol
            #     )

        self.order_groups = {}
        for group_id in range(1, self.amount_of_order_groups + 1):
            group_user_input_name_prefix = f"{unique_name_prefix}_group_{group_id}"
            if self.amount_of_order_groups > 1:
                group_user_input_name = group_user_input_name_prefix
                await basic_keywords.user_input(
                    maker.ctx,
                    group_user_input_name,
                    "object",
                    None,
                    title=f"Entry / exit order group {group_id}",
                    parent_input_name=parent_user_input_name,
                    editor_options={
                        "grid_columns": 12,
                    },
                )
            else:
                group_user_input_name = parent_user_input_name

            this_group: order_settings_group.ManagedOrderSettingsOrderGroup = (
                order_settings_group.ManagedOrderSettingsOrderGroup(
                    order_manager_id=unique_name_prefix,
                    group_id=group_id,
                    order_tag_prefix=self.order_tag_prefix,
                )
            )
            self.order_groups[group_id] = this_group

            await this_group.entry.initialize_entry_settings(
                ctx=maker.ctx,
                parent_user_input_name=group_user_input_name,
                managed_order_group_id=this_group.order_manager_group_id,
            )
            await this_group.stop_loss.initialize_sl_settings(
                maker=maker,
                parent_user_input_name=group_user_input_name,
                managed_order_group_id=this_group.order_manager_group_id,
                enable_trailing_stop_settings=enable_trailing_stop_settings,
                enable_stop_loss_settings=enable_stop_loss_settings,
            )
            await this_group.take_profit.initialize_tp_settings(
                maker=maker,
                entry_type=this_group.entry.entry_type,
                sl_type=this_group.stop_loss.sl_type,
                parent_user_input_name=group_user_input_name,
                managed_order_group_id=this_group.order_manager_group_id,
                enable_take_profit_settings=enable_take_profit_settings,
            )
            if enable_position_size_settings:
                await this_group.position_size.initialize_position_size_settings(
                    ctx=maker.ctx,
                    sl_type=this_group.stop_loss.sl_type,
                    parent_user_input_name=group_user_input_name,
                    managed_order_group_id=this_group.order_manager_group_id,
                )
            if maker.trading_mode.enable_ping_pong:
                await this_group.ping_pong.initialize_ping_pong_settings(
                    maker=maker,
                    entry_type=this_group.entry.entry_type,
                    parent_user_input_name=group_user_input_name,
                    managed_order_group_id=this_group.order_manager_group_id,
                )

        # alerts
        self.enable_alerts = False
        # await basic_keywords.user_input(
        #     maker.ctx,
        #     f"{unique_name_prefix}_enable_detailed_trade_alerts",
        #     "boolean",
        #     True,
        #     title="enable detailed trade alerts",
        #     order=9999,
        #     parent_input_name=parent_user_input_name,
        #     show_in_optimizer=False,
        #     show_in_summary=False,
        # )
        self.managed_order_active = self.initialized = True

    async def initialize_exit_settings(self):
        pass
        # self.recreate_exits = await basic_keywords.user_input(
        #     self.maker.ctx,
        #     "Recreate exit orders on new entrys: When "
        #     "enabled exit orders will be replaced with "
        #     "new ones based on the current candle",
        #     "boolean",
        #     False,
        #     path=self.exit_path,
        #     parent_input_name=self.exit_setting_name,
        # )
        # self.adapt_live_exits = await basic_keywords.user_input(
        #     self.maker.ctx,
        #     "adapt_live_exits",
        #     "boolean",
        #     False,
        #     title="Adapt live exits based on filled price: When enabled this will place"
        #     " a entry with a stop loss based on candle close. When filled it will edit "
        #     "the stop loss based on filled price and place the take profit afterwards",
        #     path=self.exit_path,
        #     parent_input_name=self.exit_setting_name,
        # )

    # async def initialize_parent_input_or_path(
    #     self, maker, input_root_path, parent_user_input_name
    # ):
    #     # init parent sections or path
    #     self.maker.ctx = maker.maker.ctx
    #     self.maker = maker
    #     self.input_root_path = input_root_path
    #     self.parent_user_input_name = parent_user_input_name
    #     if self.parent_user_input_name:

    #     else:
    #         self.exit_path = self.input_root_path + "/Exit Settings"
    #         self.sl_path = self.exit_path + "/Stop Loss Settings"
    #         self.trail_sl_path = self.sl_path + "/Trailing Stop Settings"
    #         self.tp_path = self.exit_path + "/Take Profit Settings"
    #         self.position_size_path = self.input_root_path + "/Position Size Settings"
