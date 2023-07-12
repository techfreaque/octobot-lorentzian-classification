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
import octobot_commons.enums as commons_enums

import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.entry_types as entry_types
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.sl_settings as sl_settings
# import tentacles.Meta.Keywords.pro_tentacles.standalone_data_source.standalone_data_sources as standalone_data_sources


class ManagedOrderSettingsTPTypes:
    NO_TP = "no_tp"
    SINGLE_RISK_REWARD = "SINGLE_RISK_REWARD"
    SINGLE_PERCENT = "SINGLE_PERCENT"
    SINGLE_STATIC = "SINGLE_STATIC"
    SINGLE_INDICATOR = "SINGLE_INDICATOR"
    SCALED_RISK_REWARD = "SCALED_RISK_REWARD"
    SCALED_PERCENT = "SCALED_PERCENT"
    SCALED_STATIC = "SCALED_STATIC"

    NO_TP_DESCRIPTION = "dont use managed Take Profit"
    SINGLE_RISK_REWARD_DESCRIPTION = "take profit based on risk reward"
    SINGLE_PERCENT_DESCRIPTION = "take profit based on fixed percent from entry"
    SINGLE_STATIC_DESCRIPTION = "take profit based on static price"
    SINGLE_INDICATOR_DESCRIPTION = "take profit based on indicator"
    SCALED_RISK_REWARD_DESCRIPTION = "scaled take profit based on risk reward"
    SCALED_PERCENT_DESCRIPTION = "scaled take profit based on percent"
    SCALED_STATIC_DESCRIPTION = "spread limit exits based on a dynamic or static range"

    KEY_TO_DESCRIPTIONS = {
        NO_TP: NO_TP_DESCRIPTION,
        SINGLE_RISK_REWARD: SINGLE_RISK_REWARD_DESCRIPTION,
        SINGLE_PERCENT: SINGLE_PERCENT_DESCRIPTION,
        SINGLE_STATIC: SINGLE_STATIC_DESCRIPTION,
        SINGLE_INDICATOR: SINGLE_INDICATOR_DESCRIPTION,
        SCALED_RISK_REWARD: SCALED_RISK_REWARD_DESCRIPTION,
        SCALED_PERCENT: SCALED_PERCENT_DESCRIPTION,
        SCALED_STATIC: SCALED_STATIC_DESCRIPTION,
    }
    DESCRIPTIONS = [
        NO_TP_DESCRIPTION,
        SINGLE_RISK_REWARD_DESCRIPTION,
        SINGLE_PERCENT_DESCRIPTION,
        SINGLE_STATIC_DESCRIPTION,
        SINGLE_INDICATOR_DESCRIPTION
        # SCALED_RISK_REWARD_DESCRIPTION,
        # SCALED_PERCENT_DESCRIPTION,
        # SCALED_STATIC_DESCRIPTION,
    ]


class ManagedOrderSettingsTP:
    def __init__(self) -> None:
        self.tp_type: str = None
        self.tp_rr: decimal.Decimal = None
        self.tp_in_p: decimal.Decimal = None
        self.tp_in_d: decimal.Decimal = None
        self.rr_tp_min: decimal.Decimal = None
        self.rr_tp_max: decimal.Decimal = None
        self.rr_tp_order_count: int = None
        self.p_tp_order_count: int = None
        self.p_tp_min: decimal.Decimal = None
        self.p_tp_max: decimal.Decimal = None
        self.tp_min_p: decimal.Decimal = None
        self.tp_max_p: decimal.Decimal = None
        self.position_mode: str = None
        self.use_bundled_tp_orders: bool = None
        self.indicator: None
        self.tp_indicator_id: int = None

    async def initialize_tp_settings(
        self,
        maker,
        entry_type,
        sl_type,
        parent_user_input_name,
        managed_order_group_id: int,
        enable_take_profit_settings: bool = True,
    ):
        if not enable_take_profit_settings:
            self.tp_type = sl_settings.ManagedOrderSettingsSLTypes.NO_SL_DESCRIPTION
            return
        tp_setting_name = f"{managed_order_group_id}_tp_settings"
        tp_setting_name_prefix = f"{managed_order_group_id}"
        await basic_keywords.user_input(
            maker.ctx,
            tp_setting_name,
            "object",
            title="Take profit settings",
            def_val=None,
            parent_input_name=parent_user_input_name,
            editor_options={
                commons_enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                commons_enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                commons_enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
            },
        )

        self.use_bundled_tp_orders = True  # await basic_keywords.user_input(
        #     maker.ctx,
        #     "Bundle take profit order with entry order",
        #     "boolean",
        #     False,
        #
        #     parent_input_name=tp_setting_name,
        #     other_schema_values={
        #         "description": "When this option is enabled the TP will only get "
        #         "placed once the entry got filled (OctoBot must be running). "
        #         "Only on bybit futures it will already place the TP with the entry "
        #         "and OctoBot doesnt need to run for the SL"
        #     },
        #     show_in_optimizer=False,
        #     show_in_summary=False,
        # )
        if sl_type == sl_settings.ManagedOrderSettingsSLTypes.NO_SL_DESCRIPTION:
            # self.use_bundled_tp_orders = False
            tp_type_def_val = ManagedOrderSettingsTPTypes.SINGLE_PERCENT_DESCRIPTION
            if self.use_bundled_tp_orders:
                if entry_type in (
                    entry_types.ManagedOrderSettingsEntryTypes.SINGLE_LIMIT_IN_DESCRIPTION,
                    entry_types.ManagedOrderSettingsEntryTypes.SINGLE_MARKET_IN_DESCRIPTION,
                ):
                    tp_type_optinions = [
                        ManagedOrderSettingsTPTypes.NO_TP_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_PERCENT_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_STATIC_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_INDICATOR_DESCRIPTION,
                    ]
                else:
                    tp_type_optinions = [
                        ManagedOrderSettingsTPTypes.NO_TP_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_STATIC_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_PERCENT_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_INDICATOR_DESCRIPTION,
                    ]
            else:
                tp_type_optinions = [
                    ManagedOrderSettingsTPTypes.NO_TP_DESCRIPTION,
                    # ManagedOrderSettingsTPTypes.SINGLE_PERCENT_DESCRIPTION,
                    ManagedOrderSettingsTPTypes.SINGLE_STATIC_DESCRIPTION,
                    ManagedOrderSettingsTPTypes.SINGLE_INDICATOR_DESCRIPTION,
                    # ManagedOrderSettingsTPTypes.SCALED_PERCENT_DESCRIPTION,
                    # ManagedOrderSettingsTPTypes.SCALED_STATIC_DESCRIPTION,
                ]
        else:
            tp_type_def_val = ManagedOrderSettingsTPTypes.SINGLE_RISK_REWARD_DESCRIPTION
            if self.use_bundled_tp_orders:
                if entry_type in (
                    entry_types.ManagedOrderSettingsEntryTypes.SINGLE_LIMIT_IN_DESCRIPTION,
                    entry_types.ManagedOrderSettingsEntryTypes.SINGLE_MARKET_IN_DESCRIPTION,
                ):
                    tp_type_optinions = [
                        ManagedOrderSettingsTPTypes.NO_TP_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_RISK_REWARD_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_PERCENT_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_STATIC_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_INDICATOR_DESCRIPTION,
                    ]
                else:
                    tp_type_optinions = [
                        ManagedOrderSettingsTPTypes.NO_TP_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_RISK_REWARD_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_PERCENT_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_STATIC_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_INDICATOR_DESCRIPTION,
                    ]
            else:
                if entry_type in (
                    entry_types.ManagedOrderSettingsEntryTypes.SINGLE_LIMIT_IN_DESCRIPTION,
                    entry_types.ManagedOrderSettingsEntryTypes.SINGLE_MARKET_IN_DESCRIPTION,
                ):
                    tp_type_optinions = [
                        ManagedOrderSettingsTPTypes.NO_TP_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_RISK_REWARD_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_PERCENT_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_STATIC_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_INDICATOR_DESCRIPTION,
                    ]
                else:
                    tp_type_optinions = [
                        ManagedOrderSettingsTPTypes.NO_TP_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_STATIC_DESCRIPTION,
                        ManagedOrderSettingsTPTypes.SINGLE_INDICATOR_DESCRIPTION,
                    ]
        # TP
        self.tp_type = await basic_keywords.user_input(
            maker.ctx,
            f"{tp_setting_name_prefix}_take_profit_type",
            "options",
            tp_type_def_val,
            options=tp_type_optinions,
            title="Take profit type",
            parent_input_name=tp_setting_name,
        )
        # TP based on risk reward
        if self.tp_type == ManagedOrderSettingsTPTypes.SINGLE_RISK_REWARD_DESCRIPTION:
            self.tp_rr = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        maker.ctx,
                        f"{tp_setting_name_prefix}_tp_risk_reward_target",
                        "float",
                        2,
                        min_val=0,
                        title="TP Risk Reward target",
                        parent_input_name=tp_setting_name,
                    )
                )
            )
        # # TP based on indicator
        # elif self.tp_type == ManagedOrderSettingsTPTypes.SINGLE_INDICATOR_DESCRIPTION:
        #     self.tp_indicator_id = f"{managed_order_group_id}300"
        #     self.indicator = (
        #         await standalone_data_sources.activate_standalone_data_source(
        #             "Take profit based on indicator",
        #             parent_input_name=tp_setting_name,
        #             indicator_id=self.tp_indicator_id,
        #             maker=maker,
        #         )
        #     )
        #     self.tp_min_p = decimal.Decimal(
        #         str(
        #             await basic_keywords.user_input(
        #                 maker.ctx,
        #                 f"{tp_setting_name_prefix}_min_tp_in_%",
        #                 "float",
        #                 0.5,
        #                 min_val=0,
        #                 title="min take profit in %",
        #                 parent_input_name=tp_setting_name,
        #             )
        #         )
        #     )
        #     self.tp_max_p = decimal.Decimal(
        #         str(
        #             await basic_keywords.user_input(
        #                 maker.ctx,
        #                 f"{tp_setting_name_prefix}_max_tp_in_%",
        #                 "float",
        #                 10,
        #                 min_val=0,
        #                 title="max take profit in %",
        #                 parent_input_name=tp_setting_name,
        #             )
        #         )
        #     )

        # TP based on percent
        elif self.tp_type == ManagedOrderSettingsTPTypes.SINGLE_PERCENT_DESCRIPTION:
            self.tp_in_p = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        maker.ctx,
                        f"{tp_setting_name_prefix}_take_profit_in_percent",
                        "float",
                        2,
                        title="Take profit in %",
                        min_val=0,
                        parent_input_name=tp_setting_name,
                    )
                )
            )

        # single TP based on static price
        elif self.tp_type == ManagedOrderSettingsTPTypes.SINGLE_STATIC_DESCRIPTION:
            self.tp_in_d = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        maker.ctx,
                        f"{tp_setting_name_prefix}_take_profit_static_price",
                        "float",
                        None,
                        title="Take profit static price",
                        min_val=0,
                        parent_input_name=tp_setting_name,
                    )
                )
            )

        # scaled TP based on risk reward
        elif (
            self.tp_type == ManagedOrderSettingsTPTypes.SCALED_RISK_REWARD_DESCRIPTION
            and not self.use_bundled_tp_orders
        ):
            self.rr_tp_min = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        maker.ctx,
                        f"{tp_setting_name_prefix}_take_profit_min_risk_reward_target",
                        "float",
                        2,
                        min_val=0,
                        title="take profit min risk reward target",
                        parent_input_name=tp_setting_name,
                    )
                )
            )
            self.rr_tp_max = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        maker.ctx,
                        f"{tp_setting_name_prefix}_take_profit_max_risk_reward_target",
                        "float",
                        10,
                        min_val=0,
                        title="take profit max risk reward target",
                        parent_input_name=tp_setting_name,
                    )
                )
            )
            self.rr_tp_order_count = await basic_keywords.user_input(
                maker.ctx,
                f"{tp_setting_name_prefix}_take_profit_order_count",
                "int",
                10,
                min_val=2,
                title="take profit order count",
                parent_input_name=tp_setting_name,
            )

        # scaled TP based on percent
        elif (
            self.tp_type == ManagedOrderSettingsTPTypes.SCALED_PERCENT_DESCRIPTION
            and not self.use_bundled_tp_orders
        ):
            self.p_tp_min = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        maker.ctx,
                        f"{tp_setting_name_prefix}_scale_take_profit_from_%",
                        "float",
                        1,
                        min_val=0,
                        title="scale take profit from: (measured in %) ",
                        parent_input_name=tp_setting_name,
                    )
                )
            )
            self.p_tp_max = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        maker.ctx,
                        f"{tp_setting_name_prefix}_scale_take_profit_to_%",
                        "float",
                        50,
                        min_val=0,
                        title="scale take profit to: (measured in %",
                        parent_input_name=tp_setting_name,
                    )
                )
            )
            self.p_tp_order_count = await basic_keywords.user_input(
                maker.ctx,
                f"{tp_setting_name_prefix}_take_profit_order_count",
                "int",
                10,
                min_val=2,
                title="take profit order count",
                parent_input_name=tp_setting_name,
            )

        # grid sell based on percent
        elif (
            self.tp_type == ManagedOrderSettingsTPTypes.SCALED_STATIC_DESCRIPTION
            and not not self.use_bundled_tp_orders
        ):
            self.position_mode = await basic_keywords.user_input(
                maker.ctx,
                f"{tp_setting_name_prefix}_position_mode",
                "options",
                "long only",
                options=["long only", "short only", "both"],
                title="Position Mode",
                parent_input_name=tp_setting_name,
                other_schema_values={
                    "description": "When both: it will reach the maximum short "
                    "size at the top of the range, and the max long position at the"
                    " bottom. - "
                    "When short only: it will reach the maximum short size at the"
                    " top of the range, and will be in no position at the top"
                    " bottom. - "
                    "When long only: the max size is reached at the bottom and yo"
                },
            )
            self.p_tp_min = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        maker.ctx,
                        f"{tp_setting_name_prefix}_scale_sell_orders_from_price",
                        "float",
                        1,
                        min_val=0,
                        title="scale sell orders from price",
                        parent_input_name=tp_setting_name,
                    )
                )
            )
            self.p_tp_max = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        maker.ctx,
                        f"{tp_setting_name_prefix}_scale_sell_orders_to_price",
                        "float",
                        50,
                        min_val=0,
                        title="scale sell orders to price",
                        parent_input_name=tp_setting_name,
                    )
                )
            )
            self.p_tp_order_count = await basic_keywords.user_input(
                maker.ctx,
                f"{tp_setting_name_prefix}_take_profit_order_count",
                "int",
                10,
                min_val=2,
                title="take profit order count",
                parent_input_name=tp_setting_name,
            )
