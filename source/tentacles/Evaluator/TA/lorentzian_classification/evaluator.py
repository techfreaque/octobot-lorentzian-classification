# ported to python by Max https://github.com/techfreaque

# This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
# this evaluator is based on the trading view indicator from ©jdehorty
# https://www.tradingview.com/script/WhBzgfDu-Machine-Learning-Lorentzian-Classification/


# ====================
# ==== Background ====
# ====================

# When using Machine Learning algorithms like K-Nearest Neighbors, choosing an
# appropriate distance metric is essential. Euclidean Distance is often used as
# the default distance metric, but it may not always be the best choice. This is
# because market data is often significantly impacted by proximity to significant
# world events such as FOMC Meetings and Black Swan events. These major economic
# events can contribute to a warping effect analogous a massive object's
# gravitational warping of Space-Time. In financial markets, this warping effect
# operates on a continuum, which can analogously be referred to as "Price-Time".

# To help to better account for this warping effect, Lorentzian Distance can be
# used as an alternative distance metric to Euclidean Distance. The geometry of
# Lorentzian Space can be difficult to visualize at first, and one of the best
# ways to intuitively understand it is through an example involving 2 feature
# dimensions (z=2). For purposes of this example, let's assume these two features
# are Relative Strength Index (RSI) and the Average Directional Index (ADX). In
# reality, the optimal number of features is in the range of 3-8, but for the sake
# of simplicity, we will use only 2 features in this example.

# Fundamental Assumptions:
# (1) We can calculate RSI and ADX for a given chart.
# (2) For simplicity, values for RSI and ADX are assumed to adhere to a Gaussian
#     distribution in the range of 0 to 100.
# (3) The most recent RSI and ADX value can be considered the origin of a coordinate
#     system with ADX on the x-axis and RSI on the y-axis.

# Distances in Euclidean Space:
# Measuring the Euclidean Distances of historical values with the most recent point
# at the origin will yield a distribution that resembles Figure 1 (below).

#                        [RSI]
#                          |
#                          |
#                          |
#                      ...:::....
#                .:.:::••••••:::•::..
#              .:•:.:•••::::••::••....::.
#             ....:••••:••••••••::••:...:•.
#            ...:.::::::•••:::•••:•••::.:•..
#            ::•:.:•:•••••••:.:•::::::...:..
#  |--------.:•••..•••••••:••:...:::•:•:..:..----------[ADX]
#  0        :•:....:•••••::.:::•••::••:.....
#           ::....:.:••••••••:•••::••::..:.
#            .:...:••:::••••••••::•••....:
#              ::....:.....:•::•••:::::..
#                ..:..::••..::::..:•:..
#                    .::..:::.....:
#                          |
#                          |
#                          |
#                          |
#                         _|_ 0
#
#        Figure 1: Neighborhood in Euclidean Space

# Distances in Lorentzian Space:
# However, the same set of historical values measured using Lorentzian Distance will
# yield a different distribution that resembles Figure 2 (below).

#
#                         [RSI]
#  ::..                     |                    ..:::
#   .....                   |                  ......
#    .••••::.               |               :••••••.
#     .:•••••:.             |            :::••••••.
#       .•••••:...          |         .::.••••••.
#         .::•••••::..      |       :..••••••..
#            .:•••••••::.........::••••••:..
#              ..::::••••.•••••••.•••••••:.
#                ...:•••••••.•••••••••::.
#                  .:..••.••••••.••••..
#  |---------------.:•••••••••••••••••.---------------[ADX]
#  0             .:•:•••.••••••.•••••••.
#              .••••••••••••••••••••••••:.
#            .:••••••••••::..::.::••••••••:.
#          .::••••••::.     |       .::•••:::.
#         .:••••••..        |          :••••••••.
#       .:••••:...          |           ..•••••••:.
#     ..:••::..             |              :.•••••••.
#    .:•....                |               ...::.:••.
#   ...:..                  |                   :...:••.
#  :::.                     |                       ..::
#                          _|_ 0
#
#       Figure 2: Neighborhood in Lorentzian Space


# Observations:
# (1) In Lorentzian Space, the shortest distance between two points is not
#     necessarily a straight line, but rather, a geodesic curve.
# (2) The warping effect of Lorentzian distance reduces the overall influence
#     of outliers and noise.
# (3) Lorentzian Distance becomes increasingly different from Euclidean Distance
#     as the number of nearest neighbors used for comparison increases.


import math
import numpy
import tulipy

import octobot_commons.constants as commons_constants
import octobot_commons.enums as enums
import octobot_evaluators.evaluators as evaluators
import octobot_evaluators.util as evaluators_util
import octobot_trading.api as trading_api
from tentacles.Evaluator.TA.lorentzian_classification.kernel_functions import kernel
import tentacles.Evaluator.Util as EvaluatorUtil
import tentacles.Evaluator.TA.lorentzian_classification.utils as utils
import tentacles.Evaluator.TA.lorentzian_classification.ml_extensions_2.ml_extensions as ml_extensions
from tentacles.Meta.Keywords.matrix_library.matrix_basic_keywords.tools.utilities import (
    cut_data_to_same_len,
)

try:
    from tentacles.Evaluator.Util.candles_util import CandlesUtil
except (ModuleNotFoundError, ImportError) as error:
    raise RuntimeError("CandlesUtil tentacle is required to use HLC3") from error


class LorentzianClassification(evaluators.TAEvaluator):
    GENERAL_SETTINGS_NAME = "general_settings"
    FEATURE_ENGINEERING_SETTINGS_NAME = "feature_engineering_settings"
    FILTER_SETTINGS_NAME = "filter_settings"
    KERNEL_SETTINGS_NAME = "kernel_settings"
    DISPLAY_SETTINGS_NAME = "display_settings"

    general_settings: utils.Settings = None
    filter_settings: utils.FilterSettings = None
    feature_engineering_settings: utils.FeatureEngineeringSettings = None
    kernel_settings: utils.KernelSettings = None
    display_settings: utils.DisplaySettings = None
    show_trade_stats: bool = None
    use_worst_case_estimates: bool = None

    def init_user_inputs(self, inputs: dict) -> None:
        """
        Called right before starting the evaluator,
        should define all the evaluator's user inputs
        """
        self._init_general_settings(inputs)
        self._init_feature_engineering_settings(inputs)
        self._init_filter_settings(inputs)
        self._init_kernel_settings(inputs)
        self._init_display_settings(inputs)

    def _init_general_settings(self, inputs: dict) -> None:
        self.UI.user_input(
            self.GENERAL_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="General Settings",
        )
        # Settings object for user-defined settings
        self.general_settings = utils.Settings(
            source=self.UI.user_input(
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
                parent_input_name=self.GENERAL_SETTINGS_NAME,
                other_schema_values={"description": "Source of the input data"},
            ),
            neighbors_count=self.UI.user_input(
                "neighbors_count",
                enums.UserInputTypes.INT,
                8,
                inputs,
                min_val=1,
                max_val=100,
                title="Neighbors Count",
                parent_input_name=self.GENERAL_SETTINGS_NAME,
                other_schema_values={"description": "Number of neighbors to consider"},
            ),
            max_bars_back=self.UI.user_input(
                "max_bars_back",
                enums.UserInputTypes.INT,
                2000,
                inputs,
                min_val=1,
                title="Max Bars Back",
                parent_input_name=self.GENERAL_SETTINGS_NAME,
            ),
            color_compression=self.UI.user_input(
                "color_compression",
                enums.UserInputTypes.INT,
                1,
                inputs,
                min_val=1,
                max_val=10,
                title="Color Compression",
                parent_input_name=self.GENERAL_SETTINGS_NAME,
                other_schema_values={
                    "description": "Compression factor for adjusting the "
                    "intensity of the color scale."
                },
            ),
            show_default_exits=self.UI.user_input(
                "show_default_exits",
                enums.UserInputTypes.BOOLEAN,
                False,
                inputs,
                title="Show Default Exits",
                parent_input_name=self.GENERAL_SETTINGS_NAME,
                other_schema_values={
                    "description": "Default exits occur exactly 4 bars after an entry "
                    "signal. This corresponds to the predefined length of a trade "
                    "during the model's training process."
                },
            ),
            use_dynamic_exits=self.UI.user_input(
                "use_dynamic_exits",
                enums.UserInputTypes.BOOLEAN,
                False,
                inputs,
                title="Use Dynamic Exits",
                parent_input_name=self.GENERAL_SETTINGS_NAME,
                other_schema_values={
                    "description": "Dynamic exits attempt to let profits ride by "
                    "dynamically adjusting the exit threshold based "
                    "on kernel regression logic."
                },
            ),
        )
        # Trade Stats Settings
        # Note: The trade stats section is NOT intended to be used as a replacement
        # for proper backtesting. It is intended to be used for calibration purposes only.
        self.show_trade_stats = self.UI.user_input(
            "show_trade_stats",
            enums.UserInputTypes.BOOLEAN,
            True,
            inputs,
            title="Show Trade Stats",
            parent_input_name=self.GENERAL_SETTINGS_NAME,
            other_schema_values={
                "description": "Displays the trade stats for a given configuration. "
                "Useful for optimizing the settings in the Feature Engineering section."
                " This should NOT replace backtesting and should be used for "
                "calibration purposes only. Early Signal Flips represent instances "
                "where the model changes signals before 4 bars elapses; high values can"
                " indicate choppy (ranging) market conditions."
            },
        )
        self.use_worst_case_estimates = self.UI.user_input(
            "use_worst_case_estimates",
            enums.UserInputTypes.BOOLEAN,
            False,
            inputs,
            title="Use Worst Case Estimates",
            parent_input_name=self.GENERAL_SETTINGS_NAME,
            other_schema_values={
                "description": "Whether to use the worst case scenario for backtesting."
                " This option can be useful for creating a conservative estimate that "
                "is based on close prices only, thus avoiding the effects of intrabar "
                "repainting. This option assumes that the user does not enter when the "
                "signal first appears and instead waits for the bar to close as "
                "confirmation. On larger timeframes, this can mean entering after a "
                "large move has already occurred. Leaving this option disabled is "
                "generally better for those that use this indicator as a source of "
                "confluence and prefer estimates that demonstrate discretionary "
                "mid-bar entries. Leaving this option enabled may be more consistent "
                "with traditional backtesting results."
            },
        )

    def _init_feature_engineering_settings(self, inputs: dict) -> None:
        # Feature Variables: User-Defined Inputs for calculating Feature Series.
        self.UI.user_input(
            self.FEATURE_ENGINEERING_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Feature Engineering Settings",
        )
        feature_count = self.UI.user_input(
            "feature_count",
            enums.UserInputTypes.INT,
            5,
            inputs,
            min_val=2,
            max_val=5,
            title="Feature Count",
            parent_input_name=self.FEATURE_ENGINEERING_SETTINGS_NAME,
            other_schema_values={
                "description": "Number of features to use for ML predictions."
            },
        )
        feature_1_settings_name = "feature_1_settings"
        self.UI.user_input(
            feature_1_settings_name,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Feature 1",
            parent_input_name=self.FEATURE_ENGINEERING_SETTINGS_NAME,
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
        feature_2_settings_name = "feature_2_settings"
        self.UI.user_input(
            feature_2_settings_name,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Feature 2",
            parent_input_name=self.FEATURE_ENGINEERING_SETTINGS_NAME,
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
                parent_input_name=self.FEATURE_ENGINEERING_SETTINGS_NAME,
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
                    "description": "The secondary parameter of feature 3 (if applicable)."
                },
                parent_input_name=feature_3_settings_name,
            )
            if feature_count > 3:
                feature_4_settings_name = "feature_4_settings"
                self.UI.user_input(
                    feature_4_settings_name,
                    enums.UserInputTypes.OBJECT,
                    None,
                    inputs,
                    title="Feature 4",
                    parent_input_name=self.FEATURE_ENGINEERING_SETTINGS_NAME,
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
                        "description": "The secondary parameter of feature 4 (if applicable)."
                    },
                    parent_input_name=feature_4_settings_name,
                )
                if feature_count > 4:
                    feature_5_settings_name = "feature_5_settings"
                    self.UI.user_input(
                        feature_5_settings_name,
                        enums.UserInputTypes.OBJECT,
                        None,
                        inputs,
                        title="Feature 5",
                        parent_input_name=self.FEATURE_ENGINEERING_SETTINGS_NAME,
                    )

                    f5_string = self.UI.user_input(
                        "f5_string",
                        enums.UserInputTypes.OPTIONS,
                        title="Feature 5",
                        def_val="RSI",
                        registered_inputs=inputs,
                        options=["RSI", "WT", "CCI", "ADX"],
                        other_schema_values={
                            "description": "The fifth feature to use for ML predictions."
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
                            "description": "The secondary parameter of feature 5 (if applicable)."
                        },
                        parent_input_name=feature_5_settings_name,
                    )
        self.feature_engineering_settings = utils.FeatureEngineeringSettings(
            feature_count=feature_count,
            f1_string=f1_string,
            f1_paramA=f1_paramA,
            f1_paramB=f1_paramB,
            f2_string=f2_string,
            f2_paramA=f2_paramA,
            f2_paramB=f2_paramB,
            f3_string=f3_string,
            f3_paramA=f3_paramA,
            f3_paramB=f3_paramB,
            f4_string=f4_string,
            f4_paramA=f4_paramA,
            f4_paramB=f4_paramB,
            f5_string=f5_string,
            f5_paramA=f5_paramA,
            f5_paramB=f5_paramB,
        )

    def _init_display_settings(self, inputs: dict) -> None:
        self.UI.user_input(
            self.DISPLAY_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Display Settings",
        )
        self.kernel_settings: utils.DisplaySettings = utils.DisplaySettings(
            show_bar_colors=self.UI.user_input(
                "show_bar_colors",
                enums.UserInputTypes.BOOLEAN,
                True,
                inputs,
                title="Show Bar Colors",
                parent_input_name=self.DISPLAY_SETTINGS_NAME,
                other_schema_values={"description": "Whether to show the bar colors."},
            ),
            show_bar_predictions=self.UI.user_input(
                "show_bar_predictions",
                enums.UserInputTypes.BOOLEAN,
                True,
                inputs,
                title="Show Bar Prediction Values",
                parent_input_name=self.DISPLAY_SETTINGS_NAME,
                other_schema_values={
                    "description": "Will show the ML model's evaluation "
                    "of each bar as an integer."
                },
            ),
            use_atr_offset=self.UI.user_input(
                "use_atr_offset",
                enums.UserInputTypes.BOOLEAN,
                False,
                inputs,
                title="Use ATR Offset",
                parent_input_name=self.DISPLAY_SETTINGS_NAME,
                other_schema_values={
                    "description": "Will use the ATR offset instead of "
                    "the bar prediction offset."
                },
            ),
            bar_predictions_offset=self.UI.user_input(
                "bar_predictions_offset",
                enums.UserInputTypes.FLOAT,
                8,
                inputs,
                min_val=0,
                max_val=100,
                title="Bar Prediction Offset",
                parent_input_name=self.DISPLAY_SETTINGS_NAME,
                other_schema_values={
                    "description": "The offset of the bar predictions as a percentage "
                    "from the bar high or close."
                },
            ),
        )

    def _init_kernel_settings(self, inputs: dict) -> None:
        self.UI.user_input(
            self.KERNEL_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Kernel Settings",
        )
        self.kernel_settings: utils.KernelSettings = utils.KernelSettings(
            use_kernel_filter=self.UI.user_input(
                "use_kernel_filter",
                enums.UserInputTypes.BOOLEAN,
                True,
                inputs,
                title="Trade with Kernel",
                parent_input_name=self.KERNEL_SETTINGS_NAME,
            ),
            show_kernel_estimate=self.UI.user_input(
                "show_kernel_estimate",
                enums.UserInputTypes.BOOLEAN,
                True,
                inputs,
                title="Show Kernel Estimate",
                parent_input_name=self.KERNEL_SETTINGS_NAME,
            ),
            use_kernel_smoothing=self.UI.user_input(
                "use_kernel_smoothing",
                enums.UserInputTypes.BOOLEAN,
                False,
                inputs,
                title="Enhance Kernel Smoothing",
                parent_input_name=self.KERNEL_SETTINGS_NAME,
                other_schema_values={
                    "description": "Uses a crossover based mechanism "
                    "to smoothen kernel color changes. This often "
                    "results in less color transitions overall and "
                    "may result in more ML entry signals being generated."
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
                parent_input_name=self.KERNEL_SETTINGS_NAME,
                other_schema_values={
                    "description": "The number of bars used for the estimation. This is"
                    " a sliding value that represents the most recent historical bars. "
                    "Recommended range: 3-50"
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
                parent_input_name=self.KERNEL_SETTINGS_NAME,
                other_schema_values={
                    "description": "Relative weighting of time frames. As this value "
                    "approaches zero, the longer time frames will exert more influence "
                    "on the estimation. As this value approaches infinity, the behavior"
                    " of the Rational Quadratic Kernel will become identical to the "
                    "Gaussian kernel. Recommended range: 0.25-25"
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
                parent_input_name=self.KERNEL_SETTINGS_NAME,
                other_schema_values={
                    "description": "Bar index on which to start regression. Controls "
                    "how tightly fit the kernel estimate is to the data. Smaller values"
                    " are a tighter fit. Larger values are a looser fit. Recommended "
                    "range: 2-25"
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
                parent_input_name=self.KERNEL_SETTINGS_NAME,
                other_schema_values={
                    "description": "Lag for crossover detection. Lower values result in"
                    " earlier crossovers. Recommended range: 1-2"
                },
            ),
        )

    def _init_filter_settings(self, inputs: dict) -> None:
        self.UI.user_input(
            self.FILTER_SETTINGS_NAME,
            enums.UserInputTypes.OBJECT,
            None,
            inputs,
            title="Filter Settings",
        )
        self.filter_settings: utils.FilterSettings = utils.FilterSettings(
            use_volatility_filter=self.UI.user_input(
                "use_volatility_filter",
                enums.UserInputTypes.BOOLEAN,
                True,
                inputs,
                title="Use Volatility Filter",
                parent_input_name=self.FILTER_SETTINGS_NAME,
                other_schema_values={
                    "description": "Whether to use the volatility filter."
                },
            ),
            use_regime_filter=self.UI.user_input(
                "use_regime_filter",
                enums.UserInputTypes.BOOLEAN,
                True,
                inputs,
                title="Use Regime Filter",
                parent_input_name=self.FILTER_SETTINGS_NAME,
            ),
            regime_threshold=self.UI.user_input(
                "regime_threshold",
                enums.UserInputTypes.FLOAT,
                -0.1,
                inputs,
                min_val=-10,
                max_val=10,
                title="Regime Threshold",
                parent_input_name=self.FILTER_SETTINGS_NAME,
                other_schema_values={
                    "description": "Whether to use the trend detection filter. "
                    "Threshold for detecting Trending/Ranging markets. Use steps of 0.1"
                },
            ),
            use_adx_filter=self.UI.user_input(
                "use_adx_filter",
                enums.UserInputTypes.BOOLEAN,
                False,
                inputs,
                title="Use ADX Filter",
                parent_input_name=self.FILTER_SETTINGS_NAME,
            ),
            adx_threshold=self.UI.user_input(
                "adx_threshold",
                enums.UserInputTypes.INT,
                20,
                inputs,
                min_val=0,
                max_val=100,
                title="ADX Threshold",
                parent_input_name=self.FILTER_SETTINGS_NAME,
                other_schema_values={
                    "description": "Whether to use the ADX filter. Threshold for detecting"
                    " Trending/Ranging markets."
                },
            ),
            use_ema_filter=self.UI.user_input(
                "use_ema_filter",
                enums.UserInputTypes.BOOLEAN,
                False,
                inputs,
                title="Use EMA Filter",
                parent_input_name=self.FILTER_SETTINGS_NAME,
            ),
            ema_period=self.UI.user_input(
                "ema_period",
                enums.UserInputTypes.INT,
                200,
                inputs,
                min_val=1,
                title="EMA Period",
                parent_input_name=self.FILTER_SETTINGS_NAME,
                other_schema_values={
                    "description": "The period of the EMA used for the EMA Filter."
                },
            ),
            use_sma_filter=self.UI.user_input(
                "use_sma_filter",
                enums.UserInputTypes.BOOLEAN,
                False,
                inputs,
                title="Use SMA Filter",
                parent_input_name=self.FILTER_SETTINGS_NAME,
            ),
            sma_period=self.UI.user_input(
                "sma_period",
                enums.UserInputTypes.INT,
                200,
                inputs,
                min_val=1,
                title="SMA Period",
                parent_input_name=self.FILTER_SETTINGS_NAME,
                other_schema_values={
                    "description": "The period of the SMA used for the SMA Filter."
                },
            ),
        )

    async def ohlcv_callback(
        self,
        exchange: str,
        exchange_id: str,
        cryptocurrency: str,
        symbol: str,
        time_frame,
        candle,
        inc_in_construction_data,
    ):
        await self.evaluate(
            cryptocurrency,
            symbol,
            time_frame,
            candle,
            inc_in_construction_data,
            exchange,
            exchange_id,
        )

    async def evaluate(
        self,
        cryptocurrency,
        symbol,
        time_frame,
        candle,
        inc_in_construction_data,
        exchange,
        exchange_id,
    ):
        (
            candle_closes,
            candle_highs,
            candle_lows,
            candles_hlc3,
            candles_ohlc4,
            user_selected_candles,
        ) = self._get_candle_data(
            candle_source_name=self.general_settings.source,
            exchange=exchange,
            exchange_id=exchange_id,
            symbol=symbol,
            time_frame=time_frame,
            inc_in_construction_data=inc_in_construction_data,
        )
        data_length = len(candle_highs)
        _filters: utils.Filter = self._get_filters(
            candle_closes,
            data_length,
            candles_ohlc4,
            candle_highs,
            candle_lows,
            user_selected_candles,
        )

        (
            alerts_bullish,
            alerts_bearish,
            is_bullishs,
            is_bearishs,
            is_bearish_changes,
            is_bullish_changes,
        ) = self.get_kernel_data(user_selected_candles, data_length)

        feature_arrays: utils.FeatureArrays = self.get_feature_arrays(
            candle_closes=candle_closes,
            candle_highs=candle_highs,
            candle_lows=candle_lows,
            candles_hlc3=candles_hlc3,
        )

        y_train_series = self.get_y_train_series(user_selected_candles)

        # cut all historical data to same length for numpy and loop indizies being aligned
        (
            y_train_series,
            _filters.filter_all,
            _filters.is_uptrend,
            _filters.is_downtrend,
            candle_closes,
            candle_highs,
            candle_lows,
            candles_hlc3,
            candles_ohlc4,
            feature_arrays.f1,
            feature_arrays.f2,
            feature_arrays.f3,
            feature_arrays.f4,
            feature_arrays.f5,
            is_bullishs,
            is_bearishs,
            alerts_bullish,
            alerts_bearish,
        ) = cut_data_to_same_len(
            (
                y_train_series,
                _filters.filter_all,
                _filters.is_uptrend,
                _filters.is_downtrend,
                candle_closes,
                candle_highs,
                candle_lows,
                candles_hlc3,
                user_selected_candles,
                feature_arrays.f1,
                feature_arrays.f2,
                feature_arrays.f3,
                feature_arrays.f4,
                feature_arrays.f5,
                is_bullishs,
                is_bearishs,
                alerts_bullish,
                alerts_bearish,
            )
        )
        cutted_data_length = len(candle_closes)
        max_bars_back_index = self.get_max_bars_back_index(cutted_data_length)

        # =================================
        # ==== Next Bar Classification ====
        # =================================

        # This model specializes specifically in predicting the direction of price
        # action over the course of the next 4 bars.
        # To avoid complications with the ML model, this value is hardcoded to 4 bars
        # but support for other training lengths may be added in the future.

        previous_signals: list = [utils.SignalDirection.neutral]
        bars_held: int = 0
        previous_is_valid_short_exit = False
        previous_is_valid_long_exit = False
        for candle_index in range(max_bars_back_index, data_length):
            predictions = numpy.array()
            distances = numpy.array()
            this_y_train_series = y_train_series[:candle_index]
            # Variables used for ML Logic
            prediction: float = 0

            # =========================
            # ====  Core ML Logic  ====
            # =========================

            # Approximate Nearest Neighbors Search with Lorentzian Distance:
            # A novel variation of the Nearest Neighbors (NN) search algorithm that ensures
            # a chronologically uniform distribution of neighbors.

            # In a traditional KNN-based approach, we would iterate through the entire
            # dataset and calculate the distance between the current bar
            # and every other bar in the dataset and then sort the distances in ascending
            # order. We would then take the first k bars and use their
            # labels to determine the label of the current bar.

            # There are several problems with this traditional KNN approach in the context
            # of real-time calculations involving time series data:
            # - It is computationally expensive to iterate through the entire dataset and
            #   calculate the distance between every historical bar and
            #   the current bar.
            # - Market time series data is often non-stationary, meaning that the
            #   statistical properties of the data change slightly over time.
            # - It is possible that the nearest neighbors are not the most informative ones,
            #   and the KNN algorithm may return poor results if the
            #   nearest neighbors are not representative of the majority of the data.

            # Previously, the user @capissimo attempted to address some of these issues in
            # several of his PineScript-based KNN implementations by:
            # - Using a modified KNN algorithm based on consecutive furthest neighbors to
            #   find a set of approximate "nearest" neighbors.
            # - Using a sliding window approach to only calculate the distance between the
            #   current bar and the most recent n bars in the dataset.

            # Of these two approaches, the latter is inherently limited by the fact that it
            # only considers the most recent bars in the overall dataset.

            # The former approach has more potential to leverage historical price action,
            # but is limited by:
            # - The possibility of a sudden "max" value throwing off the estimation
            # - The possibility of selecting a set of approximate neighbors that are not
            #       representative of the majority of the data by oversampling
            #       values that are not chronologically distinct enough from one another
            # - The possibility of selecting too many "far" neighbors,
            #       which may result in a poor estimation of price action

            # To address these issues, a novel Approximate Nearest Neighbors (ANN)
            # algorithm is used in this indicator.

            # In the below ANN algorithm:
            # 1. The algorithm iterates through the dataset in chronological order,
            #       using the modulo operator to only perform calculations every 4 bars.
            #       This serves the dual purpose of reducing the computational overhead of
            #       the algorithm and ensuring a minimum chronological spacing
            #       between the neighbors of at least 4 bars.
            # 2. A list of the k-similar neighbors is simultaneously maintained in both a
            #       predictions array and corresponding distances array.
            # 3. When the size of the predictions array exceeds the desired number of
            #       nearest neighbors specified in settings.neighborsCount,
            #       the algorithm removes the first neighbor from the predictions
            #       array and the corresponding distance array.
            # 4. The lastDistance variable is overriden to be a distance in the lower 25% of
            #       the array. This step helps to boost overall accuracy by ensuring
            #       subsequent newly added distance values increase at a slower rate.
            # 5. Lorentzian distance is used as a distance metric in order to minimize the
            #       effect of outliers and take into account the warping of
            #       "price-time" due to proximity to significant economic events.

            last_distance: float = -1
            size: int = min(
                self.general_settings.max_bars_back - 1, len(this_y_train_series) - 1
            )
            size_Loop: int = min(self.general_settings.max_bars_back - 1, size) + 1
            distances: list = []
            predictions: list = []
            start_long_trades: list = []
            start_short_trades: list = []
            for candles_back in range(0, size_Loop):
                # TODO check if index is right
                candles_back_index = candle_index - candles_back
                lorentzian_distance = self.get_lorentzian_distance(
                    candle_index=candle_index,
                    candles_back_index=candles_back_index,
                    feature_arrays=feature_arrays,
                )
                if lorentzian_distance >= last_distance and candles_back % 4:
                    last_distance = lorentzian_distance
                    distances.append(lorentzian_distance)
                    predictions.append(round(this_y_train_series[candles_back_index]))
                    if len(predictions) > self.general_settings.neighbors_count:
                        last_distance = distances[
                            round(self.general_settings.neighbors_count * 3 / 4)
                        ]
                        del distances[0]
                        del predictions[0]
            prediction = sum(predictions)
            # ============================
            # ==== Prediction Filters ====
            # ============================

            # Filtered Signal: The model's prediction of future price movement direction with user-defined filters applied
            signal = (
                utils.SignalDirection.long
                if prediction > 0 and _filters.filter_all[candle_index]
                else (
                    utils.SignalDirection.short
                    if prediction < 0 and _filters.filter_all[candle_index]
                    else previous_signals
                )
            )
            is_different_signal_type: bool = previous_signals[-1] != signal
            # Bar-Count Filters: Represents strict filters based on a pre-defined holding period of 4 bars
            if is_different_signal_type:
                bars_held = 0
            else:
                bars_held += 1
            is_held_four_bars = bars_held == 4
            is_held_less_than_four_bars = 0 < bars_held and bars_held < 4

            # Fractal Filters: Derived from relative appearances of signals in a given time series fractal/segment with a default length of 4 bars
            is_early_signal_flip = previous_signals[-1] and (
                previous_signals[-2] or previous_signals[-3] or previous_signals[-4]
            )
            is_buy_signal = (
                signal == utils.SignalDirection.long
                and _filters.is_uptrend[candle_index]
            )
            is_sell_signal = (
                signal == utils.SignalDirection.short
                and _filters.is_downtrend[candle_index]
            )
            is_last_signal_buy = (
                signal[-5] == utils.SignalDirection.long
                and _filters.is_uptrend[candle_index - 4]
            )
            is_last_signal_sell = (
                signal[-5] == utils.SignalDirection.short
                and _filters.is_downtrend[candle_index - 4]
            )
            is_new_buy_signal = is_buy_signal and is_different_signal_type
            is_new_sell_signal = is_sell_signal and is_different_signal_type

            # ===========================
            # ==== Entries and Exits ====
            # ===========================

            # Entry Conditions: Booleans for ML Model Position Entries
            start_long_trade = (
                is_new_buy_signal
                and is_bullishs[candle_index]
                and _filters.is_uptrend[candle_index]
            )
            start_long_trades.append(start_long_trade)
            if start_long_trade:
                bars_since_green_entry = 0
            else:
                bars_since_green_entry += 1
            start_short_trade = (
                is_new_sell_signal
                and is_bearishs[candle_index]
                and _filters.is_downtrend[candle_index]
            )
            start_short_trades.append(start_short_trade)
            if start_short_trade:
                bars_since_red_entry = 0
            else:
                bars_since_red_entry += 1

            if alerts_bullish[candle_index]:
                bars_since_red_exit = 0
            else:
                bars_since_red_exit += 1
            if alerts_bearish[candle_index]:
                bars_since_green_exit = 0
            else:
                bars_since_green_exit += 1

            # Dynamic Exit Conditions: Booleans for ML Model Position Exits based on Fractal Filters and Kernel Regression Filters
            last_signal_was_bullish = bars_since_green_entry < bars_since_red_entry
            last_signal_was_bearish = bars_since_red_entry < bars_since_green_entry
            is_valid_short_exit = bars_since_green_exit > bars_since_red_entry
            is_valid_long_exit = bars_since_green_exit > bars_since_green_entry
            end_long_trade_dynamic = (
                is_bearish_changes[candle_index] and previous_is_valid_long_exit
            )
            end_short_trade_dynamic = (
                is_bullish_changes[candle_index] and previous_is_valid_short_exit
            )
            previous_is_valid_short_exit = is_valid_short_exit
            previous_is_valid_long_exit = is_valid_long_exit

            # Fixed Exit Conditions: Booleans for ML Model Position Exits based on a Bar-Count Filters
            end_long_trade_strict = (
                (is_held_four_bars and is_last_signal_buy)
                or (
                    is_held_less_than_four_bars
                    and is_new_sell_signal
                    and is_last_signal_buy
                )
            ) and start_long_trades[-5]
            end_short_trade_strict = (
                (is_held_four_bars and is_last_signal_sell)
                or (
                    is_held_less_than_four_bars
                    and is_new_buy_signal
                    and is_last_signal_sell
                )
            ) and start_short_trades[-5]
            is_dynamic_exit_valid = (
                not self.filter_settings.use_ema_filter
                and not self.filter_settings.use_sma_filter
                and not self.kernel_settings.use_kernel_smoothing
            )
            end_long_trade = self.general_settings.use_dynamic_exits and (
                end_long_trade_dynamic
                if is_dynamic_exit_valid
                else end_long_trade_strict
            )
            end_short_trade = self.general_settings.use_dynamic_exits and (
                end_short_trade_dynamic
                if is_dynamic_exit_valid
                else end_short_trade_strict
            )

            previous_signals.append(signal)

        # self.set_eval_note(signal * -1)  # OctoBot signals are reversed
        await self.evaluation_completed(
            cryptocurrency,
            symbol,
            time_frame,
            eval_time=evaluators_util.get_eval_time(
                full_candle=candle, time_frame=time_frame
            ),
        )
        return
        # self.eval_note = commons_constants.START_PENDING_EVAL_NOTE
        # await self.evaluation_completed(
        #     cryptocurrency,
        #     symbol,
        #     time_frame,
        #     eval_time=evaluators_util.get_eval_time(
        #         full_candle=candle, time_frame=time_frame
        #     ),
        # )

    @classmethod
    def get_is_symbol_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not symbol dependant else False
        """
        return False

    @classmethod
    def get_is_time_frame_wildcard(cls) -> bool:
        """
        :return: True if the evaluator is not time_frame dependant else False
        """
        return False

    def get_filters(self, candle_closes, data_length):
        if self.filter_settings.use_ema_filter:
            filter_ema_candles, filter_ema = cut_data_to_same_len(
                (
                    candle_closes,
                    tulipy.ema(candle_closes, self.filter_settings.ema_period),
                )
            )
            is_ema_uptrend = filter_ema_candles > filter_ema
            is_ema_downtrend = filter_ema_candles < filter_ema
        else:
            is_ema_uptrend = [True] * data_length
            is_ema_downtrend = [True] * data_length
        if self.filter_settings.use_ema_filter:
            filter_sma_candles, filter_sma = cut_data_to_same_len(
                (
                    candle_closes,
                    tulipy.sma(candle_closes, self.filter_settings.sma_period),
                )
            )
            is_sma_uptrend = filter_sma_candles > filter_sma
            is_sma_downtrend = filter_sma_candles < filter_sma
        else:
            is_sma_uptrend = [True] * data_length
            is_sma_downtrend = [True] * data_length
        return is_ema_uptrend, is_ema_downtrend, is_sma_uptrend, is_sma_downtrend

    def get_y_train_series(self, user_selected_candles):
        # TODO check if 4/-5 is same as on tradingview
        cutted_candles, shifted_candles = utils.shift_data(user_selected_candles, 4)
        return numpy.where(
            shifted_candles < cutted_candles,
            utils.SignalDirection.short,
            numpy.where(
                shifted_candles > cutted_candles,
                utils.SignalDirection.long,
                utils.SignalDirection.neutral,
            ),
        )

    def get_lorentzian_distance(
        self,
        candle_index: int,
        candles_back_index: int,
        feature_arrays: utils.FeatureArrays,
    ) -> float:
        if self.feature_engineering_settings.feature_count == 5:
            return (
                math.log(
                    1
                    + abs(
                        feature_arrays.f1[candle_index]
                        - feature_arrays.f1[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f2[candle_index]
                        - feature_arrays.f2[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f3[candle_index]
                        - feature_arrays.f3[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f4[candle_index]
                        - feature_arrays.f4[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f5[candle_index]
                        - feature_arrays.f5[candles_back_index]
                    )
                )
            )
        elif self.feature_engineering_settings.feature_count == 4:
            return (
                math.log(
                    1
                    + abs(
                        feature_arrays.f1[candle_index]
                        - feature_arrays.f1[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f2[candle_index]
                        - feature_arrays.f2[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f3[candle_index]
                        - feature_arrays.f3[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f4[candle_index]
                        - feature_arrays.f4[candles_back_index]
                    )
                )
            )
        elif self.feature_engineering_settings.feature_count == 3:
            return (
                math.log(
                    1
                    + abs(
                        feature_arrays.f1[candle_index]
                        - feature_arrays.f1[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f2[candle_index]
                        - feature_arrays.f2[candles_back_index]
                    )
                )
                + math.log(
                    1
                    + abs(
                        feature_arrays.f3[candle_index]
                        - feature_arrays.f3[candles_back_index]
                    )
                )
            )
        elif self.feature_engineering_settings.feature_count == 2:
            return math.log(
                1
                + abs(
                    feature_arrays.f1[candle_index]
                    - feature_arrays.f1[candles_back_index]
                )
            ) + math.log(
                1
                + abs(
                    feature_arrays.f2[candle_index]
                    - feature_arrays.f2[candles_back_index]
                )
            )

    def _get_filters(
        self,
        candle_closes,
        data_length,
        candles_ohlc4,
        candle_highs,
        candle_lows,
        user_selected_candles,
    ) -> utils.Filter:

        # Filter object for filtering the ML predictions
        (
            is_ema_uptrend,
            is_ema_downtrend,
            is_sma_uptrend,
            is_sma_downtrend,
        ) = self.get_filters(candle_closes, data_length)
        _filter: utils.Filter = utils.Filter(
            volatility=ml_extensions.filter_volatility(
                candle_highs=candle_highs,
                candle_lows=candle_lows,
                candle_closes=candle_closes,
                min_length=1,
                max_length=10,
                use_volatility_filter=self.filter_settings.use_volatility_filter,
            ),
            regime=ml_extensions.regime_filter(
                ohlc4=candles_ohlc4,
                highs=candle_highs,
                lows=candle_lows,
                threshold=self.filter_settings.regime_threshold,
                use_regime_filter=self.filter_settings.use_regime_filter,
            ),
            adx=ml_extensions.filter_adx(
                candle_closes=user_selected_candles,
                candle_highs=candle_highs,
                candle_lows=candle_lows,
                length=14,
                adx_threshold=self.filter_settings.adx_threshold,
                use_adx_filter=self.filter_settings.use_adx_filter,
            ),
            is_ema_uptrend=is_ema_uptrend,
            is_ema_downtrend=is_ema_downtrend,
            is_sma_uptrend=is_sma_uptrend,
            is_sma_downtrend=is_sma_downtrend,
        )
        return _filter

    def get_feature_arrays(
        self, candle_closes, candle_highs, candle_lows, candles_hlc3
    ) -> utils.FeatureArrays:
        return utils.FeatureArrays(
            f1=utils.series_from(
                self.feature_engineering_settings.f1_string,
                candle_closes,
                candle_highs,
                candle_lows,
                candles_hlc3,
                self.feature_engineering_settings.f1_paramA,
                self.feature_engineering_settings.f1_paramB,
            ),
            f2=utils.series_from(
                self.feature_engineering_settings.f2_string,
                candle_closes,
                candle_highs,
                candle_lows,
                candles_hlc3,
                self.feature_engineering_settings.f2_paramA,
                self.feature_engineering_settings.f2_paramB,
            ),
            f3=utils.series_from(
                self.feature_engineering_settings.f3_string,
                candle_closes,
                candle_highs,
                candle_lows,
                candles_hlc3,
                self.feature_engineering_settings.f3_paramA,
                self.feature_engineering_settings.f3_paramB,
            ),
            f4=utils.series_from(
                self.feature_engineering_settings.f4_string,
                candle_closes,
                candle_highs,
                candle_lows,
                candles_hlc3,
                self.feature_engineering_settings.f4_paramA,
                self.feature_engineering_settings.f4_paramB,
            ),
            f5=utils.series_from(
                self.feature_engineering_settings.f5_string,
                candle_closes,
                candle_highs,
                candle_lows,
                candles_hlc3,
                self.feature_engineering_settings.f5_paramA,
                self.feature_engineering_settings.f5_paramB,
            ),
        )

    def get_kernel_data(self, user_selected_candles, data_length: int) -> tuple:
        # c_green = color.new(#009988, 20)
        # c_red = color.new(#CC3311, 20)
        # transparent = color.new(#000000, 100)
        yhat1: numpy.array = kernel.rationalQuadratic(
            user_selected_candles,
            self.kernel_settings.lookback_window,
            self.kernel_settings.relative_weighting,
            self.kernel_settings.regression_level,
        )
        yhat2: numpy.array = kernel.gaussian(
            user_selected_candles,
            self.kernel_settings.lookback_window - self.kernel_settings.lag,
            self.kernel_settings.regression_level,
        )
        yhat1, yhat2 = cut_data_to_same_len((yhat1, yhat2))

        kernelEstimate: numpy.array = yhat1
        # Kernel Rates of Change
        # shift and cut data for numpy
        yhat1_cutted_1, yhat1_shifted_1 = utils.shift_data(yhat1, 1)
        yhat1_cutted_2, yhat1_shifted_2 = utils.shift_data(yhat1_shifted_1, 1)
        was_bearish_rates: numpy.array = yhat1_shifted_2 > yhat1_cutted_2
        was_bullish_rates: numpy.array = yhat1_shifted_2 < yhat1_cutted_2
        is_bearish_rates: numpy.array = yhat1_shifted_1 > yhat1_cutted_1
        is_bullish_rates: numpy.array = yhat1_shifted_1 < yhat1_cutted_1
        is_bearish_changes: numpy.array = numpy.logical_and(
            is_bearish_rates, was_bullish_rates
        )
        is_bullish_changes: numpy.array = numpy.logical_and(
            is_bullish_rates, was_bearish_rates
        )
        # Kernel Crossovers
        is_bullish_cross_alerts, is_bearish_cross_alerts = utils.get_is_crossing_data(
            yhat2, yhat1
        )
        is_bullish_smooths: numpy.array = yhat2 >= yhat1
        is_bearish_smooths: numpy.array = yhat2 <= yhat1

        # # Kernel Colors
        # # color colorByCross = isBullishSmooth ? c_green : c_red
        # # color colorByRate = isBullishRate ? c_green : c_red
        # # color plotColor = showKernelEstimate ? (useKernelSmoothing ? colorByCross : colorByRate) : transparent
        # # plot(kernelEstimate, color=plotColor, linewidth=2, title="Kernel Regression Estimate")
        # # Alert Variables
        alerts_bullish = (
            is_bullish_cross_alerts
            if self.kernel_settings.use_kernel_smoothing
            else is_bullish_changes
        )
        alerts_bearish = (
            is_bearish_cross_alerts
            if self.kernel_settings.use_kernel_smoothing
            else is_bearish_changes
        )
        # Bullish and Bearish Filters based on Kernel
        is_bullishs: numpy.array = (
            (
                is_bullish_smooths
                if self.kernel_settings.use_kernel_smoothing
                else is_bullish_rates
            )
            if self.kernel_settings.use_kernel_filter
            else [True] * data_length
        )
        is_bearishs: numpy.array = (
            (
                is_bearish_smooths
                if self.kernel_settings.use_kernel_smoothing
                else is_bearish_rates
            )
            if self.kernel_settings.use_kernel_filter
            else [True] * data_length
        )
        return (
            alerts_bullish,
            alerts_bearish,
            is_bullishs,
            is_bearishs,
            is_bearish_changes,
            is_bullish_changes,
        )

    def _get_candle_data(
        self,
        candle_source_name,
        exchange,
        exchange_id,
        symbol,
        time_frame,
        inc_in_construction_data,
    ):
        candle_opens = trading_api.get_symbol_open_candles(
            self.get_exchange_symbol_data(exchange, exchange_id, symbol),
            time_frame,
            include_in_construction=inc_in_construction_data,
        )
        candle_closes = trading_api.get_symbol_close_candles(
            self.get_exchange_symbol_data(exchange, exchange_id, symbol),
            time_frame,
            include_in_construction=inc_in_construction_data,
        )
        candle_highs = trading_api.get_symbol_high_candles(
            self.get_exchange_symbol_data(exchange, exchange_id, symbol),
            time_frame,
            include_in_construction=inc_in_construction_data,
        )
        candle_lows = trading_api.get_symbol_low_candles(
            self.get_exchange_symbol_data(exchange, exchange_id, symbol),
            time_frame,
            include_in_construction=inc_in_construction_data,
        )
        candles_hlc3 = CandlesUtil.HLC3(
            candle_highs,
            candle_lows,
            candle_closes,
        )
        candles_ohlc4 = CandlesUtil.OHLC4(
            candle_opens,
            candle_highs,
            candle_lows,
            candle_closes,
        )
        user_selected_candles = None
        if candle_source_name == enums.PriceStrings.STR_PRICE_CLOSE.value:
            user_selected_candles = candle_closes
        if candle_source_name == enums.PriceStrings.STR_PRICE_OPEN.value:
            user_selected_candles = trading_api.get_symbol_opeb_candles(
                self.get_exchange_symbol_data(exchange, exchange_id, symbol),
                time_frame,
                include_in_construction=inc_in_construction_data,
            )
        if candle_source_name == enums.PriceStrings.STR_PRICE_HIGH.value:
            user_selected_candles = candle_highs
        if candle_source_name == enums.PriceStrings.STR_PRICE_LOW.value:
            user_selected_candles = candle_lows
        if candle_source_name == "hlc3":
            user_selected_candles = candles_hlc3
        if candle_source_name == "ohlc4":
            user_selected_candles = candles_ohlc4
        return (
            candle_closes,
            candle_highs,
            candle_lows,
            candles_hlc3,
            candles_ohlc4,
            user_selected_candles,
        )

    def get_max_bars_back_index(self, cutted_data_length) -> int:
        if cutted_data_length >= self.general_settings.max_bars_back:
            return cutted_data_length - self.general_settings.max_bars_back
        else:
            # todo logger warning
            return cutted_data_length
