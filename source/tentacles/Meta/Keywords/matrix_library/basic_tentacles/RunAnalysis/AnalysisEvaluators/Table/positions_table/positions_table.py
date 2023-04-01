import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.BaseDataProvider.default_base_data_provider.base_data_provider as base_data_provider
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.RunAnalysisFactory.abstract_analysis_evaluator as abstract_analysis_evaluator


class PositionsTable(abstract_analysis_evaluator.AnalysisEvaluator):
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


async def plot_positions_table(
    run_data: base_data_provider.RunAnalysisBaseDataGenerator, plotted_element
):
    import tentacles.Meta.Keywords.scripting_library.run_analysis.run_analysis_plots as run_analysis_plots

    realized_pnl_history = await run_data.load_spot_or_futures_base_data(
        transaction_types=(
            trading_enums.TransactionType.REALIZED_PNL.value,
            trading_enums.TransactionType.CLOSE_REALIZED_PNL.value,
        )
    )
    key_to_label = {
        "x": "Exit time",
        "first_entry_time": "Entry time",
        "average_entry_price": "Average entry price",
        "average_exit_price": "Average exit price",
        "cumulated_closed_quantity": "Cumulated closed quantity",
        "realized_pnl": "Realized PNL",
        "side": "Side",
        "trigger_source": "Closed by",
    }

    run_analysis_plots.plot_table_data(
        realized_pnl_history, plotted_element, "Positions", key_to_label, [], None
    )
