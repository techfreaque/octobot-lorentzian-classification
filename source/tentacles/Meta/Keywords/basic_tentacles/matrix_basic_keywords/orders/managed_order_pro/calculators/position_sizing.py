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

import decimal as decimal
import uuid
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.matrix_enums as matrix_enums
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.matrix_errors as matrix_errors
from tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.daemons.ping_pong import (
    ping_pong_constants,
)
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.daemons.ping_pong.ping_pong_storage.storage as storage
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.settings.position_size_settings as size_settings
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_public_data as exchange_public_data
import tentacles.Meta.Keywords.scripting_library.data.reading.exchange_private_data.open_positions as open_positions
import octobot_trading.modes.script_keywords.basic_keywords.account_balance as account_balance
import octobot_trading.enums as trading_enums


async def get_manged_order_position_size(
    maker,
    position_size_settings,
    trading_side: str,
    entry_side: str,
    entry_price: decimal.Decimal,
    entry_order_type: decimal.Decimal,
    stop_loss_percent: decimal.Decimal,
    order_tag_prefix: str,
    forced_amount: decimal.Decimal = None,
    recreate_exits: bool = False,
):
    # position size
    limit_fee, market_fee = get_fees(maker.ctx)
    entry_order_tag, tp_order_tag, sl_order_tag, order_tag_id = get_managed_order_tags(
        maker=maker, position_size_settings=position_size_settings
    )
    position_size = max_position_size = current_open_risk = None
    # position size based on amount passed through managed_order
    if forced_amount:
        position_size = max_position_size = forced_amount

    # position size based on dollar/reference market risk
    elif (
        position_size_settings.position_size_type
        == size_settings.ManagedOrderSettingsPositionSizeTypes.QUANTITY_RISK_OF_ACCOUNT_DESCRIPTION
    ):
        (
            position_size,
            max_position_size,
            current_open_risk,
        ) = get_position_size_based_ref_market_quantity_risk(
            maker.ctx,
            entry_order_type=entry_order_type,
            stop_loss_percent=stop_loss_percent,
            risk_in_ref_market_quantity=position_size_settings.risk_in_d,
            total_risk_in_ref_market_quantity=position_size_settings.total_risk_in_d,
            entry_price=entry_price,
            limit_fees=limit_fee,
            market_fees=market_fee,
        )

    # position size based risk per trade in percent
    elif (
        position_size_settings.position_size_type
        == size_settings.ManagedOrderSettingsPositionSizeTypes.PERCENT_RISK_OF_ACCOUNT_DESCRIPTION
    ):
        (
            position_size,
            max_position_size,
            current_open_risk,
        ) = await get_position_size_based_risk_percent(
            maker.ctx,
            entry_order_type=entry_order_type,
            stop_loss_percent=stop_loss_percent,
            risk_in_percent=position_size_settings.risk_in_p,
            total_risk_in_percent=position_size_settings.total_risk_in_p,
            limit_fees=limit_fee,
            market_fees=market_fee,
        )

    # position size based on percent of total account balance
    elif (
        position_size_settings.position_size_type
        == size_settings.ManagedOrderSettingsPositionSizeTypes.PERCENT_OF_ACCOUNT_DESCRIPTION
    ):
        position_size, max_position_size = await get_position_size_based_on_account(
            maker.ctx,
            trading_side,
            position_size_settings.risk_in_p,
            position_size_settings.total_risk_in_p,
        )

    # position size based on percent of available account balance
    elif (
        position_size_settings.position_size_type
        == size_settings.ManagedOrderSettingsPositionSizeTypes.PERCENT_OF_AVAILABLE_ACCOUNT_DESCRIPTION
    ):
        (
            position_size,
            max_position_size,
        ) = await get_position_size_based_on_available_account(
            maker.ctx,
            trading_side,
            position_size_settings.risk_in_p,
            position_size_settings.total_risk_in_p,
        )

    (
        max_position_size,
        max_buying_power,
        position_size,
    ) = await adapt_sizes_to_limits(
        maker.ctx,
        position_size,
        max_position_size,
        entry_side,
    )
    place_entries = False
    if position_size == 0:
        maker.ctx.logger.warning(
            "Managed order cant open a new position, "
            "the digits adapted price is 0. Make sure the position size is at "
            f"least the minimum size required by the exchange for {maker.ctx.symbol}"
        )
        raise matrix_errors.MaximumOpenPositionReachedError

    if position_size < 0:
        maker.ctx.logger.info(
            "Managed order cant open a new position, "
            "maximum position size is reached"
        )
        raise matrix_errors.MaximumOpenPositionReachedError
    place_entries = True

    return (
        position_size,
        max_position_size,
        current_open_risk,
        max_buying_power,
        place_entries,
        entry_order_tag,
        tp_order_tag,
        sl_order_tag,
        order_tag_id,
    )


def get_fees(ctx, use_decimal: bool = True):
    fees = exchange_public_data.symbol_fees(ctx)
    fallback_fees = fees.get("fee", 0)
    limit_fee = float(fallback_fees if fees["maker"] is None else fees["maker"]) * 100
    market_fee = float(fallback_fees if fees["taker"] is None else fees["taker"]) * 100
    if not use_decimal:
        return limit_fee, market_fee
    deci_limit_fee = decimal.Decimal(str(limit_fee))
    deci_market_fee = decimal.Decimal(str(market_fee))
    return deci_limit_fee, deci_market_fee


async def adapt_sizes_to_limits(
    ctx,
    position_size,
    max_position_size: decimal.Decimal,
    entry_side,
):
    max_position_size = exchange_public_data.get_digits_adapted_amount(
        ctx, max_position_size
    )

    max_buying_power = exchange_public_data.get_digits_adapted_amount(
        ctx,
        await account_balance.available_account_balance(
            ctx, side=entry_side, reduce_only=False
        ),
    )
    if not max_buying_power:
        ctx.logger.warning(
            "Managed order cant open a new position, "
            f"no available balance for {ctx.symbol}"
        )
        raise matrix_errors.MaximumOpenPositionReachedError

    # check if enough balance for requested size and cut if necessary
    if max_buying_power < position_size:
        position_size = max_buying_power

    # cut the position size so that it aligns with target risk
    if position_size > max_position_size:
        position_size = max_position_size

    position_size = exchange_public_data.get_digits_adapted_amount(ctx, position_size)

    return max_position_size, max_buying_power, position_size


async def get_current_open_risk(ctx, market_fee):
    current_average_long_entry = await open_positions.average_open_pos_entry(
        ctx, side="long"
    )

    current_average_short_entry = await open_positions.average_open_pos_entry(
        ctx, side="short"
    )

    current_open_orders = (
        ctx.exchange_manager.exchange_personal_data.orders_manager.orders
    )
    current_open_risk = 0
    for order in current_open_orders:
        if (
            current_open_orders[order].order_type
            == trading_enums.TraderOrderType.STOP_LOSS
        ):
            if current_open_orders[order].side in (
                trading_enums.PositionSide.SHORT.value,
                trading_enums.TradeOrderSide.SELL.value,
            ):
                stop_loss_distance = (
                    current_average_long_entry - current_open_orders[order].origin_price
                )
            else:
                stop_loss_distance = (
                    current_open_orders[order].origin_price
                    - current_average_short_entry
                )

            current_open_risk += (
                ((market_fee) / 100) * current_open_orders[order].origin_quantity
            ) + (
                (current_open_orders[order].origin_quantity)
                * stop_loss_distance
                / current_open_orders[order].origin_price
            )

    return current_open_risk


async def get_position_size_based_ref_market_quantity_risk(
    ctx,
    entry_order_type: str,
    stop_loss_percent: decimal.Decimal,
    risk_in_ref_market_quantity: decimal.Decimal,
    total_risk_in_ref_market_quantity: decimal.Decimal,
    entry_price: decimal.Decimal,
    limit_fees: decimal.Decimal,
    market_fees: decimal.Decimal,
):
    if entry_order_type == "market":
        position_size = (
            (risk_in_ref_market_quantity / entry_price)
            / (stop_loss_percent + (market_fees + market_fees))
        ) / 0.01
    else:
        position_size = (
            (risk_in_ref_market_quantity / entry_price)
            / (stop_loss_percent + (limit_fees + market_fees))
        ) / 0.01
    current_open_risk = await get_current_open_risk(ctx, market_fees)

    max_position_size = (
        ((total_risk_in_ref_market_quantity / entry_price) - current_open_risk)
        / (stop_loss_percent + (2 * market_fees))
    ) / 0.01
    return position_size, max_position_size, current_open_risk


async def get_position_size_based_risk_percent(
    ctx,
    entry_order_type: str,
    stop_loss_percent: decimal.Decimal,
    risk_in_percent: decimal.Decimal,
    total_risk_in_percent: decimal.Decimal,
    limit_fees: decimal.Decimal,
    market_fees: decimal.Decimal,
):
    current_total_acc_balance = await account_balance.total_account_balance(ctx)
    if not current_total_acc_balance:
        ctx.logger.warning(
            "Managed order cant open a new position, "
            f"no available balance for {ctx.symbol}"
        )
        raise matrix_errors.MaximumOpenPositionReachedError
    risk_in_d = (risk_in_percent / 100) * current_total_acc_balance
    if entry_order_type == "market":
        position_size = (
            risk_in_d / (stop_loss_percent + (2 * market_fees))
        ) / decimal.Decimal("0.01")
    else:
        position_size = (
            risk_in_d / (stop_loss_percent + limit_fees + market_fees)
        ) / decimal.Decimal("0.01")
    current_open_risk = await get_current_open_risk(ctx, market_fees)

    total_risk_in_d = (
        total_risk_in_percent / 100
    ) * current_total_acc_balance - current_open_risk
    max_position_size = (
        total_risk_in_d / (stop_loss_percent + (2 * market_fees))
    ) / decimal.Decimal("0.01")
    return position_size, max_position_size, current_open_risk


async def get_position_size_based_on_account(
    ctx,
    trading_side,
    stop_loss_percent: decimal.Decimal,
    stop_loss_total_percent: decimal.Decimal,
) -> tuple:
    current_total_acc_balance = await account_balance.total_account_balance(ctx)
    if not current_total_acc_balance:
        ctx.logger.warning(
            "Managed order cant open a new position, "
            f"no available balance for {trading_side} {ctx.symbol}"
        )
        raise matrix_errors.MaximumOpenPositionReachedError
    position_size = (stop_loss_percent / 100) * current_total_acc_balance
    current_open_position_size = open_positions.open_position_size(ctx, side="both")
    if trading_side in (
        trading_enums.PositionSide.SHORT.value,
        trading_enums.TradeOrderSide.SELL.value,
    ):
        current_open_position_size *= -1
    max_position_size = (stop_loss_total_percent / 100) * current_total_acc_balance
    return position_size, max_position_size


async def get_position_size_based_on_available_account(
    ctx,
    trading_side,
    stop_loss_percent: decimal.Decimal,
    stop_loss_total_percent: decimal.Decimal,
) -> tuple:
    current_acc_balance = await account_balance.available_account_balance(
        ctx,
        side=trading_enums.TradeOrderSide.SELL.value
        if trading_side
        in (
            trading_enums.PositionSide.SHORT.value,
            trading_enums.TradeOrderSide.SELL.value,
        )
        else trading_enums.TradeOrderSide.BUY.value,
    )
    if not current_acc_balance:
        ctx.logger.warning(
            "Managed order cant open a new position, "
            f"no available balance for {trading_side} {ctx.symbol}"
        )
        raise matrix_errors.MaximumOpenPositionReachedError
    position_size = (stop_loss_percent / 100) * current_acc_balance
    current_open_position_size = open_positions.open_position_size(ctx, side="both")
    if trading_side in (
        trading_enums.PositionSide.SHORT.value,
        trading_enums.TradeOrderSide.SELL.value,
    ):
        current_open_position_size *= -1
    max_position_size = (stop_loss_total_percent / 100) * current_acc_balance
    return position_size, max_position_size


def get_managed_order_tags(maker, position_size_settings):
    ping_pong_storage: storage.PingPongStorage = storage.get_ping_pong_storage(
        maker.ctx.exchange_manager
    )
    if ping_pong_storage is None:
        order_tag_id = str(uuid.uuid4()).split("-")[0]
    else:
        order_tag_id = ping_pong_storage.generate_next_order_group_id()
    tp_order_tag = (
        f"{ping_pong_constants.TAKE_PROFIT}{matrix_enums.TAG_SEPERATOR}"
        f"{position_size_settings.managed_order_group_id}{matrix_enums.TAG_SEPERATOR}{order_tag_id}"
    )
    sl_order_tag = (
        f"{ping_pong_constants.STOP_LOSS}{matrix_enums.TAG_SEPERATOR}"
        f"{position_size_settings.managed_order_group_id}{matrix_enums.TAG_SEPERATOR}{order_tag_id}"
    )
    entry_order_tag = (
        f"{ping_pong_constants.ENTRY}{matrix_enums.TAG_SEPERATOR}"
        f"{position_size_settings.managed_order_group_id}{matrix_enums.TAG_SEPERATOR}{order_tag_id}"
    )
    return entry_order_tag, tp_order_tag, sl_order_tag, order_tag_id
