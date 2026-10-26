"""Linear regression from scratch: gradient descent with NumPy, plots with Matplotlib."""

from .data import Dataset, StandardScaler, load_csv, make_regression, train_test_split
from .metrics import mae, mse, r2_score, rmse
from .model import LinearRegression, TrainingHistory, unscale_parameters

__all__ = [
    "Dataset",
    "LinearRegression",
    "StandardScaler",
    "TrainingHistory",
    "load_csv",
    "mae",
    "make_regression",
    "mse",
    "r2_score",
    "rmse",
    "train_test_split",
    "unscale_parameters",
]

__version__ = "1.0.0"
