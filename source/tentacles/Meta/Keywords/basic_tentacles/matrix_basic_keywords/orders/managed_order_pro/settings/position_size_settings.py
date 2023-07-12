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
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.sl_settings as sl_settings


class ManagedOrderSettingsPositionSizeTypes:
    QUANTITY_RISK_OF_ACCOUNT = "quantity_risk_of_account"
    PERCENT_RISK_OF_ACCOUNT = "percent_risk_of_account"
    PERCENT_OF_ACCOUNT = "percent_of_account"
    PERCENT_OF_AVAILABLE_ACCOUNT = "percent_of_available_account"

    QUANTITY_RISK_OF_ACCOUNT_DESCRIPTION = (
        "Position size based on quantity risk (for example 0.1 BTC)"
    )
    PERCENT_RISK_OF_ACCOUNT_DESCRIPTION = (
        "Position size based on % risk of total account"
    )
    PERCENT_OF_ACCOUNT_DESCRIPTION = "Position size based on % of total account size"
    PERCENT_OF_AVAILABLE_ACCOUNT_DESCRIPTION = (
        "Position size based on % of available account size"
    )
    KEY_TO_DESCRIPTIONS = {
        QUANTITY_RISK_OF_ACCOUNT: QUANTITY_RISK_OF_ACCOUNT_DESCRIPTION,
        PERCENT_RISK_OF_ACCOUNT: PERCENT_RISK_OF_ACCOUNT_DESCRIPTION,
        PERCENT_OF_ACCOUNT: PERCENT_OF_ACCOUNT_DESCRIPTION,
        PERCENT_OF_AVAILABLE_ACCOUNT: PERCENT_OF_AVAILABLE_ACCOUNT_DESCRIPTION,
    }
    DESCRIPTIONS = [
        QUANTITY_RISK_OF_ACCOUNT_DESCRIPTION,
        PERCENT_RISK_OF_ACCOUNT_DESCRIPTION,
        PERCENT_OF_ACCOUNT_DESCRIPTION,
        PERCENT_OF_AVAILABLE_ACCOUNT_DESCRIPTION,
    ]


class ManagedOrderSettingsPositionSize:
    def __init__(self) -> None:
        self.position_size_type: str = None
        self.risk_in_d: float = None
        self.total_risk_in_d: float = None
        self.risk_in_p: float = None
        self.total_risk_in_p: float = None
        self.managed_order_group_id: str = None

    async def initialize_position_size_settings(
        self,
        ctx,
        sl_type,
        parent_user_input_name,
        managed_order_group_id: int,
    ):
        self.managed_order_group_id = managed_order_group_id
        position_size_setting_name_prefix = f"{managed_order_group_id}"
        position_size_setting_name = f"{managed_order_group_id}_position_size_settings"
        await basic_keywords.user_input(
            ctx,
            position_size_setting_name,
            "object",
            title="Position size settings",
            def_val=None,
            parent_input_name=parent_user_input_name,
            editor_options={
                commons_enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                commons_enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                commons_enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
            },
        )
        if sl_type == sl_settings.ManagedOrderSettingsSLTypes.NO_SL_DESCRIPTION:
            position_size_options = [
                ManagedOrderSettingsPositionSizeTypes.PERCENT_OF_ACCOUNT_DESCRIPTION,
                ManagedOrderSettingsPositionSizeTypes.PERCENT_OF_AVAILABLE_ACCOUNT_DESCRIPTION,
            ]
            position_size_def_val = (
                ManagedOrderSettingsPositionSizeTypes.PERCENT_OF_AVAILABLE_ACCOUNT_DESCRIPTION
            )
        else:
            position_size_options = ManagedOrderSettingsPositionSizeTypes.DESCRIPTIONS
            position_size_def_val = (
                ManagedOrderSettingsPositionSizeTypes.PERCENT_RISK_OF_ACCOUNT_DESCRIPTION
            )

        # position size
        self.position_size_type = await basic_keywords.user_input(
            ctx,
            f"{position_size_setting_name_prefix}_position_size_type",
            "options",
            position_size_def_val,
            title="position Size Type",
            options=position_size_options,
            parent_input_name=position_size_setting_name,
        )

        # position size based on percent risk
        if (
            self.position_size_type
            == ManagedOrderSettingsPositionSizeTypes.QUANTITY_RISK_OF_ACCOUNT_DESCRIPTION
        ):
            self.risk_in_d = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        ctx,
                        f"{position_size_setting_name_prefix}_risk_per_trade",
                        "float",
                        100,
                        title="risk per trade (measured in reference market currency)",
                        min_val=0,
                        parent_input_name=position_size_setting_name,
                    )
                )
            )
            self.total_risk_in_d = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        ctx,
                        f"{position_size_setting_name_prefix}_total_risk",
                        "float",
                        200,
                        title="total risk (measured in reference market currency)",
                        min_val=0,
                        parent_input_name=position_size_setting_name,
                    )
                )
            )

        # position size based on dollar risk (measured in reference market)
        elif (
            self.position_size_type
            == ManagedOrderSettingsPositionSizeTypes.PERCENT_RISK_OF_ACCOUNT_DESCRIPTION
        ):
            self.risk_in_p = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        ctx,
                        f"{position_size_setting_name_prefix}_risk_per_trade_in_%",
                        "float",
                        0.5,
                        title="risk per trade in %",
                        min_val=0,
                        parent_input_name=position_size_setting_name,
                    )
                )
            )
            self.total_risk_in_p = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        ctx,
                        f"{position_size_setting_name_prefix}_total_risk_in_%",
                        "float",
                        2,
                        title="total risk in %",
                        min_val=0,
                        parent_input_name=position_size_setting_name,
                    )
                )
            )

        # position size based on % of total account size
        elif (
            self.position_size_type
            == ManagedOrderSettingsPositionSizeTypes.PERCENT_OF_ACCOUNT_DESCRIPTION
        ):
            self.risk_in_p = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        ctx,
                        f"{position_size_setting_name_prefix}_position_per_trade_in_%_of_account_size",
                        "float",
                        50,
                        title="position per trade in % of account size",
                        min_val=0,
                        parent_input_name=position_size_setting_name,
                    )
                )
            )
            self.total_risk_in_p = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        ctx,
                        f"{position_size_setting_name_prefix}_max_position_in_%_of_account_size",
                        "float",
                        100,
                        title="max position in % of account size",
                        min_val=0,
                        parent_input_name=position_size_setting_name,
                    )
                )
            )

        # position size based on % of available account size
        elif (
            self.position_size_type
            == ManagedOrderSettingsPositionSizeTypes.PERCENT_OF_AVAILABLE_ACCOUNT_DESCRIPTION
        ):
            self.risk_in_p = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        ctx,
                        f"{position_size_setting_name_prefix}_position_per_trade_in_%_of_account_size",
                        "float",
                        50,
                        title="position per trade in % of available account size",
                        min_val=0,
                        max_val=100,
                        parent_input_name=position_size_setting_name,
                    )
                )
            )
            self.total_risk_in_p = decimal.Decimal(
                str(
                    await basic_keywords.user_input(
                        ctx,
                        f"{position_size_setting_name_prefix}_max_position_in_%_of_account_size",
                        "float",
                        100,
                        title="max position in % of available account size",
                        min_val=0,
                        max_val=100,
                        parent_input_name=position_size_setting_name,
                    )
                )
            )
