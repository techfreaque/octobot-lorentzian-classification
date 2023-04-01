import octobot_commons.enums as commons_enums

import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.AnalysisKeywords.common_user_inputs as common_user_inputs
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.BaseDataProvider.default_base_data_provider.base_data_provider as base_data_provider
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.RunAnalysisFactory.abstract_analysis_evaluator as abstract_analysis_evaluator


class PlotCandles(abstract_analysis_evaluator.AnalysisEvaluator):
    PLOT_CANDLES_NAME = "_candles"
    PLOT_CANDLES_TILE = "Candles"

    @classmethod
    def init_user_inputs(
        cls, analysis_mode_plugin, inputs: dict, parent_input_name: str
    ) -> None:
        common_user_inputs.init_data_source_settings(
            data_source_input_name=parent_input_name + cls.PLOT_CANDLES_NAME,
            data_source_input_title=cls.PLOT_CANDLES_TILE,
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
            data_source_input_name=self.PLOT_CANDLES_NAME,
            default_chart_location="main-chart",
        )
        if plotted_element is not None:
            candles = await run_data.get_candles(
                run_data.ctx.symbol, run_data.ctx.time_frame
            )
            plotted_element.plot(
                x=list(candles[commons_enums.PriceIndexes.IND_PRICE_TIME.value]),
                open=list(candles[commons_enums.PriceIndexes.IND_PRICE_OPEN.value]),
                high=list(candles[commons_enums.PriceIndexes.IND_PRICE_HIGH.value]),
                low=list(candles[commons_enums.PriceIndexes.IND_PRICE_LOW.value]),
                close=list(candles[commons_enums.PriceIndexes.IND_PRICE_CLOSE.value]),
                volume=list(candles[commons_enums.PriceIndexes.IND_PRICE_VOL.value]),
                x_type="date",
                title=f"Candles {run_data.ctx.symbol} {run_data.ctx.time_frame}",
                own_yaxis=False,
                kind="candlestick",
                mode="lines",
            )
