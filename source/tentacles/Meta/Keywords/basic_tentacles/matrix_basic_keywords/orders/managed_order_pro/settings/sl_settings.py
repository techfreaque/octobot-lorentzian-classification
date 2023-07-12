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

# import tentacles.Meta.Keywords.pro_tentacles.standalone_data_source.standalone_data_sources as standalone_data_sources


class ManagedOrderSettingsSLTypes:
    NO_SL = "no_sl"
    BASED_ON_LOW_HIGH = "based_on_low_high"
    BASED_ON_PERCENT_ENTRY = "based_on_percent"
    BASED_ON_PERCENT_PRICE = "based_on_percent_price"
    BASED_ON_STATIC_PRICE = "based_on_static_price"
    BASED_ON_ATR = "based_on_atr"
    BASED_ON_INDICATOR = "based_on_indicator"

    NO_SL_DESCRIPTION = "no SL"
    AT_LOW_HIGH_DESCRIPTION = "SL at the low/high"
    BASED_ON_PERCENT_ENTRY_DESCRIPTION = "SL based on % from the filled entry price"
    BASED_ON_PERCENT_PRICE_DESCRIPTION = "SL based on % from the current price"
    BASED_ON_STATIC_PRICE_DESCRIPTION = "SL based on static_price"
    BASED_ON_ATR_DESCRIPTION = "Sl based on ATR"
    BASED_ON_INDICATOR_DESCRIPTION = "SL based on indicator"

    KEY_TO_DESCRIPTIONS = {
        NO_SL: NO_SL_DESCRIPTION,
        BASED_ON_LOW_HIGH: AT_LOW_HIGH_DESCRIPTION,
        BASED_ON_PERCENT_ENTRY: BASED_ON_PERCENT_ENTRY_DESCRIPTION,
        BASED_ON_PERCENT_PRICE: BASED_ON_PERCENT_PRICE_DESCRIPTION,
        BASED_ON_STATIC_PRICE: BASED_ON_STATIC_PRICE_DESCRIPTION,
        BASED_ON_ATR: BASED_ON_ATR_DESCRIPTION,
        BASED_ON_INDICATOR: BASED_ON_INDICATOR_DESCRIPTION,
    }
    DESCRIPTIONS = [
        NO_SL_DESCRIPTION,
        AT_LOW_HIGH_DESCRIPTION,
        BASED_ON_PERCENT_ENTRY_DESCRIPTION,
        BASED_ON_PERCENT_PRICE_DESCRIPTION,
        BASED_ON_STATIC_PRICE_DESCRIPTION,
        BASED_ON_ATR_DESCRIPTION,
        BASED_ON_INDICATOR_DESCRIPTION,
    ]


class ManagedOrderSettingsSLTrailTypes:
    DONT_TRAIL = "dont_trail"
    BREAK_EVEN = "break_even"
    TRAILING = "trailing"
    TRAILING_INDICATOR = "trailing_indicator"

    DONT_TRAIL_DESCRIPTION = "dont move the stop loss"
    BREAK_EVEN_DESCRIPTION = "move stop loss to break even"
    TRAILING_DESCRIPTION = "trailing stop loss based on sl settings"
    TRAILING_INDICATOR_DESCRIPTION = "trailing stop loss based on indicator"

    KEY_TO_DESCRIPTIONS = {
        DONT_TRAIL: DONT_TRAIL_DESCRIPTION,
        BREAK_EVEN: BREAK_EVEN_DESCRIPTION,
        TRAILING: TRAILING_DESCRIPTION,
        TRAILING_INDICATOR: TRAILING_INDICATOR_DESCRIPTION,
    }
    DESCRIPTIONS = [
        DONT_TRAIL_DESCRIPTION,
        BREAK_EVEN_DESCRIPTION,
        TRAILING_DESCRIPTION,
        TRAILING_INDICATOR_DESCRIPTION,
    ]


class ManagedOrderSettingsSL:
    def __init__(self) -> None:
        super().__init__()

        self.sl_type: str = None
        self.use_bundled_sl_orders: bool = None
        self.sl_low_high_lookback: int = None
        self.sl_low_high_buffer: float = None
        self.sl_min_p: float = None
        self.sl_max_p: float = None
        self.sl_in_p_value: float = None
        self.sl_price: float = None
        self.sl_min_p: float = None
        self.sl_max_p: float = None
        self.atr_period: int = None
        self.sl_min_p: float = None
        self.sl_trail_type: str = None
        self.sl_trail_start_only_in_profit: bool = None
        self.sl_trail_start: float = None
        self.sl_trail_start_only_if_above_entry: bool = None
        self.sl_trailing_min_p: float = None
        self.sl_trailing_max_p: float = None

        self.sl_indicator_id: int = None
        self.trailing_indicator_id: int = None

    async def initialize_sl_settings(
        self,
        maker,
        parent_user_input_name,
        managed_order_group_id: int,
        enable_trailing_stop_settings: bool = False,
        enable_stop_loss_settings: bool = False,
    ):
        self.use_bundled_sl_orders = True  # await basic_keywords.user_input(
        #     maker.ctx,
        #     "Bundle stop order with entry order",
        #     "boolean",
        #     False,
        #
        #     parent_input_name=sl_setting_name,
        #     other_schema_values={
        #         "description": "When this option is enabled the SL will only get "
        #         "placed once the entry got filled (OctoBot must be running). "
        #         "Only on bybit futures it will already place the SL with the entry "
        #         "and OctoBot doesnt need to run for the SL"
        #     },
        #     show_in_optimizer=False,
        #     show_in_summary=False,
        # )
        if not enable_stop_loss_settings:
            self.sl_type = ManagedOrderSettingsSLTypes.NO_SL_DESCRIPTION
            return
        sl_setting_name_prefix = f"{managed_order_group_id}"
        sl_trailing_setting_name_prefix = f"{managed_order_group_id}"

        sl_setting_name = f"{managed_order_group_id}_sl_settings"
        sl_trailing_setting_name = f"{managed_order_group_id}_sl_trailing_settings"
        await basic_keywords.user_input(
            maker.ctx,
            sl_setting_name,
            "object",
            title="Stop loss settings",
            def_val=None,
            parent_input_name=parent_user_input_name,
            editor_options={
                commons_enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                commons_enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                commons_enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
            },
        )

        if self.use_bundled_sl_orders:
            available_types = ManagedOrderSettingsSLTypes.DESCRIPTIONS
            default_type = (
                ManagedOrderSettingsSLTypes.BASED_ON_PERCENT_ENTRY_DESCRIPTION
            )
        else:
            available_types = [
                ManagedOrderSettingsSLTypes.NO_SL_DESCRIPTION,
                ManagedOrderSettingsSLTypes.AT_LOW_HIGH_DESCRIPTION,
                ManagedOrderSettingsSLTypes.BASED_ON_STATIC_PRICE_DESCRIPTION,
                ManagedOrderSettingsSLTypes.BASED_ON_ATR_DESCRIPTION,
                ManagedOrderSettingsSLTypes.BASED_ON_INDICATOR_DESCRIPTION,
            ]
            default_type = ManagedOrderSettingsSLTypes.NO_SL_DESCRIPTION

        self.sl_type = await basic_keywords.user_input(
            maker.ctx,
            f"{sl_setting_name_prefix}_sl_type",
            "options",
            def_val=default_type,
            options=available_types,
            title="SL type",
            parent_input_name=sl_setting_name,
        )

        if self.sl_type == ManagedOrderSettingsSLTypes.NO_SL_DESCRIPTION:
            self.sl_trail_type = ManagedOrderSettingsSLTrailTypes.DONT_TRAIL_DESCRIPTION
        else:
            # SL based on low/high
            if self.sl_type == ManagedOrderSettingsSLTypes.AT_LOW_HIGH_DESCRIPTION:
                self.sl_low_high_lookback = await basic_keywords.user_input(
                    maker.ctx,
                    f"{sl_setting_name_prefix}_sl_at_low_high_lookback_period",
                    "int",
                    3,
                    title="SL at low/high lookback period",
                    parent_input_name=sl_setting_name,
                )
                self.sl_low_high_buffer = decimal.Decimal(
                    str(
                        await basic_keywords.user_input(
                            maker.ctx,
                            f"{sl_setting_name_prefix}_sl_at_low_high_buffer_in_%",
                            "float",
                            0.2,
                            title="SL at low/high buffer in %",
                            parent_input_name=sl_setting_name,
                        )
                    )
                )
                self.sl_min_p = decimal.Decimal(
                    str(
                        await basic_keywords.user_input(
                            maker.ctx,
                            f"{sl_setting_name_prefix}_min_sl_in_%",
                            "float",
                            0.1,
                            min_val=0,
                            title="min SL in %",
                            parent_input_name=sl_setting_name,
                        )
                    )
                )
                self.sl_max_p = decimal.Decimal(
                    str(
                        await basic_keywords.user_input(
                            maker.ctx,
                            f"{sl_setting_name_prefix}_max_sl_in_%",
                            "float",
                            1,
                            min_val=0,
                            title="max SL in %",
                            parent_input_name=sl_setting_name,
                        )
                    )
                )

            # sl based on percent
            elif self.sl_type in (
                ManagedOrderSettingsSLTypes.BASED_ON_PERCENT_ENTRY_DESCRIPTION,
                ManagedOrderSettingsSLTypes.BASED_ON_PERCENT_PRICE_DESCRIPTION,
            ):
                self.sl_in_p_value = decimal.Decimal(
                    str(
                        await basic_keywords.user_input(
                            maker.ctx,
                            f"{sl_setting_name_prefix}_sl_in_%",
                            "float",
                            0.5,
                            min_val=0,
                            title="SL in %",
                            parent_input_name=sl_setting_name,
                        )
                    )
                )

            # sl based on static price
            elif (
                self.sl_type
                == ManagedOrderSettingsSLTypes.BASED_ON_STATIC_PRICE_DESCRIPTION
            ):
                self.sl_price = decimal.Decimal(
                    str(
                        await basic_keywords.user_input(
                            maker.ctx,
                            f"{sl_setting_name_prefix}_sl_based_on_static_price",
                            "float",
                            0,
                            min_val=0,
                            title="SL based on static price",
                            parent_input_name=sl_setting_name,
                        )
                    )
                )

            # sl based on indicator
            # elif (
            #     self.sl_type
            #     == ManagedOrderSettingsSLTypes.BASED_ON_INDICATOR_DESCRIPTION
            # ):
            #     self.sl_indicator_id = f"{managed_order_group_id}100"
            #     await standalone_data_sources.activate_standalone_data_source(
            #         "Stop loss indicator",
            #         parent_input_name=sl_setting_name,
            #         indicator_id=self.sl_indicator_id,
            #         maker=maker,
            #     )
            #     self.sl_min_p = decimal.Decimal(
            #         str(
            #             await basic_keywords.user_input(
            #                 maker.ctx,
            #                 f"{sl_setting_name_prefix}_min_sl_in_%",
            #                 "float",
            #                 0.1,
            #                 min_val=0,
            #                 title="min SL in %",
            #                 parent_input_name=sl_setting_name,
            #             )
            #         )
            #     )
            #     self.sl_max_p = decimal.Decimal(
            #         str(
            #             await basic_keywords.user_input(
            #                 maker.ctx,
            #                 f"{sl_setting_name_prefix}_max_sl_in_%",
            #                 "float",
            #                 1,
            #                 min_val=0,
            #                 title="max SL in %",
            #                 parent_input_name=sl_setting_name,
            #             )
            #         )
            #     )

            # SL based on atr
            elif self.sl_type == ManagedOrderSettingsSLTypes.BASED_ON_ATR_DESCRIPTION:
                self.atr_period = await basic_keywords.user_input(
                    maker.ctx,
                    f"{sl_setting_name_prefix}_atr_period",
                    "int",
                    4,
                    title="ATR Period",
                    parent_input_name=sl_setting_name,
                )
                self.sl_min_p = decimal.Decimal(
                    str(
                        await basic_keywords.user_input(
                            maker.ctx,
                            f"{sl_setting_name_prefix}_min_sl_in_%",
                            "float",
                            0.1,
                            min_val=0,
                            title="min SL in %",
                            parent_input_name=sl_setting_name,
                        )
                    )
                )
                self.sl_max_p = decimal.Decimal(
                    str(
                        await basic_keywords.user_input(
                            maker.ctx,
                            f"{sl_setting_name_prefix}_max_sl_in_%",
                            "float",
                            1,
                            min_val=0,
                            title="max SL in %",
                            parent_input_name=sl_setting_name,
                        )
                    )
                )

            if enable_trailing_stop_settings:
                # trailing SL
                await basic_keywords.user_input(
                    maker.ctx,
                    sl_trailing_setting_name,
                    "object",
                    title="Trailing stop loss settings",
                    def_val=None,
                    parent_input_name=parent_user_input_name,
                    editor_options={
                        commons_enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                        commons_enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                        commons_enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
                    },
                )
                self.sl_trail_type = await basic_keywords.user_input(
                    maker.ctx,
                    f"{sl_trailing_setting_name_prefix}_sl_trailing_type",
                    "options",
                    ManagedOrderSettingsSLTrailTypes.DONT_TRAIL_DESCRIPTION,
                    options=ManagedOrderSettingsSLTrailTypes.DESCRIPTIONS,
                    title="SL trailing type",
                    parent_input_name=sl_trailing_setting_name,
                )
                if (
                    self.sl_trail_type
                    == ManagedOrderSettingsSLTrailTypes.BREAK_EVEN_DESCRIPTION
                ):
                    self.sl_trail_start_only_in_profit = True
                    self.sl_trail_start = decimal.Decimal(
                        str(
                            await basic_keywords.user_input(
                                maker.ctx,
                                f"{sl_trailing_setting_name_prefix}_move_stop_loss_to_break_even_when_price_moves_x%_into_profit",
                                "float",
                                0.5,
                                min_val=0,
                                title="move stop loss to break even when price moves x% into profit",
                                parent_input_name=sl_trailing_setting_name,
                            )
                        )
                    )
                    self.sl_trail_start_only_if_above_entry = False
                elif (
                    self.sl_trail_type
                    == ManagedOrderSettingsSLTrailTypes.TRAILING_DESCRIPTION
                ):
                    self.sl_trail_start_only_in_profit = await basic_keywords.user_input(
                        maker.ctx,
                        f"{sl_trailing_setting_name_prefix}_start_stop_loss_trailing_only_when_price_moves_into_profit",
                        "boolean",
                        True,
                        title="start stop loss trailing only when price moves into profit",
                        parent_input_name=sl_trailing_setting_name,
                    )
                    if self.sl_trail_start_only_in_profit:
                        self.sl_trail_start = decimal.Decimal(
                            str(
                                await basic_keywords.user_input(
                                    maker.ctx,
                                    f"{sl_trailing_setting_name_prefix}_start_trailing_the_SL_when_price_moves_x%_into_profit",
                                    "float",
                                    0.5,
                                    min_val=0,
                                    title="start trailing the SL when price moves x% into profit",
                                    parent_input_name=sl_trailing_setting_name,
                                )
                            )
                        )
                    self.sl_trail_start_only_if_above_entry = await basic_keywords.user_input(
                        maker.ctx,
                        f"{sl_trailing_setting_name_prefix}_start_trailing_only_if_SL_would_be_above_the_entry",
                        "boolean",
                        True,
                        title="Start trailing only if SL would be above the entry",
                        parent_input_name=sl_trailing_setting_name,
                    )

            #     elif (
            #         self.sl_trail_type
            #         == ManagedOrderSettingsSLTrailTypes.TRAILING_INDICATOR_DESCRIPTION
            #     ):
            #         self.trailing_indicator_id = managed_order_group_id + 200

            #         await standalone_data_sources.activate_standalone_data_source(
            #             "Trailing stop loss indicator",
            #             parent_input_name=sl_trailing_setting_name,
            #             indicator_id=self.trailing_indicator_id,
            #             maker=maker,
            #         )
            #         self.sl_trail_start_only_in_profit = await basic_keywords.user_input(
            #             maker.ctx,
            #             f"{sl_trailing_setting_name_prefix}_start_stop_loss_trailing_only_when_price_moves_into_profit",
            #             "boolean",
            #             True,
            #             title="start stop loss trailing only when price moves into profit",
            #             parent_input_name=sl_trailing_setting_name,
            #         )
            #         if self.sl_trail_start_only_in_profit:
            #             self.sl_trail_start = decimal.Decimal(
            #                 str(
            #                     await basic_keywords.user_input(
            #                         maker.ctx,
            #                         f"{sl_trailing_setting_name_prefix}_start_trailing_the_SL_when_price_moves_x%_into_profit",
            #                         "float",
            #                         0.5,
            #                         min_val=0,
            #                         title="start trailing the SL when price moves x% into profit",
            #                         parent_input_name=sl_trailing_setting_name,
            #                     )
            #                 )
            #             )
            #         self.sl_trailing_min_p = decimal.Decimal(
            #             str(
            #                 await basic_keywords.user_input(
            #                     maker.ctx,
            #                     f"{sl_trailing_setting_name_prefix}_min_trailing_SL_in_%",
            #                     "float",
            #                     0.1,
            #                     min_val=0,
            #                     title="min trailing SL in %",
            #                     parent_input_name=sl_trailing_setting_name,
            #                 )
            #             )
            #         )
            #         self.sl_trailing_max_p = decimal.Decimal(
            #             str(
            #                 await basic_keywords.user_input(
            #                     maker.ctx,
            #                     f"{sl_trailing_setting_name_prefix}_max_trailing_SL_in_%",
            #                     "float",
            #                     1,
            #                     min_val=0,
            #                     title="max trailing SL in %",
            #                     parent_input_name=sl_trailing_setting_name,
            #                 )
            #             )
            #         )
            #         self.sl_trail_start_only_if_above_entry = await basic_keywords.user_input(
            #             maker.ctx,
            #             f"{sl_trailing_setting_name_prefix}_start_trailing_only_if_sl_would_be_above_the_entry",
            #             "boolean",
            #             True,
            #             title="Start trailing only if SL would be above the entry",
            #             parent_input_name=sl_trailing_setting_name,
            #         )
            # else:
            #     self.sl_trail_type = (
            #         ManagedOrderSettingsSLTrailTypes.DONT_TRAIL_DESCRIPTION
            #     )
