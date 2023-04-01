from types import ModuleType

from tentacles.Meta.Keywords.matrix_library.basic_tentacles.RunAnalysis.RunAnalysisFactory.abstract_analysis_evaluator import (
    AnalysisEvaluator,
)


def get_installed_run_analyzer_modules(modules_root):
    available_run_analyzer_modules = {
        module_name: {
            sub_module_name: sub_module
            for sub_module_name, sub_module in module.__dict__.items()
            if isinstance(sub_module, type)
        }
        for module_name, module in modules_root.__dict__.items()
        if isinstance(module, ModuleType)
    }
    return available_run_analyzer_modules
