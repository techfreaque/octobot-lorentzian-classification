import octobot_commons.logging as logging
import octobot_trading.enums as trading_enums
import tentacles.Trading.Mode.lorentzian_classification.classification as classification
import tentacles.Trading.Mode.lorentzian_classification.settings as settings


class LorentzianClassificationMode(settings.LorentzianClassificationModeInputs):
    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        self.producer = LorentzianClassificationProducer
        if exchange_manager:
            try:
                import backtesting_script

                self.register_script_module(backtesting_script, live=False)
            except (AttributeError, ModuleNotFoundError):
                pass
            try:
                import profile_trading_script

                self.register_script_module(profile_trading_script)
            except (AttributeError, ModuleNotFoundError):
                pass
        else:
            logging.get_logger(self.get_name()).error(
                "At least one exchange must be enabled to use LorentzianClassificationMode"
            )

    def get_mode_producer_classes(self) -> list:
        return [LorentzianClassificationProducer]

    @classmethod
    def get_supported_exchange_types(cls) -> list:
        """
        :return: The list of supported exchange types
        """
        return [
            trading_enums.ExchangeTypes.SPOT,
            trading_enums.ExchangeTypes.FUTURE,
        ]


class LorentzianClassificationProducer(classification.LorentzianClassificationScript):
    async def _pre_script_call(self, context, action: dict or str = None) -> None:
        self.action = action
        await self.evaluate_lorentzian_classification(
            ctx=context,
        )
