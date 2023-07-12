import decimal
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.all_settings as all_settings
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.managed_orders as managed_orders


async def activate_managed_orders(
    maker,
    # user_input_path: str = "evaluator/Managed_Order_Settings",
    parent_input_name: str = None,
    order_tag_prefix: str = "Managed order",
    name_prefix: str = None,
    enable_position_size_settings: bool = True,
    enable_stop_loss_settings: bool = True,
    enable_trailing_stop_settings: bool = False,
    enable_take_profit_settings: bool = True,
) -> all_settings.ManagedOrdersSettings:
    try:
        orders_settings = all_settings.ManagedOrdersSettings()
        await orders_settings.initialize(
            maker,
            parent_user_input_name=parent_input_name,
            order_tag_prefix=order_tag_prefix,
            unique_name_prefix=name_prefix,
            enable_position_size_settings=enable_position_size_settings,
            enable_trailing_stop_settings=enable_trailing_stop_settings,
            enable_stop_loss_settings=enable_stop_loss_settings,
            enable_take_profit_settings=enable_take_profit_settings,
        )
        return orders_settings
    except Exception as error:
        raise RuntimeError(
            "Managed Order: There is an issue in your Managed Order "
            "configuration. Check the settings: " + str(error)
        ) from error


async def managed_order(
    maker,
    order_block,
    trading_side: str,
    orders_settings: all_settings.ManagedOrdersSettings,
    forced_amount: decimal.Decimal = None,
    order_preview_mode: bool = False,
) -> managed_orders.ManagedOrder:
    """
    :param maker:
    :param trading_side:
        can be "long" or short
    :param orders_settings:
        pass custom settings or use activate_managed_orders(ctx)

    :return:
    """
    _managed_order = managed_orders.ManagedOrder()
    return await _managed_order.initialize_and_trade(
        maker=maker,
        order_block=order_block,
        trading_side=trading_side,
        orders_settings=orders_settings,
        forced_amount=forced_amount,
        order_preview_mode=order_preview_mode,
    )


async def managed_order_preview(
    maker,
    order_block,
    trading_side: str,
    orders_settings: all_settings.ManagedOrdersSettings,
) -> managed_orders.ManagedOrder or None:
    if not maker.exchange_manager.is_backtesting:
        return await managed_order(
            maker,
            order_block=order_block,
            trading_side=trading_side,
            orders_settings=orders_settings,
            order_preview_mode=True,
        )
