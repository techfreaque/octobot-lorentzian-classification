import typing


class AbstractRunAnalysisMode:
    available_run_analyzer_plot_modules: dict = None
    available_run_analyzer_table_modules: dict = None
    available_run_analyzer_module_names: list = None
    selected_run_analyzer_module_names: list = None

    @staticmethod
    def init_user_inputs(
        cls, analysis_mode_plugin, inputs: dict, parent_input_name: str
    ) -> None:
        """
        all analysis mode inputs including analysis evaluators should be defined here
        """

    @classmethod
    async def get_and_execute_run_analysis_mode(
        cls,
        trading_mode_class,
        config: dict,
        exchange_name: str,
        symbol: str,
        time_frame: str,
        backtesting_id: typing.Optional[int] = None,
        optimizer_id: typing.Optional[int] = None,
        live_id: typing.Optional[int] = None,
        optimization_campaign: typing.Optional[str] = None,
    ):
        """
        all analysis mode logic should be defined here
        """
