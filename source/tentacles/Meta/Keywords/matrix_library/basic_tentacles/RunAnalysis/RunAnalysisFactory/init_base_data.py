import octobot_commons.enums as commons_enums
from tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.BaseDataProvider.default_base_data_provider import (
    future_base_data_provider,
    spot_base_data_provider,
)
from tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.RunAnalysisFactory.analysis_errors import (
    LiveMetaDataNotInitializedError,
)


async def get_base_data(
    ctx,
    exchange_id: str,
    is_backtesting: bool,
    run_database,
    run_display,
    main_plotted_element,
    sub_plotted_element,
):
    # load and generate unified base data

    metadata = await _get_metadata(run_database)
    if metadata["trading_type"] == "spot":
        run_data = spot_base_data_provider.SpotRunAnalysisBaseDataGenerator(
            ctx=ctx,
            run_database=run_database,
            run_display=run_display,
            metadata=metadata,
            is_backtesting=is_backtesting,
            main_plotted_element=main_plotted_element,
            sub_plotted_element=sub_plotted_element,
        )
    elif metadata["trading_type"] == "future":
        run_data = future_base_data_provider.FutureRunAnalysisBaseDataGenerator(
            ctx=ctx,
            run_database=run_database,
            run_display=run_display,
            metadata=metadata,
            is_backtesting=is_backtesting,
            main_plotted_element=main_plotted_element,
            sub_plotted_element=sub_plotted_element,
        )
    else:
        raise NotImplementedError(
            f"RunDataAnalysis is not supported for {metadata['trading_type']}"
        )
    await run_data.load_base_data(exchange_id)
    return run_data


async def _get_metadata(run_database):
    try:
        return (
            await run_database.get_run_db().all(commons_enums.DBTables.METADATA.value)
        )[0]
    except IndexError as error:
        raise LiveMetaDataNotInitializedError from error
