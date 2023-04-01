import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.BaseDataProvider.default_base_data_provider.base_data_provider as base_data_provider
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.RunAnalysisFactory.abstract_analysis_evaluator as abstract_analysis_evaluator


class RealizedPortfolioValue(abstract_analysis_evaluator.AnalysisEvaluator):
    @classmethod
    def init_user_inputs(
        cls, analysis_mode_plugin, inputs: dict, parent_input_name: str
    ) -> None:
        """
        define all settings for your AnalysisEvaluator
        """

    async def evaluate(
        self,
        run_data: base_data_provider.RunAnalysisBaseDataGenerator,
        analysis_type: str,
    ):
        pass


async def plot_realized_portfolio_value(
    run_data: base_data_provider.RunAnalysisBaseDataGenerator,
    plotted_element,
    x_as_trade_count: bool = True,
    own_yaxis: bool = False,
):
    await run_data.load_realized_pnl(x_as_trade_count)
    plotted_element.plot(
        mode="scatter",
        x=run_data.realized_pnl_x_data,
        y=run_data.realized_pnl_cumulative,
        x_type="tick0" if x_as_trade_count else "date",
        title="Realized portfolio value",
        own_yaxis=own_yaxis,
        line_shape="hv",
    )
