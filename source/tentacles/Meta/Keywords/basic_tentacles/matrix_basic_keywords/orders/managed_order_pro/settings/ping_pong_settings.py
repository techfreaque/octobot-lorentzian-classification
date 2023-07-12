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

import octobot_commons.enums as commons_enums

import octobot_trading.modes.script_keywords.basic_keywords as basic_keywords
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.entry_types as entry_types


class ManagedOrderSettingsPingPongTypes:
    SIMPLE_PING_PONG = "simple_ping_pong"
    SIMPLE_PING_PONG_DESCRIPTION = (
        "Recreate entry orders when take profits get filled "
        "and repeat the process until the order gets canceled"
    )
    NO_PING_PONG = "no_ping_pong"
    NO_PING_PONG_DESCRIPTION = "dont use ping pong mode"

    KEY_TO_DESCRIPTIONS = {
        SIMPLE_PING_PONG: SIMPLE_PING_PONG_DESCRIPTION,
        NO_PING_PONG: NO_PING_PONG_DESCRIPTION,
    }
    DESCRIPTIONS = [
        SIMPLE_PING_PONG_DESCRIPTION,
        NO_PING_PONG_DESCRIPTION,
    ]


class ManagedOrderSettingsPingPong:
    ping_pong_mode_enabled: bool = False

    def __init__(self) -> None:
        self.ping_pong_type: str = None

    async def initialize_ping_pong_settings(
        self,
        maker,
        entry_type: str,
        parent_user_input_name: str,
        managed_order_group_id: int,
    ):
        if entry_type in (
            entry_types.ManagedOrderSettingsEntryTypes.SCALED_DYNAMIC_DESCRIPTION,
            entry_types.ManagedOrderSettingsEntryTypes.SCALED_STATIC_DESCRIPTION,
        ):
            ping_pong_name_prefix = f"{managed_order_group_id}"
            ping_pong_settings_name = f"{managed_order_group_id}_ping_pong_settings"
            await basic_keywords.user_input(
                maker.ctx,
                ping_pong_settings_name,
                "object",
                title="Ping pong settings",
                def_val=None,
                parent_input_name=parent_user_input_name,
                editor_options={
                    commons_enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                    commons_enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                    commons_enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
                },
            )
            self.ping_pong_type = await basic_keywords.user_input(
                maker.ctx,
                f"{ping_pong_name_prefix}_ping_pong_type",
                "options",
                ManagedOrderSettingsPingPongTypes.NO_PING_PONG_DESCRIPTION,
                title="Ping pong type",
                options=ManagedOrderSettingsPingPongTypes.DESCRIPTIONS,
                parent_input_name=ping_pong_settings_name,
            )

            if (
                self.ping_pong_type
                == ManagedOrderSettingsPingPongTypes.SIMPLE_PING_PONG_DESCRIPTION
            ):
                maker.any_ping_pong_mode_active = True
                self.ping_pong_mode_enabled = True
