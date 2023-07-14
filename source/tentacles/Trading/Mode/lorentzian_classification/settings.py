import typing
import octobot_commons.enums as enums
import octobot_trading.util.config_util as config_util
from tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.matrix_enums import (
    UserInputEditorOptionsTypes,
    UserInputOtherSchemaValuesTypes,
)
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.ml_utils.classification_functions.classification_utils as classification_utils
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.ml_utils.classification_functions.downsampling as downsampling
import tentacles.Meta.Keywords.basic_tentacles.basic_modes.mode_base.abstract_mode_base as abstract_mode_base
import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.ml_utils.utils as utils

try:
    import tentacles.Meta.Keywords.basic_tentacles.matrix_basic_keywords.orders.managed_order_pro.activate_managed_order as activate_managed_order
except (ImportError, ModuleNotFoundError):
    activate_managed_order = None

GENERAL_SETTINGS_NAME = "general_settings"
TRAINING_DATA_SETTINGS_NAME = "training_data_settings"
DATA_SOURCE_SETTINGS_NAME = "data_source_settings"
FEATURE_ENGINEERING_SETTINGS_NAME = "feature_engineering_settings"
FILTER_SETTINGS_NAME = "filter_settings"
ORDER_SETTINGS_NAME = "order_settings"
KERNEL_SETTINGS_NAME = "kernel_settings"
DISPLAY_SETTINGS_NAME = "display_settings"


class LorentzianClassificationModeInputs(abstract_mode_base.AbstractBaseMode):
    classification_settings: utils.ClassificationSettings = None
    data_source_settings: utils.DataSourceSettings = None
    filter_settings: utils.FilterSettings = None
    feature_engineering_settings: utils.FeatureEngineeringSettings = None
    kernel_settings: utils.KernelSettings = None
    display_settings: utils.DisplaySettings = None
    order_settings: utils.LorentzianOrderSettings = None
    show_trade_stats: bool = None
    use_worst_case_estimates: bool = None

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the trading mode,
        should define all the trading mode's user inputs
        """
        self._init_general_settings(inputs)
        self._init_feature_engineering_settings(inputs)
        self._init_filter_settings(inputs)
        self._init_kernel_settings(inputs)
        self._init_order_settings(inputs)
        self._init_data_source_settings(inputs)
        self._init_display_settings(inputs)

    def _init_general_settings(self, inputs: dict) -> None:
        self.UI.user_input(
            GENERAL_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Classification Settings",
            editor_options={
                enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
                # enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                # enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                UserInputEditorOptionsTypes.ANT_ICON.value: "RobotOutlined",
            },
            other_schema_values={
                UserInputOtherSchemaValuesTypes.DISPLAY_AS_TAB.value: True,
                UserInputOtherSchemaValuesTypes.TAB_ORDER.value: 2,
            },
        )

        neighbors_count = self.UI.user_input(
            "neighbors_count",
            enums.UserInputTypes.INT,
            8,
            inputs,
            min_val=1,
            max_val=100,
            title="Neighbors Count",
            parent_input_name=GENERAL_SETTINGS_NAME,
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6},
            other_schema_values={
                "description": "Number of similar neighbors to consider "
                "for the prediction."
            },
            order=1,
        )
        config_candles = classification_utils.get_config_candles(self.config)
        default_max_bars_back = 2000 if config_candles >= 2000 else config_candles
        max_bars_back = self.UI.user_input(
            "max_bars_back",
            enums.UserInputTypes.INT,
            default_max_bars_back,
            inputs,
            min_val=1,
            max_val=config_candles,
            title="Max Bars Back",
            parent_input_name=GENERAL_SETTINGS_NAME,
            other_schema_values={
                "description": "Amount of historical candles to use as training data. "
                "To increase the max allowed bars back, change 'Amount of historical "
                "candles' in the TimeFrameStrategyEvaluator settings."
            },
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6},
            order=2,
        )
        prediction_threshold: int = self.UI.user_input(
            "prediction_threshold",
            enums.UserInputTypes.INT,
            50,
            inputs,
            min_val=0,
            max_val=100,
            title="Percent of required neighbor signals",
            parent_input_name=GENERAL_SETTINGS_NAME,
            other_schema_values={
                "description": "If you set this value to 80, a signal will require more than "
                "80% of the neighbors to be winners in the past. For example if you "
                "set the neighbors count to 10, a signal will require at least 9 "
                "neighbors to be winners in the past to trigger a trade. "
                "In the trading view version this value is 0 and cant be changed."
            },
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6},
            order=2,
        )
        self.UI.user_input(
            TRAINING_DATA_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Training Data Settings",
            editor_options={
                enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
            },
            parent_input_name=GENERAL_SETTINGS_NAME,
        )
        training_data_type_str: int = self.UI.user_input(
            "training_data_type",
            enums.UserInputTypes.OPTIONS,
            utils.YTrainTypeDescriptions.IS_IN_PROFIT_AFTER_4_BARS_CLOSES,
            inputs,
            options=[
                utils.YTrainTypeDescriptions.IS_WINNING_TRADE,
                utils.YTrainTypeDescriptions.IS_IN_PROFIT_AFTER_4_BARS,
                utils.YTrainTypeDescriptions.IS_IN_PROFIT_AFTER_4_BARS_CLOSES,
            ],
            title="Training data type",
            parent_input_name=TRAINING_DATA_SETTINGS_NAME,
            other_schema_values={"description": ""},
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12},
            order=1,
        )
        training_data_type: utils.YTrainTypes = utils.Y_TRAIN_DESCRIPTIONS_TO_TYPES[
            training_data_type_str
        ]
        percent_for_a_win: typing.Optional[float] = None
        percent_for_a_loss: typing.Optional[float] = None
        is_in_profit_after_x_bars: typing.Optional[int] = None
        if training_data_type == utils.YTrainTypes.IS_WINNING_TRADE:
            percent_for_a_win = self.UI.user_input(
                "percent_for_a_win",
                enums.UserInputTypes.FLOAT,
                2,
                inputs,
                min_val=0,
                max_val=100,
                title="Percent to count as a winning trade",
                parent_input_name=TRAINING_DATA_SETTINGS_NAME,
                other_schema_values={
                    "description": "A trade for the training data will be considered as a win if it hits the win percentge before the loss percentage"
                },
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
                },
                order=2,
            )
            percent_for_a_loss = self.UI.user_input(
                "percent_for_a_loss",
                enums.UserInputTypes.FLOAT,
                0.5,
                inputs,
                min_val=0,
                max_val=100,
                title="Percent to count as a losing trade",
                parent_input_name=TRAINING_DATA_SETTINGS_NAME,
                other_schema_values={
                    "description": "A trade for the training data will be considered as a win if it hits the win percentge before the loss percentage"
                },
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
                },
                order=3,
            )
        elif training_data_type in (
            utils.YTrainTypes.IS_IN_PROFIT_AFTER_4_BARS_CLOSES,
            utils.YTrainTypes.IS_IN_PROFIT_AFTER_4_BARS,
        ):
            is_in_profit_after_x_bars = self.UI.user_input(
                "is_in_profit_after_x_bars",
                enums.UserInputTypes.INT,
                4,
                inputs,
                min_val=0,
                max_val=100,
                title="Check if trade is in profit after X bars",
                parent_input_name=TRAINING_DATA_SETTINGS_NAME,
                other_schema_values={
                    "description": (
                        "For each candle in the training data, it will check if the trade would be in profit after X bars. "
                        "This value is 4 in the TradingView version and cant be changed."
                    )
                },
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
                },
                order=2,
            )
        required_neighbors: float = neighbors_count / 100 * prediction_threshold
        down_sampling_mode = self.UI.user_input(
            "down_sampler",
            enums.UserInputTypes.OPTIONS,
            downsampling.DownSamplers.DEFAULT_DOWN_SAMPLER,
            inputs,
            options=downsampling.DownSamplers.AVAILABLE_DOWN_SAMPLERS,
            title="Down Sampling Mode",
            parent_input_name=GENERAL_SETTINGS_NAME,
            other_schema_values={
                "description": "When enabled, the strategy will skip candles of the "
                "training data, within the max bars back. This will speed up "
                "classification and allows you to use a higher max bars back instead, "
                "which will result in a more diverse training data."
            },
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6},
            order=3,
        )
        only_train_on_every_x_bars = None
        this_down_sampler: typing.Callable[
            [int, int], bool
        ] = downsampling.DownSamplers.DOWN_SAMPLERS_BY_TITLES.get(
            down_sampling_mode, downsampling.DownSamplers.NO_DOWN_SAMPLER
        )
        if down_sampling_mode in (
            downsampling.DownSamplers.SKIP_EVERY_X_DOWN_SAMPLER,
            downsampling.DownSamplers.USE_EVERY_X_DOWN_SAMPLER,
        ):
            title: str = None
            description: str = None
            if (
                down_sampling_mode
                == downsampling.DownSamplers.SKIP_EVERY_X_DOWN_SAMPLER
            ):
                title = "Skip every X bars of training data"
                description = (
                    "Instead of using every bar as training data, "
                    "you can instead skip candles and only train on the non skipped "
                    "bars. This will speed up classification and allows you to "
                    "increase the max bars back instead."
                )
            elif (
                down_sampling_mode == downsampling.DownSamplers.USE_EVERY_X_DOWN_SAMPLER
            ):
                title = "Only train on every X bars"
                description = (
                    "Instead of using every bar as training data, "
                    "you can instead skip candles and only train on every X bars. "
                    "This will speed up classification and allows you to increase the "
                    "max bars back instead."
                )

            only_train_on_every_x_bars = self.UI.user_input(
                "only_train_on_x_bars",
                enums.UserInputTypes.INT,
                4,
                inputs,
                min_val=2,
                title=title,
                parent_input_name=GENERAL_SETTINGS_NAME,
                other_schema_values={"description": description},
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
                },
                order=4,
            )
        use_remote_fractals = self.UI.user_input(
            "use_remote_fractals",
            enums.UserInputTypes.BOOLEAN,
            False,
            inputs,
            title="Use Remote Fractals",
            parent_input_name=GENERAL_SETTINGS_NAME,
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6},
            other_schema_values={
                "description": "When the option is enabled, the model will utilize "
                "training data from the first bar up to a maximum of X bars in the "
                "past. On the other hand, if the option is disabled, the model will use"
                " training data from the current bar up to a maximum of X bars in the "
                "past. When enabled during backtesting, the starting index for each "
                'candle iteration will be determined by the "Amount of historical '
                'live candles" setting. '
                "Although this approach may yield outcomes that differ from those "
                "observed on TradingView, it can provide valuable insights. "
            },
            order=5,
        )
        color_compression = 1
        # color_compression=self.UI.user_input(
        #     "color_compression",
        #     enums.UserInputTypes.INT,
        #     1,
        #     inputs,
        #     min_val=1,
        #     max_val=10,
        #     title="Color Compression",
        #     parent_input_name=GENERAL_SETTINGS_NAME,
        #     other_schema_values={
        #         "description": "Compression factor for adjusting the "
        #         "intensity of the color scale."
        #     },
        # )

        self.classification_settings = utils.ClassificationSettings(
            neighbors_count=neighbors_count,
            use_remote_fractals=use_remote_fractals,
            only_train_on_every_x_bars=only_train_on_every_x_bars,
            live_history_size=config_candles,
            max_bars_back=max_bars_back,
            color_compression=color_compression,
            down_sampler=this_down_sampler,
            required_neighbors=required_neighbors,
            training_data_settings=utils.YTrainSettings(
                training_data_type=training_data_type,
                percent_for_a_win=percent_for_a_win,
                percent_for_a_loss=percent_for_a_loss,
                is_in_profit_after_x_bars=is_in_profit_after_x_bars,
            ),
        )
        # Trade Stats Settings
        # Note: The trade stats section is NOT intended to be used as a replacement for
        # proper backtesting. It is intended to be used for calibration purposes only.
        # self.show_trade_stats = self.UI.user_input(
        #     "show_trade_stats",
        #     enums.UserInputTypes.BOOLEAN,
        #     True,
        #     inputs,
        #     title="Show Trade Stats",
        #     parent_input_name=GENERAL_SETTINGS_NAME,
        #     other_schema_values={
        #         "description": "Displays the trade stats for a given configuration. "
        #         "Useful for optimizing the settings in the Feature Engineering section."
        #         " This should NOT replace backtesting and should be used for "
        #         "calibration purposes only. Early Signal Flips represent instances "
        #         "where the model changes signals before 4 bars elapses; high values can"
        #         " indicate choppy (ranging) market conditions."
        #     },
        # )
        # self.use_worst_case_estimates = self.UI.user_input(
        #     "use_worst_case_estimates",
        #     enums.UserInputTypes.BOOLEAN,
        #     False,
        #     inputs,
        #     title="Use Worst Case Estimates",
        #     parent_input_name=GENERAL_SETTINGS_NAME,
        #     other_schema_values={
        #         "description": "Whether to use the worst case scenario for backtesting."
        #         " This option can be useful for creating a conservative estimate that "
        #         "is based on close prices only, thus avoiding the effects of intrabar "
        #         "repainting. This option assumes that the user does not enter when the "
        #         "signal first appears and instead waits for the bar to close as "
        #         "confirmation. On larger timeframes, this can mean entering after a "
        #         "large move has already occurred. Leaving this option disabled is "
        #         "generally better for those that use this indicator as a source of "
        #         "confluence and prefer estimates that demonstrate discretionary "
        #         "mid-bar entries. Leaving this option enabled may be more consistent "
        #         "with traditional backtesting results."
        #     },
        # )

    def _init_feature_engineering_settings(self, inputs: dict) -> None:
        # Feature Variables: User-Defined Inputs for calculating Feature Series.
        self.UI.user_input(
            FEATURE_ENGINEERING_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Feature Engineering Settings",
            editor_options={
                enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
                # enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                # enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                UserInputEditorOptionsTypes.ANT_ICON.value: "FunctionOutlined",
            },
            other_schema_values={
                UserInputOtherSchemaValuesTypes.DISPLAY_AS_TAB.value: True,
                UserInputOtherSchemaValuesTypes.TAB_ORDER.value: 4,
            },
        )
        feature_count = self.UI.user_input(
            "feature_count",
            enums.UserInputTypes.INT,
            5,
            inputs,
            min_val=2,
            max_val=5,
            title="Feature Count",
            parent_input_name=FEATURE_ENGINEERING_SETTINGS_NAME,
            other_schema_values={
                "description": "Number of features to use for ML predictions."
            },
        )
        plot_features = self.UI.user_input(
            "plot_features",
            enums.UserInputTypes.BOOLEAN,
            title="Plot Features",
            def_val=False,
            registered_inputs=inputs,
            parent_input_name=FEATURE_ENGINEERING_SETTINGS_NAME,
        )
        self.feature_engineering_settings = utils.FeatureEngineeringSettings(
            feature_count=feature_count,
            plot_features=plot_features,
        )

        feature_1_settings_name = "feature_1_settings"
        self.UI.user_input(
            feature_1_settings_name,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Feature 1",
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12},
            parent_input_name=FEATURE_ENGINEERING_SETTINGS_NAME,
        )
        f1_string = self.UI.user_input(
            "f1_string",
            enums.UserInputTypes.OPTIONS,
            title="Feature 1",
            def_val="RSI",
            registered_inputs=inputs,
            options=["RSI", "WT", "CCI", "ADX"],
            other_schema_values={
                "description": "The first feature to use for ML predictions."
            },
            parent_input_name=feature_1_settings_name,
        )
        f1_paramA = self.UI.user_input(
            "f1_paramA",
            enums.UserInputTypes.INT,
            title="Parameter A",
            def_val=14,
            registered_inputs=inputs,
            other_schema_values={"description": "The primary parameter of feature 1."},
            parent_input_name=feature_1_settings_name,
        )
        f1_paramB = self.UI.user_input(
            "f1_paramB",
            enums.UserInputTypes.INT,
            title="Parameter B",
            def_val=1,
            registered_inputs=inputs,
            other_schema_values={
                "description": "The secondary parameter of feature 2 (if applicable)."
            },
            parent_input_name=feature_1_settings_name,
        )
        self.feature_engineering_settings.add_feature(
            indicator_name=f1_string, param_a=f1_paramA, param_b=f1_paramB
        )

        feature_2_settings_name = "feature_2_settings"
        self.UI.user_input(
            feature_2_settings_name,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Feature 2",
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12},
            parent_input_name=FEATURE_ENGINEERING_SETTINGS_NAME,
        )
        f2_string = self.UI.user_input(
            "f2_string",
            enums.UserInputTypes.OPTIONS,
            title="Feature 2",
            def_val="WT",
            registered_inputs=inputs,
            options=["RSI", "WT", "CCI", "ADX"],
            other_schema_values={
                "description": "The second feature to use for ML predictions."
            },
            parent_input_name=feature_2_settings_name,
        )
        f2_paramA = self.UI.user_input(
            "f2_paramA",
            enums.UserInputTypes.INT,
            title="Parameter A",
            def_val=10,
            registered_inputs=inputs,
            other_schema_values={"description": "The primary parameter of feature 2."},
            parent_input_name=feature_2_settings_name,
        )
        f2_paramB = self.UI.user_input(
            "f2_paramB",
            enums.UserInputTypes.INT,
            title="Parameter B",
            def_val=11,
            registered_inputs=inputs,
            other_schema_values={
                "description": "The secondary parameter of feature 2 (if applicable)."
            },
            parent_input_name=feature_2_settings_name,
        )
        self.feature_engineering_settings.add_feature(
            indicator_name=f2_string, param_a=f2_paramA, param_b=f2_paramB
        )
        f3_string = None
        f3_paramA = None
        f3_paramB = None
        f4_string = None
        f4_paramA = None
        f4_paramB = None
        f5_string = None
        f5_paramA = None
        f5_paramB = None
        if feature_count > 2:
            feature_3_settings_name = "feature_3_settings"
            self.UI.user_input(
                feature_3_settings_name,
                enums.UserInputTypes.OBJECT,
                None,
                inputs,
                title="Feature 3",
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12
                },
                parent_input_name=FEATURE_ENGINEERING_SETTINGS_NAME,
            )
            f3_string = self.UI.user_input(
                "f3_string",
                enums.UserInputTypes.OPTIONS,
                title="Feature 3",
                def_val="CCI",
                registered_inputs=inputs,
                options=["RSI", "WT", "CCI", "ADX"],
                other_schema_values={
                    "description": "The third feature to use for ML predictions."
                },
                parent_input_name=feature_3_settings_name,
            )
            f3_paramA = self.UI.user_input(
                "f3_paramA",
                enums.UserInputTypes.INT,
                title="Parameter A",
                def_val=20,
                registered_inputs=inputs,
                other_schema_values={
                    "description": "The primary parameter of feature 3."
                },
                parent_input_name=feature_3_settings_name,
            )
            f3_paramB = self.UI.user_input(
                "f3_paramB",
                enums.UserInputTypes.INT,
                title="Parameter B",
                def_val=1,
                registered_inputs=inputs,
                other_schema_values={
                    "description": "The secondary parameter of feature "
                    "3 (if applicable)."
                },
                parent_input_name=feature_3_settings_name,
            )
            self.feature_engineering_settings.add_feature(
                indicator_name=f3_string, param_a=f3_paramA, param_b=f3_paramB
            )
            if feature_count > 3:
                feature_4_settings_name = "feature_4_settings"
                self.UI.user_input(
                    feature_4_settings_name,
                    enums.UserInputTypes.OBJECT,
                    None,
                    inputs,
                    title="Feature 4",
                    editor_options={
                        enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12
                    },
                    parent_input_name=FEATURE_ENGINEERING_SETTINGS_NAME,
                )

                f4_string = self.UI.user_input(
                    "f4_string",
                    enums.UserInputTypes.OPTIONS,
                    title="Feature 4",
                    def_val="ADX",
                    registered_inputs=inputs,
                    options=["RSI", "WT", "CCI", "ADX"],
                    other_schema_values={
                        "description": "The fourth feature to use for ML predictions."
                    },
                    parent_input_name=feature_4_settings_name,
                )
                f4_paramA = self.UI.user_input(
                    "f4_paramA",
                    enums.UserInputTypes.INT,
                    title="Parameter A",
                    def_val=20,
                    registered_inputs=inputs,
                    other_schema_values={
                        "description": "The primary parameter of feature 4."
                    },
                    parent_input_name=feature_4_settings_name,
                )
                f4_paramB = self.UI.user_input(
                    "f4_paramB",
                    enums.UserInputTypes.INT,
                    title="Parameter B",
                    def_val=2,
                    registered_inputs=inputs,
                    other_schema_values={
                        "description": "The secondary parameter of feature "
                        "4 (if applicable)."
                    },
                    parent_input_name=feature_4_settings_name,
                )
                self.feature_engineering_settings.add_feature(
                    indicator_name=f4_string, param_a=f4_paramA, param_b=f4_paramB
                )
                if feature_count > 4:
                    feature_5_settings_name = "feature_5_settings"
                    self.UI.user_input(
                        feature_5_settings_name,
                        enums.UserInputTypes.OBJECT,
                        None,
                        inputs,
                        title="Feature 5",
                        editor_options={
                            enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12
                        },
                        parent_input_name=FEATURE_ENGINEERING_SETTINGS_NAME,
                    )

                    f5_string = self.UI.user_input(
                        "f5_string",
                        enums.UserInputTypes.OPTIONS,
                        title="Feature 5",
                        def_val="RSI",
                        registered_inputs=inputs,
                        options=["RSI", "WT", "CCI", "ADX"],
                        other_schema_values={
                            "description": "The fifth feature to use for "
                            "ML predictions."
                        },
                        parent_input_name=feature_5_settings_name,
                    )
                    f5_paramA = self.UI.user_input(
                        "f5_paramA",
                        enums.UserInputTypes.INT,
                        title="Parameter A",
                        def_val=9,
                        registered_inputs=inputs,
                        other_schema_values={
                            "description": "The primary parameter of feature 5."
                        },
                        parent_input_name=feature_5_settings_name,
                    )
                    f5_paramB = self.UI.user_input(
                        "f5_paramB",
                        enums.UserInputTypes.INT,
                        title="Parameter B",
                        def_val=1,
                        registered_inputs=inputs,
                        other_schema_values={
                            "description": "The secondary parameter of feature "
                            "5 (if applicable)."
                        },
                        parent_input_name=feature_5_settings_name,
                    )
                    self.feature_engineering_settings.add_feature(
                        indicator_name=f5_string, param_a=f5_paramA, param_b=f5_paramB
                    )

    def _init_kernel_settings(self, inputs: dict) -> None:
        self.UI.user_input(
            KERNEL_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Kernel Settings",
            editor_options={
                enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
                # enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                # enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                UserInputEditorOptionsTypes.ANT_ICON.value: "BulbOutlined",
            },
            other_schema_values={
                UserInputOtherSchemaValuesTypes.DISPLAY_AS_TAB.value: True,
                UserInputOtherSchemaValuesTypes.TAB_ORDER.value: 6,
            },
        )
        self.kernel_settings: utils.KernelSettings = utils.KernelSettings(
            use_kernel_filter=self.UI.user_input(
                "use_kernel_filter",
                enums.UserInputTypes.BOOLEAN,
                True,
                inputs,
                title="Trade with Kernel",
                parent_input_name=KERNEL_SETTINGS_NAME,
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6,
                },
            ),
            show_kernel_estimate=self.UI.user_input(
                "show_kernel_estimate",
                enums.UserInputTypes.BOOLEAN,
                True,
                inputs,
                title="Show Kernel Estimate",
                parent_input_name=KERNEL_SETTINGS_NAME,
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6,
                },
            ),
            use_kernel_smoothing=self.UI.user_input(
                "use_kernel_smoothing",
                enums.UserInputTypes.BOOLEAN,
                False,
                inputs,
                title="Enhance Kernel Smoothing",
                parent_input_name=KERNEL_SETTINGS_NAME,
                other_schema_values={
                    "description": "Uses a crossover based mechanism "
                    "to smoothen kernel color changes. This often "
                    "results in less color transitions overall and "
                    "may result in more ML entry signals being generated."
                },
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6,
                },
            ),
            lookback_window=self.UI.user_input(
                "lookback_window",
                enums.UserInputTypes.INT,
                8,
                inputs,
                min_val=0,
                max_val=100,
                title="Lookback Window",
                parent_input_name=KERNEL_SETTINGS_NAME,
                other_schema_values={
                    "description": "The number of bars used for the estimation. This is"
                    " a sliding value that represents the most recent historical bars. "
                    "Recommended range: 3-50"
                },
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6,
                },
            ),
            relative_weighting=self.UI.user_input(
                "relative_weighting",
                enums.UserInputTypes.FLOAT,
                8,
                inputs,
                min_val=0,
                max_val=100,
                title="Relative Weighting",
                parent_input_name=KERNEL_SETTINGS_NAME,
                other_schema_values={
                    "description": "Relative weighting of time frames. As this value "
                    "approaches zero, the longer time frames will exert more influence "
                    "on the estimation. As this value approaches infinity, the behavior"
                    " of the Rational Quadratic Kernel will become identical to the "
                    "Gaussian kernel. Recommended range: 0.25-25"
                },
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6,
                },
            ),
            regression_level=self.UI.user_input(
                "regression_level",
                enums.UserInputTypes.INT,
                25,
                inputs,
                min_val=0,
                max_val=100,
                title="Regression Level",
                parent_input_name=KERNEL_SETTINGS_NAME,
                other_schema_values={
                    "description": "Bar index on which to start regression. Controls "
                    "how tightly fit the kernel estimate is to the data. Smaller values"
                    " are a tighter fit. Larger values are a looser fit. Recommended "
                    "range: 2-25"
                },
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6,
                },
            ),
            lag=self.UI.user_input(
                "lag",
                enums.UserInputTypes.INT,
                2,
                inputs,
                min_val=0,
                max_val=100,
                title="Lag",
                parent_input_name=KERNEL_SETTINGS_NAME,
                other_schema_values={
                    "description": "Lag for crossover detection. Lower values result in"
                    " earlier crossovers. Recommended range: 1-2"
                },
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6,
                },
            ),
        )

    def _init_filter_settings(self, inputs: dict) -> None:
        self.UI.user_input(
            FILTER_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Filter Settings",
            editor_options={
                enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
                # enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                # enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                UserInputEditorOptionsTypes.ANT_ICON.value: "FilterOutlined",
            },
            other_schema_values={
                UserInputOtherSchemaValuesTypes.DISPLAY_AS_TAB.value: True,
                UserInputOtherSchemaValuesTypes.TAB_ORDER.value: 8,
            },
        )
        volatility_filter_name = "volatility_filter_settings"
        self.UI.user_input(
            volatility_filter_name,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Volatility Filter Settings",
            parent_input_name=FILTER_SETTINGS_NAME,
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12},
        )
        use_volatility_filter = self.UI.user_input(
            "use_volatility_filter",
            enums.UserInputTypes.BOOLEAN,
            True,
            inputs,
            title="Use Volatility Filter",
            parent_input_name=volatility_filter_name,
            other_schema_values={
                "description": "Whether to use the volatility filter.",
            },
        )
        plot_volatility_filter = False
        if use_volatility_filter:
            plot_volatility_filter = self.UI.user_input(
                "plot_volatility_filter",
                enums.UserInputTypes.BOOLEAN,
                False,
                inputs,
                title="Plot Volatility Filter",
                parent_input_name=volatility_filter_name,
            )

        regime_filter_name = "regime_filter_settings"
        self.UI.user_input(
            regime_filter_name,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Regime Filter Settings",
            parent_input_name=FILTER_SETTINGS_NAME,
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6},
        )
        use_regime_filter = self.UI.user_input(
            "use_regime_filter",
            enums.UserInputTypes.BOOLEAN,
            True,
            inputs,
            title="Use Regime Filter",
            parent_input_name=regime_filter_name,
        )
        plot_regime_filter = False
        regime_threshold = None
        if use_regime_filter:
            plot_regime_filter = self.UI.user_input(
                "plot_regime_filter",
                enums.UserInputTypes.BOOLEAN,
                False,
                inputs,
                title="Plot Regime Filter",
                parent_input_name=regime_filter_name,
            )
            regime_threshold = self.UI.user_input(
                "regime_threshold",
                enums.UserInputTypes.FLOAT,
                -0.1,
                inputs,
                min_val=-10,
                max_val=10,
                title="Regime Threshold",
                parent_input_name=regime_filter_name,
                other_schema_values={
                    "description": "Whether to use the trend detection filter. "
                    "Threshold for detecting Trending/Ranging markets. Use steps of 0.1"
                },
            )

        adx_filter_name = "adx_filter_settings"
        self.UI.user_input(
            adx_filter_name,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="ADX Filter Settings",
            parent_input_name=FILTER_SETTINGS_NAME,
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6},
        )
        use_adx_filter = self.UI.user_input(
            "use_adx_filter",
            enums.UserInputTypes.BOOLEAN,
            False,
            inputs,
            title="Use ADX Filter",
            parent_input_name=adx_filter_name,
        )
        plot_adx_filter = False
        adx_threshold = None
        if use_adx_filter:
            plot_adx_filter = self.UI.user_input(
                "plot_adx_filter",
                enums.UserInputTypes.BOOLEAN,
                False,
                inputs,
                title="Plot EMA Filter",
                parent_input_name=adx_filter_name,
            )
            adx_threshold = self.UI.user_input(
                "adx_threshold",
                enums.UserInputTypes.INT,
                20,
                inputs,
                min_val=0,
                max_val=100,
                title="ADX Threshold",
                parent_input_name=adx_filter_name,
                other_schema_values={
                    "description": "Whether to use the ADX filter. "
                    "Threshold for detecting Trending/Ranging markets."
                },
            )
        ema_filter_name = "ema_filter_settings"
        self.UI.user_input(
            ema_filter_name,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="EMA Filter Settings",
            parent_input_name=FILTER_SETTINGS_NAME,
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6},
        )
        use_ema_filter = self.UI.user_input(
            "use_ema_filter",
            enums.UserInputTypes.BOOLEAN,
            False,
            inputs,
            title="Use EMA Filter",
            parent_input_name=ema_filter_name,
        )
        plot_ema_filter = False
        ema_period = None
        if use_ema_filter:
            plot_ema_filter = self.UI.user_input(
                "plot_ema_filter",
                enums.UserInputTypes.BOOLEAN,
                False,
                inputs,
                title="Plot EMA Filter",
                parent_input_name=ema_filter_name,
            )

            ema_period = self.UI.user_input(
                "ema_period",
                enums.UserInputTypes.INT,
                200,
                inputs,
                min_val=1,
                title="EMA Period",
                parent_input_name=ema_filter_name,
                other_schema_values={
                    "description": "The period of the EMA used for the EMA Filter."
                },
            )
        sma_filter_name = "sma_filter_settings"
        self.UI.user_input(
            sma_filter_name,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="SMA Filter Settings",
            parent_input_name=FILTER_SETTINGS_NAME,
            other_schema_values={
                enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
            },
        )
        use_sma_filter = self.UI.user_input(
            "use_sma_filter",
            enums.UserInputTypes.BOOLEAN,
            False,
            inputs,
            title="Use SMA Filter",
            parent_input_name=sma_filter_name,
        )
        plot_sma_filter = False
        sma_period = None
        if use_sma_filter:
            plot_sma_filter = self.UI.user_input(
                "plot_sma_filter",
                enums.UserInputTypes.BOOLEAN,
                False,
                inputs,
                title="Plot SMA Filter",
                parent_input_name=sma_filter_name,
            )
            sma_period = self.UI.user_input(
                "sma_period",
                enums.UserInputTypes.INT,
                200,
                inputs,
                min_val=1,
                title="SMA Period",
                parent_input_name=sma_filter_name,
                other_schema_values={
                    "description": "The period of the SMA used for the SMA Filter."
                },
            )

        self.filter_settings: utils.FilterSettings = utils.FilterSettings(
            use_volatility_filter=use_volatility_filter,
            plot_volatility_filter=plot_volatility_filter,
            use_regime_filter=use_regime_filter,
            regime_threshold=regime_threshold,
            plot_regime_filter=plot_regime_filter,
            use_adx_filter=use_adx_filter,
            adx_threshold=adx_threshold,
            plot_adx_filter=plot_adx_filter,
            use_ema_filter=use_ema_filter,
            ema_period=ema_period,
            plot_ema_filter=plot_ema_filter,
            use_sma_filter=use_sma_filter,
            sma_period=sma_period,
            plot_sma_filter=plot_sma_filter,
        )

    def _init_data_source_settings(self, inputs: dict) -> None:
        self.UI.user_input(
            DATA_SOURCE_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Data Source Settings",
            editor_options={
                enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
                # enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                # enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                UserInputEditorOptionsTypes.ANT_ICON.value: "DollarOutlined",
            },
            other_schema_values={
                UserInputOtherSchemaValuesTypes.DISPLAY_AS_TAB.value: True,
                UserInputOtherSchemaValuesTypes.TAB_ORDER.value: 10,
            },
        )
        source = self.UI.user_input(
            "candle_source",
            enums.UserInputTypes.OPTIONS,
            enums.PriceStrings.STR_PRICE_CLOSE.value,
            inputs,
            options=[
                enums.PriceStrings.STR_PRICE_CLOSE.value,
                enums.PriceStrings.STR_PRICE_OPEN.value,
                enums.PriceStrings.STR_PRICE_HIGH.value,
                enums.PriceStrings.STR_PRICE_LOW.value,
                "hlc3",
                "ohlc4",
            ],
            title="Candle source",
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12},
            parent_input_name=DATA_SOURCE_SETTINGS_NAME,
            other_schema_values={"description": "Source of the input data"},
        )
        available_symbols = config_util.get_symbols(self.config, enabled_only=True)
        symbol_settings_by_symbols: typing.Dict[utils.SymbolSettings] = {}
        for symbol in available_symbols:
            this_symbol_data_source_settings = f"data_source_settings_{symbol}"
            self.UI.user_input(
                this_symbol_data_source_settings,
                enums.UserInputTypes.OBJECT,
                None,
                inputs,
                title=f"{symbol} Data Source Settings",
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 4,
                    enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                    enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                },
                parent_input_name=DATA_SOURCE_SETTINGS_NAME,
            )
            trade_on_this_pair: bool = self.UI.user_input(
                f"trade_on_{symbol}",
                enums.UserInputTypes.BOOLEAN,
                True,
                inputs,
                title=f"Trade on {symbol}",
                parent_input_name=this_symbol_data_source_settings,
                other_schema_values={
                    "description": f"Enable this option to trade on {symbol}"
                },
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12
                },
            )
            this_target_symbol: typing.Optional[str] = None
            inverse_signals: bool = False
            use_custom_pair: bool = False
            enable_long_orders: bool = False
            enable_short_orders: bool = False
            if trade_on_this_pair and len(available_symbols):
                if self.order_settings.enable_long_orders:
                    enable_long_orders: bool = self.UI.user_input(
                        f"enable_long_orders_{symbol}",
                        enums.UserInputTypes.BOOLEAN,
                        True,
                        inputs,
                        title=f"Enable long tading on {symbol}",
                        parent_input_name=this_symbol_data_source_settings,
                        editor_options={
                            enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
                        },
                    )
                else:
                    enable_long_orders: bool = False
                if self.order_settings.enable_short_orders:
                    enable_short_orders = self.UI.user_input(
                        f"enable_short_orders_{symbol}",
                        enums.UserInputTypes.BOOLEAN,
                        True,
                        inputs,
                        title=f"Enable short tading on {symbol}",
                        parent_input_name=this_symbol_data_source_settings,
                        editor_options={
                            enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
                        },
                        other_schema_values={
                            enums.UserInputOtherSchemaValuesTypes.DESCRIPTION.value: "Note that "
                            "short trading is only working on futures or inversed short tokens"
                        },
                    )
                else:
                    enable_short_orders: bool = False
                inverse_signals = self.UI.user_input(
                    f"inverse_signals_{symbol}",
                    enums.UserInputTypes.BOOLEAN,
                    False,
                    inputs,
                    title=f"Inverse the signals of the strategy for {symbol}",
                    parent_input_name=this_symbol_data_source_settings,
                    other_schema_values={
                        "description": "Sells on long signals and buys on short "
                        "signals. This option can be used to trade short tokens. "
                        "As short tokens will grow in value if the underlying asset "
                        "price decreases."
                    },
                    editor_options={
                        enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
                    },
                )
                use_custom_pair = self.UI.user_input(
                    f"enable_custom_source_{symbol}",
                    enums.UserInputTypes.BOOLEAN,
                    False,
                    inputs,
                    title=f"Use other symbols data to evaluate on {symbol}",
                    parent_input_name=this_symbol_data_source_settings,
                    other_schema_values={
                        "description": f"Enable this option to be able to use another "
                        f"symbols data to trade on {symbol}."
                    },
                    editor_options={
                        enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
                    },
                )
                if use_custom_pair:
                    this_target_symbol = self.UI.user_input(
                        f"{symbol}_target_symbol",
                        enums.UserInputTypes.OPTIONS,
                        self.symbol,
                        inputs,
                        options=available_symbols,
                        title=f"Data source to use for {symbol}",
                        parent_input_name=this_symbol_data_source_settings,
                        other_schema_values={
                            "description": f"Instead of using {symbol} as a data source"
                            " for the strategy, you can use the data from any other "
                            f"available pair to trade on {symbol}."
                        },
                        editor_options={
                            enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12
                        },
                    )
            symbol_settings_by_symbols[symbol] = utils.SymbolSettings(
                symbol=symbol,
                this_target_symbol=this_target_symbol,
                trade_on_this_pair=trade_on_this_pair,
                use_custom_pair=use_custom_pair,
                inverse_signals=inverse_signals,
                enable_long_orders=enable_long_orders,
                enable_short_orders=enable_short_orders,
            )

        self.data_source_settings: utils.DataSourceSettings = utils.DataSourceSettings(
            available_symbols=available_symbols,
            symbol_settings_by_symbols=symbol_settings_by_symbols,
            source=source,
        )

    def _init_order_settings(self, inputs: dict) -> None:
        self.UI.user_input(
            ORDER_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Order Settings",
            editor_options={
                enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
                # enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                # enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                UserInputEditorOptionsTypes.ANT_ICON.value: "ShoppingCartOutlined",
            },
            other_schema_values={
                UserInputOtherSchemaValuesTypes.DISPLAY_AS_TAB.value: True,
                UserInputOtherSchemaValuesTypes.TAB_ORDER.value: 12,
            },
        )
        exit_type = self.UI.user_input(
            "exit_type",
            enums.UserInputTypes.OPTIONS,
            utils.ExitTypes.SWITCH_SIDES,
            inputs,
            options=[
                utils.ExitTypes.FOUR_BARS,
                # utils.ExitTypes.DYNAMIC,
                utils.ExitTypes.SWITCH_SIDES,
            ],
            title="Exit Type",
            parent_input_name=ORDER_SETTINGS_NAME,
            other_schema_values={
                "description": "Four bars: Exits will occour exactly 4 bars "
                "after the entry. - "
                "Dynamic: attempts to let profits ride by dynamically adjusting "
                "the exit threshold based on kernel regression logic. - "
                "Switch sides: The position will switch sides on each signal.",
            },
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12},
        )
        if activate_managed_order:
            order_type = self.UI.user_input(
                "order_type",
                enums.UserInputTypes.OPTIONS,
                utils.OrderTypes.REGULAR_ORDER,
                inputs,
                options=[
                    utils.OrderTypes.MANAGED_ORDER,
                    utils.OrderTypes.REGULAR_ORDER,
                ],
                title="Order Type",
                parent_input_name=ORDER_SETTINGS_NAME,
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12
                },
            )
            uses_managed_order = order_type == utils.OrderTypes.MANAGED_ORDER
        else:
            uses_managed_order = False
        leverage: typing.Optional[int] = None
        if not uses_managed_order:
            if self.exchange_manager.is_future:
                leverage = self.UI.user_input(
                    "leverage",
                    enums.UserInputTypes.INT,
                    1,
                    inputs,
                    min_val=1,
                    max_val=125,
                    title="Leverage",
                    parent_input_name=ORDER_SETTINGS_NAME,
                    editor_options={
                        enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12
                    },
                    other_schema_values={
                        enums.UserInputOtherSchemaValuesTypes.DESCRIPTION.value: "Leverage to use for futures trades"
                    },
                )
        long_order_volume: typing.Optional[float] = None
        enable_long_orders: bool = self.UI.user_input(
            "enable_long_orders",
            enums.UserInputTypes.BOOLEAN,
            True,
            inputs,
            title="Enable long tading",
            parent_input_name=ORDER_SETTINGS_NAME,
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6},
        )
        if enable_long_orders and not uses_managed_order:
            long_order_volume = self.UI.user_input(
                "long_order_size",
                enums.UserInputTypes.TEXT,
                "50%",
                inputs,
                title="Amount to use for long trades",
                parent_input_name=ORDER_SETTINGS_NAME,
                other_schema_values={
                    enums.UserInputOtherSchemaValuesTypes.DESCRIPTION.value: "The "
                    "following syntax is supported: "
                    "1. Percent of total account: '50%' "
                    "2. Percent of availale balance: '50a%' "
                    "3. Flat amount '5' will "
                    "open a 5 BTC trade on BTC/USDT "
                },
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
                },
            )
        enable_short_orders: bool = False
        short_order_volume: typing.Optional[float] = None
        # if self.exchange_manager.is_future:
        enable_short_orders = self.UI.user_input(
            "enable_short_orders",
            enums.UserInputTypes.BOOLEAN,
            True,
            inputs,
            title="Enable short tading",
            parent_input_name=ORDER_SETTINGS_NAME,
            editor_options={enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6},
            other_schema_values={
                enums.UserInputOtherSchemaValuesTypes.DESCRIPTION.value: "Note that "
                "short trading is only working on futures or inversed short tokens"
            },
        )
        if enable_short_orders and not uses_managed_order:
            short_order_volume = self.UI.user_input(
                "short_order_size",
                enums.UserInputTypes.TEXT,
                "50%",
                inputs,
                title="Amount to use for short trades",
                parent_input_name=ORDER_SETTINGS_NAME,
                other_schema_values={
                    enums.UserInputOtherSchemaValuesTypes.DESCRIPTION.value: "The "
                    "following syntax is supported: "
                    "1. Percent of total account: '50%' "
                    "2. Percent of availale balance: '50a%' "
                    "3. Flat amount '5' will "
                    "open a 5 BTC trade on BTC/USDT "
                },
                editor_options={
                    enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 6
                },
            )
        self.order_settings: utils.LorentzianOrderSettings = (
            utils.LorentzianOrderSettings(
                enable_short_orders=enable_short_orders,
                short_order_volume=short_order_volume,
                long_order_volume=long_order_volume,
                enable_long_orders=enable_long_orders,
                leverage=leverage,
                exit_type=exit_type,
                uses_managed_order=uses_managed_order,
            )
        )

    def _init_display_settings(self, inputs: dict) -> None:
        self.UI.user_input(
            DISPLAY_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Display Settings",
            editor_options={
                enums.UserInputEditorOptionsTypes.GRID_COLUMNS.value: 12,
                # enums.UserInputEditorOptionsTypes.DISABLE_COLLAPSE.value: False,
                # enums.UserInputEditorOptionsTypes.COLLAPSED.value: True,
                UserInputEditorOptionsTypes.ANT_ICON.value: "LineChartOutlined",
            },
            other_schema_values={
                UserInputOtherSchemaValuesTypes.DISPLAY_AS_TAB.value: True,
                UserInputOtherSchemaValuesTypes.TAB_ORDER.value: 14,
            },
        )
        self.display_settings: utils.DisplaySettings = utils.DisplaySettings(
            show_bar_colors=False,
            # show_bar_colors=self.UI.user_input(
            #     "show_bar_colors",
            #     enums.UserInputTypes.BOOLEAN,
            #     True,
            #     inputs,
            #     title="Show Bar Colors",
            #     parent_input_name=DISPLAY_SETTINGS_NAME,
            #     other_schema_values={"description": "Whether to show the bar colors."},
            # ),
            show_bar_predictions=self.UI.user_input(
                "show_bar_predictions",
                enums.UserInputTypes.BOOLEAN,
                False,
                inputs,
                title="Show Bar Prediction Values",
                parent_input_name=DISPLAY_SETTINGS_NAME,
                other_schema_values={
                    "description": "Will show the ML model's evaluation "
                    "of each bar as an integer."
                },
            ),
            bar_predictions_offset=8,
            # bar_predictions_offset=self.UI.user_input(
            #     "bar_predictions_offset",
            #     enums.UserInputTypes.FLOAT,
            #     8,
            #     inputs,
            #     min_val=0,
            #     max_val=100,
            #     title="Bar Prediction Offset",
            #     parent_input_name=DISPLAY_SETTINGS_NAME,
            #     other_schema_values={
            #         "description": "The offset of the bar predictions as a percentage "
            #         "from the bar high or close."
            #     },
            # ),
            use_atr_offset=False,
            # use_atr_offset=self.UI.user_input(
            #     "use_atr_offset",
            #     enums.UserInputTypes.BOOLEAN,
            #     False,
            #     inputs,
            #     title="Use ATR Offset",
            #     parent_input_name=DISPLAY_SETTINGS_NAME,
            #     other_schema_values={
            #         "description": "Will use the ATR offset instead of "
            #         "the bar prediction offset."
            #     },
            # ),
            enable_additional_plots=self.UI.user_input(
                "enable_additional_plots",
                enums.UserInputTypes.BOOLEAN,
                False,
                inputs,
                title="Enable additional plots",
                parent_input_name=DISPLAY_SETTINGS_NAME,
            ),
            is_backtesting=self.exchange_manager.is_backtesting,
            plotting_mode=self.UI.user_input(
                "plotting_mode",
                enums.UserInputTypes.OPTIONS,
                utils.PlottingModes.REPLOT_MODE,
                inputs,
                options=[
                    utils.PlottingModes.REPLOT_MODE,
                    utils.PlottingModes.PLOT_RECORDING_MODE,
                ],
                other_schema_values={
                    enums.UserInputOtherSchemaValuesTypes.DESCRIPTION.value: "Replot "
                    "history mode will overwrite the existing plots on each bar close "
                    "and when you change settings. While plot recording mode will only "
                    "add to the plotting history on each bar close. "
                },
                title="Plotting Mode",
                parent_input_name=DISPLAY_SETTINGS_NAME,
            ),
        )
