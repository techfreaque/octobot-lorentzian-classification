import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.AnalysisKeywords.common_user_inputs as common_user_inputs
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.BaseDataProvider.default_base_data_provider.base_data_provider as base_data_provider
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.RunAnalysisFactory.abstract_analysis_evaluator as abstract_analysis_evaluator


class HistoricalFees(abstract_analysis_evaluator.AnalysisEvaluator):
    HISTORICAL_FEES_NAME = "historical_fees"
    HISTORICAL_FEES_TITLE = "Historical Fees"

    @classmethod
    def init_user_inputs(
        cls, analysis_mode_plugin, inputs: dict, parent_input_name: str
    ) -> None:
        common_user_inputs.init_data_source_settings(
            data_source_input_name=cls.HISTORICAL_FEES_NAME,
            data_source_input_title=cls.HISTORICAL_FEES_TITLE,
            analysis_mode_plugin=analysis_mode_plugin,
            inputs=inputs,
            parent_input_name=parent_input_name,
            default_chart_location="sub-chart",
        )

    async def evaluate(
        self,
        run_data: base_data_provider.RunAnalysisBaseDataGenerator,
        analysis_type: str,
    ):
        plotted_element = common_user_inputs.get_plotted_element_based_on_settings(
            run_data,
            analysis_type=analysis_type,
            data_source_input_name=self.HISTORICAL_FEES_NAME,
            default_chart_location="sub-chart",
        )
        if plotted_element is not None:
            own_yaxis: bool = True
            fees_for_each_symbol = False
            trading_fees = False
            funding_fees = False
            total_fees = True

            fees_by_title = calculate_historical_fees(
                run_data,
                trading_fees,
                funding_fees,
                total_fees,
                fees_for_each_symbol,
            )
            for fee_title, data in fees_by_title.items():
                plotted_element.plot(
                    mode="scatter",
                    x=data["times"],
                    y=data["cumulative_fees"],
                    title=fee_title,
                    own_yaxis=own_yaxis,
                    line_shape="hv",
                )

    # if funding_fees and run_data.trading_type == "future":
    #     await run_data.load_grouped_funding_fees()
    #     for currency, fees in run_data.funding_fees_history_by_pair.items():
    #         cumulative_fees = []
    #         previous_fee = 0
    #         for fee in fees:
    #             cumulated_fee = fee["quantity"] + previous_fee
    #             cumulative_fees.append(cumulated_fee)
    #             previous_fee = cumulated_fee
    #         plotted_element.plot(
    #             mode="scatter",
    #             x=[fee[commons_enums.PlotAttributes.X.value] for fee in fees],
    #             y=cumulative_fees,
    #             title=f"{currency} paid funding fees",
    #             own_yaxis=own_yaxis,
    #             line_shape="hv",
    #         )
    # if total_fees:
    #     pass


def calculate_historical_fees(
    run_data: base_data_provider.RunAnalysisBaseDataGenerator,
    trading_fees: bool,
    funding_fees: bool,
    total_fees: bool,
    fees_for_each_symbol: bool,
) -> dict:
    fees_by_title = {}
    # for transaction in run_data.trading_transactions_history:
    #     if trading_fees:
    #         pass
    #     if funding_fees:
    #         pass
    #     if total_fees:
    #         pass
    #     if fees_for_each_symbol:
    #         pass

    return fees_by_title
