import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.ping_pong_settings as ping_pong_settings
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.entry_settings as entry_settings
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.sl_settings as sl_settings
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.position_size_settings as position_size_settings
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.tp_settings as tp_settings
import tentacles.Meta.Keywords.scripting_library.orders.grouping as grouping


class ManagedOrderSettingsOrderGroup:
    stop_loss: sl_settings.ManagedOrderSettingsSL = sl_settings.ManagedOrderSettingsSL
    take_profit: tp_settings.ManagedOrderSettingsTP = tp_settings.ManagedOrderSettingsTP
    entry: entry_settings.ManagedOrderSettingsEntry = (
        entry_settings.ManagedOrderSettingsEntry
    )
    position_size: position_size_settings.ManagedOrderSettingsPositionSize = (
        position_size_settings.ManagedOrderSettingsPositionSize
    )
    ping_pong: ping_pong_settings.ManagedOrderSettingsPingPong = (
        ping_pong_settings.ManagedOrderSettingsPingPong
    )

    def __init__(self, order_manager_id, group_id, order_tag_prefix):
        self.order_tag_prefix = f"{order_tag_prefix}_{group_id}"
        self.stop_loss = self.stop_loss()
        self.take_profit = self.take_profit()
        self.entry = self.entry()
        self.position_size = self.position_size()
        self.ping_pong = self.ping_pong()
        self.order_manager_group_id = f"{order_manager_id}_{group_id}"
        self.order_groups: list = []
        self.enabled_order_group = False

    async def create_managed_order_group(self, ctx):
        if (
            tp_settings.ManagedOrderSettingsTPTypes.NO_TP_DESCRIPTION
            != self.take_profit.tp_type
            and sl_settings.ManagedOrderSettingsSLTypes.NO_SL_DESCRIPTION
            != self.stop_loss.sl_type
        ):
            try:
                order_group = (
                    grouping.get_or_create_balanced_take_profit_and_stop_group(ctx)
                )
                self.order_groups.append(order_group)
            except AttributeError:
                # try to continue creating exits without grouping as entries are probably placed already
                self.enabled_order_group = False
                ctx.logger.error(
                    "Managed order: failed to activate exit order grouping, "
                    "one cancels the other will not work"
                )
                return self
            # disable group to be able to create stop and take profit orders sequentially
            await grouping.enable_group(order_group, True)
            self.enabled_order_group = True
            return order_group

    async def enable_managed_order_groups(self):
        if self.order_groups:
            for order_group in self.order_groups:
                await grouping.enable_group(order_group, True)
