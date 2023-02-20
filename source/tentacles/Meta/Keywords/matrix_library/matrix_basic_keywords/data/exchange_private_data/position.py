import octobot_commons.symbols.symbol_util as symbol_util


def get_position_size(ctx):
    if ctx.exchange_manager.is_future:
        try:
            return (
                ctx.exchange_manager.exchange_personal_data.positions_manager.positions[
                    ctx.symbol
                ].size
            )
        except KeyError:
            return 0
    currency = symbol_util.parse_symbol(ctx.symbol).base
    portfolio = ctx.exchange_manager.exchange_personal_data.portfolio_manager.portfolio
    return portfolio.get_currency_portfolio(currency).total
