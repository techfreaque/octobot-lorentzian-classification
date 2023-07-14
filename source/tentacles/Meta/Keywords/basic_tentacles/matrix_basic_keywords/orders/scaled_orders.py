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
import numpy
import octobot_trading.enums as trading_enums
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.matrix_errors as matrix_errors
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.order_placement as order_placement
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.position_sizing as position_sizing
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.stop_loss as stop_loss
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.calculators.take_profit as take_profit
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.utilities as matrix_utilities
import tentacles.Meta.Keywords.scripting_library.orders.order_types.create_order as create_order
import tentacles.Meta.Keywords.scripting_library.orders.position_size as position_size
import tentacles.Meta.Keywords.scripting_library.orders.offsets as offsets


class ScaledOrderValueDistributionTypes:
    FLAT = "flat"  # all orders have the same amount
    LINEAR_GROWTH = "linear_growth"  # order value will grow linear
    EXPONENTIAL = "exponential"  # order value will grow exponential
    all_types = [FLAT, LINEAR_GROWTH]


class ScaledOrderPriceDistributionTypes:
    FLAT = "flat"  # all orders have the same distance
    LINEAR_GROWTH = "linear_growth"
    EXPONENTIAL = "exponential"
    all_types = [FLAT, LINEAR_GROWTH]


async def scaled_order(
    maker,
    order_block,
    current_price,
    side=None,
    symbol=None,
    order_type_name="limit",
    scale_from=None,
    scale_to=None,
    order_count=10,
    value_distribution_type=ScaledOrderValueDistributionTypes.FLAT,
    price_distribution_type=ScaledOrderPriceDistributionTypes.FLAT,
    value_growth_factor=2,
    price_growth_factor=2,
    group_orders_settings=None,
    # either amount, value, target_position or position_size_calculator
    amount=None,
    forced_amount: decimal.Decimal = None,
    value: decimal.Decimal = None,  # value in ref market
    target_position=None,
    # position_size_calculator=None,
    # either stop_loss_calculator or stop_loss_offset
    # stop_loss_calculator=None,
    # stop_loss_calculator_bundling=False,
    stop_loss_offset=None,
    stop_loss_tag=None,
    stop_loss_type=None,
    stop_loss_group=None,
    # either offset or take_profit_calculator
    take_profit_offset=None,
    # take_profit_calculator=None,
    take_profit_tag=None,
    take_profit_type=None,
    take_profit_group=None,
    slippage_limit=None,
    time_limit=None,
    reduce_only=False,
    post_only=False,
    tag=None,
    group=None,
    wait_for=None,
    force_enter_the_grid=True,
    order_preview_mode=False,
):
    order_tag_id = None
    try:
        (
            entry_prices,
            stop_loss_prices,
            order_amounts,
            place_entries,
            entry_order_tag,
            tp_order_tag,
            sl_order_tag,
            order_tag_id,
        ) = await calculate_scaled_order(
            maker,
            order_block=order_block,
            side=side,
            order_type_name=order_type_name,
            current_price=current_price,
            scale_from=scale_from,
            scale_to=scale_to,
            order_count=order_count,
            value_distribution_type=value_distribution_type,
            price_distribution_type=price_distribution_type,
            value_growth_factor=value_growth_factor,
            price_growth_factor=price_growth_factor,
            amount=amount,
            forced_amount=forced_amount,
            value=value,
            group_orders_settings=group_orders_settings,
            target_position=target_position,
            reduce_only=reduce_only,
            wait_for=wait_for,
        )
    except matrix_errors.MaximumOpenPositionReachedError:
        maker.ctx.logger.info(
            "Managed order cant open a new position. Maximum size reached"
        )
        return None, None, None, None, None, None, None
    created_orders = []
    take_profit_prices = []
    limit_fee, market_fee = position_sizing.get_fees(maker.ctx)
    entry_fee = limit_fee if order_type_name == "limit" else market_fee
    for order_index, entry_price in enumerate(entry_prices):
        exit_group = await group_orders_settings.create_managed_order_group(maker.ctx)
        (
            final_entry_tag,
            final_stop_loss_tag,
            final_take_profit_tag,
        ) = matrix_utilities.add_order_counter_to_tags(
            order_id=order_index,
            entry_order_tag=entry_order_tag or tag,
            bundled_tp_tag=tp_order_tag or take_profit_tag,
            bundled_sl_tag=sl_order_tag or stop_loss_tag,
        )
        (
            bundled_sl_offset,
            final_stop_loss_tag,
            bundled_sl_group,
        ) = order_placement.get_bundled_parameters(
            price=stop_loss_prices[order_index] if len(stop_loss_prices) else None,
            tag=final_stop_loss_tag,
            group=exit_group,
            is_bundled=True,
        )
        take_profit_price = take_profit.get_manged_order_take_profits(
            maker,
            order_block=order_block,
            take_profit_settings=group_orders_settings.take_profit,
            entry_side=side,
            current_price=current_price,
            entry_price=entry_price,
            stop_loss_price=stop_loss_prices[order_index]
            if len(stop_loss_prices)
            else None,
            entry_fee=entry_fee,
            market_fee=market_fee,
        )
        if take_profit_price:
            take_profit_prices.append(take_profit_price)
        (
            bundled_tp_offset,
            final_take_profit_tag,
            bundled_tp_group,
        ) = order_placement.get_bundled_parameters(
            price=take_profit_price,
            tag=final_take_profit_tag,
            group=exit_group,
            is_bundled=True,
        )
        this_order_type_name = order_type_name
        this_order_offset = f"@{entry_price}"
        this_entry_price = entry_price
        if force_enter_the_grid:
            if side == trading_enums.TradeOrderSide.SELL.value:
                if entry_price < current_price:
                    this_order_type_name = "market"
                    this_order_offset = None
                    this_entry_price = current_price

            else:
                if entry_price > current_price:
                    this_order_type_name = "market"
                    this_order_offset = None
                    this_entry_price = current_price
        if not order_preview_mode:
            created_order = None
            error = None
            error_message = ""
            try:
                new_created_order = await create_order.create_order_instance(
                    maker.ctx,
                    side=side,
                    symbol=symbol or maker.ctx.symbol,
                    order_amount=order_amounts[order_index],
                    order_type_name=this_order_type_name,
                    order_offset=this_order_offset,
                    stop_loss_offset=bundled_sl_offset or stop_loss_offset,
                    stop_loss_tag=final_stop_loss_tag,
                    stop_loss_group=bundled_sl_group or stop_loss_group,
                    stop_loss_type=stop_loss_type,
                    take_profit_offset=bundled_tp_offset or take_profit_offset,
                    take_profit_tag=final_take_profit_tag,
                    take_profit_group=bundled_tp_group or take_profit_group,
                    take_profit_type=take_profit_type,
                    slippage_limit=slippage_limit,
                    time_limit=time_limit,
                    reduce_only=reduce_only,
                    post_only=post_only,
                    # group=exit_order_group,
                    tag=final_entry_tag,
                    wait_for=wait_for,
                )
                created_order = new_created_order[0]
                created_orders.append(created_order)
                continue
            except IndexError as _error:
                error = _error
                error_message = "Order not created"
            except Exception as _error:
                error = _error
                error_message = f"{error}"
            if not created_order:
                created_order = {
                    "symbol": symbol or maker.ctx.symbol,
                    "order_amount": float(str(order_amounts[order_index])),
                    "order_type_name": this_order_type_name,
                    "order_offset": this_order_offset,
                    "entry_price": float(str(this_entry_price)),
                    "stop_loss_offset": bundled_sl_offset or stop_loss_offset,
                    "stop_loss_tag": final_stop_loss_tag,
                    "stop_loss_type": stop_loss_type,
                    "take_profit_offset": bundled_tp_offset or take_profit_offset,
                    "take_profit_tag": final_take_profit_tag,
                    "take_profit_type": take_profit_type,
                    "status": "rejected",
                    "status_message": f"failed_to_create: error: {error_message}",
                }
                maker.ctx.logger.warning(
                    f"Scaled {side} order failed to create order: {created_order} - "
                    f"error: {error_message}",
                )
            else:
                maker.ctx.logger.exception(
                    error, True, f"Scaled {side} order failed to create order"
                )
            created_orders.append(created_order)
    if exit_group and not order_preview_mode:
        await group_orders_settings.enable_managed_order_groups()
    return (
        created_orders,
        place_entries,
        entry_prices,
        stop_loss_prices,
        take_profit_prices,
        order_amounts,
        order_tag_id,
    )


async def calculate_scaled_order(
    maker,
    order_block,
    order_type_name,
    current_price,
    side=None,
    scale_from=None,
    scale_to=None,
    order_count=10,
    value_distribution_type=ScaledOrderValueDistributionTypes.FLAT,
    price_distribution_type=ScaledOrderPriceDistributionTypes.FLAT,
    value_growth_factor=2,
    price_growth_factor=2,
    # either amount, value, target_position or position_size_calculator
    amount=None,
    forced_amount: decimal.Decimal = None,
    value: decimal.Decimal = None,  # value in ref market
    group_orders_settings=None,
    target_position=None,
    # stop_loss_calculator=None,
    reduce_only=False,
    wait_for=None,
):
    total_amount = None
    unknown_portfolio_on_creation = wait_for is not None

    if (amount is not None and side is not None) and (
        target_position is None and value is None and group_orders_settings is None
    ):
        total_amount = await position_size.get_amount(
            maker.ctx,
            amount,
            side=side,
            use_total_holding=True,
            unknown_portfolio_on_creation=unknown_portfolio_on_creation,
        )

    elif target_position is not None and (
        amount is None
        and side is None
        and value is None
        and group_orders_settings is None
    ):
        total_amount, side = await position_size.get_target_position(
            maker.ctx,
            target_position,
            reduce_only=reduce_only,
            unknown_portfolio_on_creation=unknown_portfolio_on_creation,
        )
    elif (value is not None and side is not None) and (
        amount is None and target_position is None and group_orders_settings is None
    ):
        pass
    elif (group_orders_settings is not None and side is not None) and (
        amount is None and target_position is None and value is None
    ):
        pass

    else:
        raise RuntimeError(
            "Scaled order supports either (side with amount), (target_position), "
            "(side with position_size_calculator) or "
            "(side with value in reference market). "
            "Not required parameters must be set to none "
        )

    scale_from_price = await offsets.get_offset(maker.ctx, scale_from, side=side)
    scale_to_price = await offsets.get_offset(maker.ctx, scale_to, side=side)
    normalized_scale_from_price, normalized_scale_to_price = get_normalized_scale(
        scale_from_price, scale_to_price, side
    )

    # price_distribution_types
    entry_prices: list = []
    stop_loss_prices: list = []
    stop_loss_percents: list = []
    filled_entry_prices: list = []
    distance_factors: list = []
    place_entries: bool = False
    if price_distribution_type == "linear_growth":
        distance_factors = calculate_linear_growth(
            float(str(price_growth_factor)),
            1,
            # - one because start is given
            order_count - 1,
        )
        total_factor = decimal.Decimal(str(sum(distance_factors)))
        from_to_distance = normalized_scale_to_price - normalized_scale_from_price
        prev_price = normalized_scale_from_price
        entry_prices.append(normalized_scale_from_price)
        await get_stop_loss_from_group_settings(
            group_orders_settings=group_orders_settings,
            order_block=order_block,
            side=side,
            entry_price=normalized_scale_from_price,
            current_price=current_price,
            filled_entry_prices=filled_entry_prices,
            maker=maker,
            stop_loss_prices=stop_loss_prices,
            stop_loss_percents=stop_loss_percents,
        )
        for factor in distance_factors:
            multiplier = 100 / total_factor  # 100%
            percent_of_total_factor = (decimal.Decimal(str(factor)) * multiplier) / 100
            entry_prices.append(
                (percent_of_total_factor * from_to_distance) + prev_price
            )
            prev_price = entry_prices[-1]
            await get_stop_loss_from_group_settings(
                group_orders_settings=group_orders_settings,
                order_block=order_block,
                side=side,
                entry_price=entry_prices[-1],
                current_price=current_price,
                filled_entry_prices=filled_entry_prices,
                maker=maker,
                stop_loss_prices=stop_loss_prices,
                stop_loss_percents=stop_loss_percents,
            )

    elif price_distribution_type == "flat":
        (
            entry_prices,
            stop_loss_prices,
            filled_entry_prices,
            stop_loss_percents,
        ) = await calculate_flat_distribution(
            normalized_scale_from_price,
            normalized_scale_to_price,
            order_count,
            side,
            group_orders_settings,
            current_price,
            maker,
            order_block,
        )
    else:
        raise RuntimeError(
            "scaled order: unsupported amount_of_orders_distribution_type. "
            "check the documentation for more informations"
        )
    # value_distribution_types
    order_amounts: list = []
    order_tag_id = None
    if value_distribution_type == "flat":
        # distance_factors = [1] * order_count
        if value:
            value_per_order = value / order_count
            for price in entry_prices:
                order_amounts.append(value_per_order / price)
        elif total_amount:
            amount_per_order = total_amount / order_count
            order_amounts = [amount_per_order] * order_count
        elif group_orders_settings:
            # get average entry for the position site calculator
            tmp_total_value = 1000
            tmp_value_per_order = decimal.Decimal(str(tmp_total_value / order_count))
            tmp_total_quantity = 0
            stop_loss_total_value = 0
            for order_index, entry_price in enumerate(entry_prices):
                this_quantity = entry_price / tmp_value_per_order
                tmp_total_quantity += this_quantity
                if stop_loss_prices:
                    stop_loss_total_value += (
                        stop_loss_prices[order_index] * this_quantity
                    )
            try:
                average_entry_price = tmp_total_value / tmp_total_quantity
            except ZeroDivisionError as error:
                raise RuntimeError(
                    "Scaled order failed to determine the average entry price"
                ) from error
            average_stop_loss_percentage = None
            if stop_loss_total_value:
                average_stop_loss_price = stop_loss_total_value / tmp_total_quantity
                average_stop_loss_percentage = convert_sl_price_to_percent(
                    side, average_entry_price, stop_loss_price=average_stop_loss_price
                )
            (
                total_amount,
                max_position_size,
                current_open_risk,
                max_buying_power,
                place_entries,
                entry_order_tag,
                tp_order_tag,
                sl_order_tag,
                order_tag_id,
            ) = await position_sizing.get_manged_order_position_size(
                maker=maker,
                position_size_settings=group_orders_settings.position_size,
                trading_side=trading_enums.PositionSide.SHORT.value
                if side == trading_enums.TradeOrderSide.SELL.value
                else trading_enums.PositionSide.LONG.value,
                entry_side=side,
                entry_price=average_entry_price,
                entry_order_type=order_type_name,
                stop_loss_percent=average_stop_loss_percentage,
                order_tag_prefix=group_orders_settings.order_tag_prefix,
                recreate_exits=False,
                forced_amount=forced_amount,
            )
            order_amounts = [total_amount / order_count] * order_count
        else:
            raise RuntimeError("Scaled order failed to determine the position size")
    elif value_distribution_type in (
        ScaledOrderValueDistributionTypes.LINEAR_GROWTH,
        ScaledOrderValueDistributionTypes.EXPONENTIAL,
    ):
        (
            order_values,
            entry_order_tag,
            tp_order_tag,
            sl_order_tag,
            order_tag_id,
            place_entries,
        ) = await calculate_scaled_growth_orders(
            maker,
            side=side,
            total_value=value,
            total_amount=total_amount,
            group_orders_settings=group_orders_settings,
            order_type_name=order_type_name,
            entry_prices=entry_prices,
            amount_of_orders=order_count,
            growth_factor=value_growth_factor,
            growth_type=value_distribution_type,
            power=15,
            stop_loss_prices=stop_loss_prices,
        )

        if value:
            for index, price in enumerate(entry_prices):
                order_amounts.append(order_values[index] / price)
        else:
            order_amounts = order_values
    else:
        raise RuntimeError(
            "scaled order: unsupported value_distribution_type. "
            "check the documentation for more informations"
        )
    return (
        entry_prices,
        stop_loss_prices,
        order_amounts,
        place_entries,
        entry_order_tag,
        tp_order_tag,
        sl_order_tag,
        order_tag_id,
    )


async def get_stop_loss_from_group_settings(
    group_orders_settings,
    order_block,
    side,
    entry_price,
    current_price,
    filled_entry_prices,
    maker,
    stop_loss_prices,
    stop_loss_percents,
) -> list:
    if group_orders_settings:
        if side == "buy":
            entry_price = entry_price if entry_price < current_price else current_price
        else:
            entry_price = entry_price if entry_price > current_price else current_price
        filled_entry_prices.append(entry_price)
        stop_loss_price, stop_loss_percent = await stop_loss.get_manged_order_stop_loss(
            maker=maker,
            order_block=order_block,
            stop_loss_settings=group_orders_settings.stop_loss,
            trading_side=side,
            entry_price=entry_price,
            current_price=current_price,
        )
        if stop_loss_price is not None:
            stop_loss_prices.append(stop_loss_price)
            stop_loss_percents.append(stop_loss_percent)


def calculate_linear_growth(scale_from, scale_to, order_count) -> list:
    _growth_array = numpy.linspace(
        start=scale_from,
        stop=scale_to,
        num=order_count,
        dtype=float,
    )
    return _growth_array


async def calculate_flat_distribution(
    scale_from,
    scale_to,
    count: int,
    side: str,
    group_orders_settings,
    current_price,
    maker,
    order_block,
) -> list:
    entry_prices = []
    stop_loss_prices = []
    filled_entry_prices = []
    stop_loss_percents = []
    if scale_from >= scale_to:
        price_difference = scale_from - scale_to
        step_size = price_difference / (count - 1)
        for i in range(0, count):
            entry_prices.append(scale_from - (step_size * i))
            await get_stop_loss_from_group_settings(
                group_orders_settings=group_orders_settings,
                order_block=order_block,
                side=side,
                entry_price=entry_prices[-1],
                current_price=current_price,
                filled_entry_prices=filled_entry_prices,
                maker=maker,
                stop_loss_prices=stop_loss_prices,
                stop_loss_percents=stop_loss_percents,
            )
    elif scale_to > scale_from:
        price_difference = scale_to - scale_from
        step_size = price_difference / (count - 1)
        for i in range(0, count):
            entry_prices.append(scale_from + (step_size * i))
            await get_stop_loss_from_group_settings(
                group_orders_settings=group_orders_settings,
                order_block=order_block,
                side=side,
                entry_price=entry_prices[-1],
                current_price=current_price,
                filled_entry_prices=filled_entry_prices,
                maker=maker,
                stop_loss_prices=stop_loss_prices,
                stop_loss_percents=stop_loss_percents,
            )
    return entry_prices, stop_loss_prices, filled_entry_prices, stop_loss_percents


def get_normalized_scale(scale_from_price, scale_to_price, side) -> tuple:
    normalized_scale_from_price: decimal.Decimal = None
    normalized_scale_to_price: decimal.Decimal = None
    if scale_from_price == scale_to_price:
        raise RuntimeError("scale_from_price and scale_to_price cant be the same")
    if scale_from_price > scale_to_price:
        if side == "buy":
            # from is higher
            normalized_scale_from_price = scale_from_price
            # to is lower
            normalized_scale_to_price = scale_to_price
        else:  # sell
            # from is lower
            normalized_scale_from_price = scale_to_price
            # to is higher
            normalized_scale_to_price = scale_from_price
    elif scale_to_price > scale_from_price:
        if side == "buy":
            # from is higher
            normalized_scale_from_price = scale_to_price
            # to is lower
            normalized_scale_to_price = scale_from_price
        else:  # sell
            # from is lower
            normalized_scale_from_price = scale_from_price
            # to is higher
            normalized_scale_to_price = scale_to_price
    return (
        normalized_scale_from_price,
        normalized_scale_to_price,
    )


async def calculate_scaled_growth_orders(
    maker,
    side: str,
    total_value: decimal.Decimal = None,
    total_amount: decimal.Decimal = None,
    group_orders_settings=None,
    order_type_name: str = "limit",
    amount_of_orders: int = 10,
    growth_factor: float = 2,
    growth_type="linear_growth",
    power: int = 15,
    stop_loss_prices: list = None,
    entry_prices: list = None,
):
    SUM_OF_ARRAY = 100
    _array_start = SUM_OF_ARRAY / amount_of_orders
    _array_end = (SUM_OF_ARRAY / amount_of_orders) * float(str(growth_factor))
    if growth_type == "linear_growth":
        _growth_array = calculate_linear_growth(
            _array_start, _array_end, amount_of_orders
        )
    elif growth_type == "exponential":

        def func(x, adj1, adj2):
            return ((x + adj1) ** power) * adj2

        # two given datapoints to which the exponential
        # function with power pw should fit
        x = [
            _array_start,
            _array_end,
        ]
        y = [1, amount_of_orders]

        A = numpy.exp(numpy.log(y[0] / y[1]) / power)
        a = (x[0] - x[1] * A) / (A - 1)
        b = y[0] / (x[0] + a) ** power
        xf = numpy.linspace(1, amount_of_orders, amount_of_orders)
        _growth_array = func(xf, a, b)
    else:
        # Handle other growth types here
        raise NotImplementedError()

    growth_array_sum = 0
    growth_deci_array = []
    for number in _growth_array:
        growth_deci_array.append(decimal.Decimal(str(number)))
        growth_array_sum += growth_deci_array[-1]
    order_tag_id = None
    if group_orders_settings:
        # get average entry for the position site calculator
        tmp_total_quantity = 0
        stop_loss_total_value = 0
        for order_index, entry_price in enumerate(entry_prices):
            this_quantity = growth_deci_array[order_index] / entry_price
            tmp_total_quantity += this_quantity
            if len(stop_loss_prices):
                stop_loss_total_value += stop_loss_prices[order_index] * this_quantity
        try:
            average_entry_price = growth_array_sum / tmp_total_quantity
        except ZeroDivisionError as error:
            raise RuntimeError(
                "Scaled order failed to determine the average entry price"
            ) from error
        average_stop_loss_percentage = None
        if stop_loss_total_value:
            average_stop_loss_price = stop_loss_total_value / tmp_total_quantity
            average_stop_loss_percentage = convert_sl_price_to_percent(
                side, average_entry_price, stop_loss_price=average_stop_loss_price
            )
        (
            total_amount,
            max_position_size,
            current_open_risk,
            max_buying_power,
            place_entries,
            entry_order_tag,
            tp_order_tag,
            sl_order_tag,
            order_tag_id,
        ) = await position_sizing.get_manged_order_position_size(
            maker=maker,
            position_size_settings=group_orders_settings.position_size,
            trading_side=trading_enums.PositionSide.SHORT.value
            if side == trading_enums.TradeOrderSide.SELL.value
            else trading_enums.PositionSide.LONG.value,
            entry_side=side,
            entry_price=average_entry_price,
            entry_order_type=order_type_name,
            stop_loss_percent=average_stop_loss_percentage,
            order_tag_prefix=group_orders_settings.order_tag_prefix,
            recreate_exits=False,
        )

    normalized_amount = []
    for number in growth_deci_array:
        normalized_amount.append(
            total_amount * ((number / (growth_array_sum / 100)) / 100)
        )
    return (
        normalized_amount,
        entry_order_tag,
        tp_order_tag,
        sl_order_tag,
        order_tag_id,
        place_entries,
    )


def convert_sl_price_to_percent(
    side, entry_price: decimal.Decimal, stop_loss_price: decimal.Decimal
) -> decimal.Decimal:
    if side == "buy":
        return (entry_price - stop_loss_price) / (entry_price / 100)
    else:
        return (stop_loss_price - entry_price) / (entry_price / 100)
