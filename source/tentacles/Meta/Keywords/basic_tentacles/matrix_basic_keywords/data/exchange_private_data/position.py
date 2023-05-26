import decimal
import octobot_commons.symbols.symbol_util as symbol_util
import octobot_trading.modes.script_keywords.context_management as context_management


def get_position_size(ctx: context_management.Context) -> decimal.Decimal:
    if ctx.exchange_manager.is_future:
        try:
            return (
                ctx.exchange_manager.exchange_personal_data.positions_manager.positions[
                    ctx.symbol
                ].size
            )
        except KeyError:
            return decimal.Decimal("0")
    currency = symbol_util.parse_symbol(ctx.symbol).base
    portfolio = ctx.exchange_manager.exchange_personal_data.portfolio_manager.portfolio
    return portfolio.get_currency_portfolio(currency).total
