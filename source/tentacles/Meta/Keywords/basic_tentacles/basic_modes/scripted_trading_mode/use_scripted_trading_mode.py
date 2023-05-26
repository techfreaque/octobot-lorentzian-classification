def initialize_scripted_trading_mode(trading_mode)->bool:
    try:
        import backtesting_script

        trading_mode.register_script_module(backtesting_script, live=False)
    except (AttributeError, ModuleNotFoundError):
        pass
    try:
        import profile_trading_script
        trading_mode.register_script_module(profile_trading_script)
        return True
    except (AttributeError, ModuleNotFoundError):
        return False
