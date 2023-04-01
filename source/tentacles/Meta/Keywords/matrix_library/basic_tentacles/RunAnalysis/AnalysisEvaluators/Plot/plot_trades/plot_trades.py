import octobot_commons.enums as commons_enums

import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.AnalysisKeywords.common_user_inputs as common_user_inputs
from tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.AnalysisKeywords.plot_keywords import plot_from_standard_data
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.BaseDataProvider.default_base_data_provider.base_data_provider as base_data_provider
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.RunAnalysisFactory.abstract_analysis_evaluator as abstract_analysis_evaluator


class PlotTrades(abstract_analysis_evaluator.AnalysisEvaluator):
    PLOT_TRADES_NAME = "_trades"
    PLOT_TRADES_TILE = "Trades"

    @classmethod
    def init_user_inputs(
        cls, analysis_mode_plugin, inputs: dict, parent_input_name: str
    ) -> None:
        common_user_inputs.init_data_source_settings(
            data_source_input_name=parent_input_name + cls.PLOT_TRADES_NAME,
            data_source_input_title=cls.PLOT_TRADES_TILE,
            analysis_mode_plugin=analysis_mode_plugin,
            inputs=inputs,
            parent_input_name=parent_input_name,
            default_chart_location="main-chart",
            default_data_source_enabled=True,
        )

    async def evaluate(
        self,
        run_data: base_data_provider.RunAnalysisBaseDataGenerator,
        analysis_type: str,
    ):
        plotted_element = common_user_inputs.get_plotted_element_based_on_settings(
            run_data,
            analysis_type=analysis_type,
            data_source_input_name=self.PLOT_TRADES_NAME,
            default_chart_location="main-chart",
        )
        if plotted_element is not None:
            # TODO add symols filter
            trades = await run_data.get_trades()
            plot_from_standard_data(trades, plotted_element, title="Trades")