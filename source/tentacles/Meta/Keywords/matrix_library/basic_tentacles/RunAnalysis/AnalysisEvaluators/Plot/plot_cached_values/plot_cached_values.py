import octobot_commons.enums as commons_enums
import octobot_commons.errors as commons_errors
import octobot_commons.constants as commons_constants
import octobot_commons.databases as databases

import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.AnalysisKeywords.common_user_inputs as common_user_inputs
from tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.AnalysisKeywords.plot_keywords import (
    plot_from_standard_data,
)
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.BaseDataProvider.default_base_data_provider.base_data_provider as base_data_provider
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.RunAnalysisFactory.abstract_analysis_evaluator as abstract_analysis_evaluator


class PlotCachedValues(abstract_analysis_evaluator.AnalysisEvaluator):
    PLOT_CACHED_VALUES_NAME = "_cached_values"
    PLOT_CACHED_VALUES_TITLE = "Cached Values"

    @classmethod
    def init_user_inputs(
        cls, analysis_mode_plugin, inputs: dict, parent_input_name: str
    ) -> None:
        common_user_inputs.init_data_source_settings(
            data_source_input_name=parent_input_name + cls.PLOT_CACHED_VALUES_NAME,
            data_source_input_title=cls.PLOT_CACHED_VALUES_TITLE,
            analysis_mode_plugin=analysis_mode_plugin,
            inputs=inputs,
            parent_input_name=parent_input_name,
            default_data_source_enabled=True,
        )

    async def evaluate(
        self,
        run_data: base_data_provider.RunAnalysisBaseDataGenerator,
        analysis_type: str,
    ):
        if common_user_inputs.get_is_data_source_enabled(
            run_data,
            parent_input_name=self.PLOT_CACHED_VALUES_NAME,
            def_val=True,
            analysis_type=analysis_type,
        ):
            main_plotted_element = run_data.get_plotted_element("main-chart")
            sub_plotted_element = run_data.get_plotted_element("sub-chart")
            cached_values_metadata = await run_data.get_cached_values(
                run_data.ctx.symbol
            )
            for cached_value_metadata in cached_values_metadata:
                if (
                    cached_value_metadata.get(
                        commons_enums.DBRows.TIME_FRAME.value, None
                    )
                    == run_data.ctx.time_frame
                ):
                    try:
                        chart = cached_value_metadata[
                            commons_enums.DisplayedElementTypes.CHART.value
                        ]
                        plotted_element = None
                        if chart == "main-chart":
                            plotted_element = main_plotted_element
                        elif chart == "sub-chart":
                            plotted_element = sub_plotted_element
                        else:
                            continue
                        x_shift = cached_value_metadata["x_shift"]
                        values = sorted(
                            await _get_cached_values_to_display(
                                run_data.logger,
                                cached_value_metadata,
                                x_shift,
                                run_data.start_time,
                                run_data.end_time,
                            ),
                            key=lambda x: x[commons_enums.PlotAttributes.X.value],
                        )
                        values[0] = {**cached_value_metadata, **values[0]}
                        plot_from_standard_data(
                            data_set=values,
                            plotted_element=plotted_element,
                            title=cached_value_metadata["title"],
                        )
                    except Exception as error:
                        run_data.logger.exception(
                            error,
                            True,
                            "Failed to plot cached values for "
                            f"{cached_value_metadata.get('title', '')}",
                        )


async def _get_cached_values_to_display(
    logger, cached_value_metadata, x_shift, start_time, end_time
):
    # unmodified version from displayed_elements
    cache_file = cached_value_metadata[commons_enums.PlotAttributes.VALUE.value]
    cache_displayed_value = plotted_displayed_value = cached_value_metadata[
        "cache_value"
    ]
    kind = cached_value_metadata[commons_enums.PlotAttributes.KIND.value]
    mode = cached_value_metadata[commons_enums.PlotAttributes.MODE.value]
    own_yaxis = cached_value_metadata[commons_enums.PlotAttributes.OWN_YAXIS.value]
    line_shape = cached_value_metadata["line_shape"]
    condition = cached_value_metadata.get("condition", None)
    try:
        cache_database = databases.CacheDatabase(cache_file)
        cache_type = (await cache_database.get_metadata())[
            commons_enums.CacheDatabaseColumns.TYPE.value
        ]
        if cache_type == databases.CacheTimestampDatabase.__name__:
            cache = await cache_database.get_cache()
            for cache_val in cache:
                try:
                    if isinstance(cache_val[cache_displayed_value], bool):
                        plotted_displayed_value = _get_cache_displayed_value(
                            cache_val, cache_displayed_value
                        )
                        if plotted_displayed_value is None:
                            logger.error(
                                f"Impossible to plot {cache_displayed_value}: "
                                "unset y axis value"
                            )
                            return []
                    else:
                        break
                except KeyError:
                    pass
                except Exception as e:
                    print(e)
            plotted_values = []
            for values in cache:
                try:
                    if condition is None or condition == values[cache_displayed_value]:
                        x = (
                            values[commons_enums.CacheDatabaseColumns.TIMESTAMP.value]
                            + x_shift
                        ) * 1000
                        if (start_time == end_time == 0) or start_time <= x <= end_time:
                            y = values[plotted_displayed_value]
                            if not isinstance(x, list) and isinstance(y, list):
                                for y_val in y:
                                    plotted_values.append(
                                        {
                                            commons_enums.PlotAttributes.X.value: x,
                                            commons_enums.PlotAttributes.Y.value: y_val,
                                            commons_enums.PlotAttributes.KIND.value: kind,
                                            commons_enums.PlotAttributes.MODE.value: mode,
                                            commons_enums.PlotAttributes.OWN_YAXIS.value: own_yaxis,
                                            "line_shape": line_shape,
                                        }
                                    )
                            else:
                                plotted_values.append(
                                    {
                                        commons_enums.PlotAttributes.X.value: x,
                                        commons_enums.PlotAttributes.Y.value: y,
                                        commons_enums.PlotAttributes.KIND.value: kind,
                                        commons_enums.PlotAttributes.MODE.value: mode,
                                        commons_enums.PlotAttributes.OWN_YAXIS.value: own_yaxis,
                                        "line_shape": line_shape,
                                    }
                                )
                except KeyError:
                    pass
            return plotted_values
        logger.error(f"Unhandled cache type to display: {cache_type}")
    except TypeError:
        logger.error(f"Missing cache type in {cache_file} metadata file")
    except commons_errors.DatabaseNotFoundError as ex:
        logger.warning(f"Missing cache values ({ex})")
    return []


def _get_cache_displayed_value(cache_val, base_displayed_value):
    # unmodified version from displayed_elements
    for key in cache_val.keys():
        separator_split_key = key.split(commons_constants.CACHE_RELATED_DATA_SEPARATOR)
        if (
            base_displayed_value == separator_split_key[0]
            and len(separator_split_key) == 2
        ):
            return key
    return None
