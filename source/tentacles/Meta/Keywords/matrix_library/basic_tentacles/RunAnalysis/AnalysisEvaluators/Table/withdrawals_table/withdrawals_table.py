import octobot_trading.enums as trading_enums
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.BaseDataProvider.default_base_data_provider.base_data_provider as base_data_provider
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.RunAnalysisFactory.abstract_analysis_evaluator as abstract_analysis_evaluator


class WithdrawalsTable(abstract_analysis_evaluator.AnalysisEvaluator):
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


async def plot_withdrawals_table(
    run_data: base_data_provider.RunAnalysisBaseDataGenerator, plotted_element
):
    import tentacles.Meta.Keywords.scripting_library.run_analysis.run_analysis_plots as run_analysis_plots

    withdrawal_history = await run_data.load_spot_or_futures_base_data(
        transaction_types=(trading_enums.TransactionType.BLOCKCHAIN_WITHDRAWAL.value,)
    )

    # apply quantity to y for each withdrawal
    for withdrawal in withdrawal_history:
        withdrawal["y"] = withdrawal["quantity"]
    key_to_label = {
        "y": "Quantity",
        "currency": "Currency",
        "side": "Side",
    }
    additional_columns = []

    run_analysis_plots.plot_table_data(
        withdrawal_history,
        plotted_element,
        "Withdrawals",
        key_to_label,
        additional_columns,
        None,
    )
