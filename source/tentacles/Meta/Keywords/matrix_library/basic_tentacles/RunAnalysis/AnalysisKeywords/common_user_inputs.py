import octobot_commons.enums as commons_enums
from tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.AnalysisKeywords.analysis_enums import (
    AnalysisModePlotSettingsTypes,
)
import octobot_commons.enums as commons_enums
from tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.AnalysisKeywords.analysis_enums import (
    AnalysisModePlotSettingsTypes,
)
import tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.AnalysisKeywords.common_user_inputs as common_user_inputs
from tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.BaseDataProvider.default_base_data_provider import (
    base_data_provider,
)

CHART_LOCATION_SUFFIX: str = "_chart_location"
ENABLE_PREFIX: str = "enable_"


def init_data_source_settings(
    data_source_input_name: str,
    data_source_input_title: str,
    analysis_mode_plugin,
    inputs: dict,
    parent_input_name: str,
    default_chart_location: str = "sub-chart",
    default_data_source_enabled: bool = False,
    has_chart_location: bool = True,
):
    analysis_mode_plugin.CLASS_UI.user_input(
        data_source_input_name,
        commons_enums.UserInputTypes.OBJECT,
        None,
        inputs,
        editor_options={
            commons_enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6,
            commons_enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
            commons_enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
        },
        title=data_source_input_title,
        parent_input_name=parent_input_name,
    )
    enabled = common_user_inputs.user_enable_data_source(
        analysis_mode_plugin=analysis_mode_plugin,
        inputs=inputs,
        parent_input_name=data_source_input_name,
        data_source_input_title=data_source_input_title,
        def_val=default_data_source_enabled,
    )
    if enabled and has_chart_location:
        common_user_inputs.user_select_chart_location(
            analysis_mode_plugin=analysis_mode_plugin,
            inputs=inputs,
            parent_input_name=data_source_input_name,
            data_source_input_title=data_source_input_title,
            def_val=default_chart_location,
        )


def user_select_chart_location(
    analysis_mode_plugin,
    inputs: dict,
    parent_input_name: str,
    data_source_input_title: str,
    def_val="sub-chart",
) -> str:
    return analysis_mode_plugin.CLASS_UI.user_input(
        parent_input_name + CHART_LOCATION_SUFFIX,
        commons_enums.UserInputTypes.OPTIONS,
        def_val,
        inputs,
        title=f"{data_source_input_title} Chart Location",
        editor_options={
            commons_enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
        },
        options=["main-chart", "sub-chart"],
        parent_input_name=parent_input_name,
    )


def get_evaluator_settings(
    run_data,
    parent_input_name: str,
    analysis_type: str,
):
    return run_data.config.get(analysis_type, {}).get(
        analysis_type + parent_input_name, {}
    )


def get_user_selected_chart_location(
    run_data,
    parent_input_name: str,
    analysis_type: str,
    def_val: str = "sub-chart",
):
    return get_evaluator_settings(run_data, parent_input_name, analysis_type).get(
        analysis_type + parent_input_name + CHART_LOCATION_SUFFIX, def_val
    )


def user_enable_data_source(
    analysis_mode_plugin,
    inputs: dict,
    parent_input_name: str,
    data_source_input_title: str,
    def_val=False,
) -> str:
    return analysis_mode_plugin.CLASS_UI.user_input(
        ENABLE_PREFIX + parent_input_name,
        commons_enums.UserInputTypes.BOOLEAN,
        def_val,
        inputs,
        title=f"Enable {data_source_input_title}",
        editor_options={
            commons_enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
        },
        parent_input_name=parent_input_name,
    )


def get_is_data_source_enabled(
    run_data,
    parent_input_name: str,
    analysis_type: str,
    def_val: str = "sub-chart",
):
    return get_evaluator_settings(run_data, parent_input_name, analysis_type).get(
        ENABLE_PREFIX + analysis_type + parent_input_name, def_val
    )


def get_plotted_element_based_on_settings(
    run_data: base_data_provider.RunAnalysisBaseDataGenerator,
    analysis_type: str,
    data_source_input_name: str,
    default_data_source_enabled: bool = False,
    default_chart_location: str = "sub-chart",
):
    if common_user_inputs.get_is_data_source_enabled(
        run_data,
        parent_input_name=data_source_input_name,
        def_val=default_data_source_enabled,
        analysis_type=analysis_type,
    ):
        return run_data.get_plotted_element(
            chart_location=get_user_selected_chart_location(
                run_data=run_data,
                parent_input_name=data_source_input_name,
                analysis_type=analysis_type,
                def_val=default_chart_location,
            )
        )
    return None
