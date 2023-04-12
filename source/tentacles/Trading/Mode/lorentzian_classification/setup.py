import os

from setuptools import dist

dist.Distribution().fetch_build_eggs(["Cython"])

try:
    from Cython.Distutils import build_ext
    from Cython.Build import cythonize
except ImportError:
    # create closure for deferred import
    def cythonize(*args, **kwargs):
        from Cython.Build import cythonize

        return cythonize(*args, **kwargs)

    def build_ext(*args, **kwargs):
        from Cython.Distutils import build_ext

        return build_ext(*args, **kwargs)


from setuptools import setup, Extension

packages_list = [
    "classification",
    "classification_functions.classification_utils",
    "classification_functions._init__",
    "kernel_functions.kernel",
    "ml_extensions_2.ml_extensions",
    "settings",
    "trading_mode_entry",  # error
    "utils",
]

ext_modules = [
    Extension(package, [f"{package.replace('.', '/')}.py"]) for package in packages_list
]

setup(
    ext_modules=cythonize(ext_modules),
)
