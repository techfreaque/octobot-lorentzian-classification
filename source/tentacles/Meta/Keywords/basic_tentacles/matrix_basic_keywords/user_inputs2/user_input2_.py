import octobot_commons.enums as commons_enums
import octobot_trading.modes.script_keywords.basic_keywords.user_inputs as user_inputs


async def user_input2(
    maker,
    indicator,
    name,
    input_type,
    def_val,
    min_val=None,
    max_val=None,
    title=None,
    options=None,
    show_in_summary=True,
    show_in_optimizer=True,
    item_title: str = None,
    order=None,
    parent_input_name=None,
    grid_columns=None,
    description=None,
    other_schema_values: dict = {},
    editor_options: dict = {},
):
    parent_input_name = parent_input_name or indicator.config_path_short
    editor_options = (
        {
            **editor_options,
            commons_enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: grid_columns,
        }
        if grid_columns
        else editor_options
    )
    other_schema_values = (
        {**other_schema_values, "description": description}
        if description
        else other_schema_values
    )
    return await user_inputs.user_input(
        maker.ctx,
        f"{indicator.config_path_short}_{name.replace(' ', '_')}",
        input_type=input_type,
        title=title or name,
        def_val=def_val,
        min_val=min_val,
        max_val=max_val,
        options=options,
        item_title=item_title,
        show_in_summary=show_in_summary,
        show_in_optimizer=show_in_optimizer,
        editor_options=editor_options,
        other_schema_values=other_schema_values,
        order=order,
        parent_input_name=parent_input_name,
    )
