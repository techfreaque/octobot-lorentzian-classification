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
    order=None,
    parent_input_name=None,
):
    parent_input_name = parent_input_name or indicator.config_path_short
    return await user_inputs.user_input(
        maker.ctx,
        f"{indicator.config_path_short}_{name.replace(' ', '_')}",
        input_type=input_type,
        title=title or name,
        def_val=def_val,
        min_val=min_val,
        max_val=max_val,
        options=options,
        show_in_summary=show_in_summary,
        show_in_optimizer=show_in_optimizer,
        order=order,
        parent_input_name=parent_input_name,
    )
