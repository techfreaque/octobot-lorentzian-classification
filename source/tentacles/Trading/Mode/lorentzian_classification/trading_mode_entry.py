import typing
from tulipy import InvalidOptionError

import octobot_commons.logging as logging
import octobot_trading.enums as trading_enums
import octobot_trading.modes.script_keywords.context_management as context_management
import tentacles.Meta.Keywords.basic_tentacles.basic_modes.scripted_trading_mode.use_scripted_trading_mode as use_scripted_trading_mode
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.matrix_enums as matrix_enums

import tentacles.Trading.Mode.lorentzian_classification.classification as classification
import tentacles.Trading.Mode.lorentzian_classification.settings as settings


class LorentzianClassificationMode(settings.LorentzianClassificationModeInputs):
    ENABLE_PRO_FEATURES = False

    def __init__(self, config, exchange_manager):
        super().__init__(config, exchange_manager)
        self.producer = LorentzianClassificationProducer
        if exchange_manager:
            # allow scripted trading if a
            #   profile_trading_script.py is in the current profile
            use_scripted_trading_mode.initialize_scripted_trading_mode(self)
        else:
            logging.get_logger(self.get_name()).error(
                "At least one exchange must be enabled "
                "to use LorentzianClassificationMode"
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
    async def make_strategy(
        self,
        ctx: context_management.Context,
        action: str,
        action_data: typing.Optional[dict] = None,
    ):
        self.action = action
        if matrix_enums.TradingModeCommands.INIT_CALL != action:
            self.allow_trading_only_on_execution(ctx)
            try:
                await self.evaluate_lorentzian_classification(
                    ctx=ctx,
                )
            except InvalidOptionError as error:
                ctx.logger.exception(
                    error,
                    True,
                    "Failed generate Filters or Features. "
                    "Most likely due to not enough available historical bars. "
                    "Check the historical bars in the TimeFrameStrategyEvaluator "
                    "settings",
                )
