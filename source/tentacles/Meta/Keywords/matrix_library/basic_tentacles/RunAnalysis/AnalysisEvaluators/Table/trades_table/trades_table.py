import octobot_commons.enums as commons_enums
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.BaseDataProvider.default_base_data_provider.base_data_provider as base_data_provider
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.RunAnalysisFactory.abstract_analysis_evaluator as abstract_analysis_evaluator


class TradesTable(abstract_analysis_evaluator.AnalysisEvaluator):
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


async def plot_trades_table(meta_database, plotted_element):
    import tentacles.Meta.Keywords.scripting_library.run_analysis.run_analysis_plots as run_analysis_plots

    data = await meta_database.get_trades_db().all(commons_enums.DBTables.TRADES.value)
    key_to_label = {
        "y": "Price",
        "type": "Type",
        "side": "Side",
    }
    additional_columns = [
        {"field": "total", "label": "Total", "render": None},
        {"field": "fees", "label": "Fees", "render": None},
    ]

    def datum_columns_callback(datum):
        datum["total"] = datum["cost"]
        datum["fees"] = f'{datum["fees_amount"]} {datum["fees_currency"]}'

    run_analysis_plots.plot_table_data(
        data,
        plotted_element,
        commons_enums.DBTables.TRADES.value,
        key_to_label,
        additional_columns,
        datum_columns_callback,
    )
