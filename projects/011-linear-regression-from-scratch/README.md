# Linear Regression From Scratch

Linear regression trained with **gradient descent**, written with nothing but
NumPy. Matplotlib plots show the fitted line, the training loss, and the path
gradient descent takes across the loss surface. No scikit-learn: every update
rule, metric and scaler is implemented and tested here.

```
$ make demo
Data: synthetic: y = 3·x1 + 4 + N(0, 2²)
      200 samples, 1 feature(s), 160 train / 40 test

solver      epochs   train MSE  test RMSE  test R²
--------------------------------------------------
batch         2000      4.4403     1.7884   0.9610
sgd           2000      9.0032     2.5270   0.9222
minibatch     2000      4.4436     1.8088   0.9601
normal           1      4.4403     1.7884   0.9610

Learned parameters (batch, original units):
  x1            2.9971
  (bias)        3.8893

Plots written:
  plots/loss_curve.png
  plots/fit.png
  plots/loss_surface.png
  plots/predictions.png
```

Batch gradient descent lands on the same answer as the closed-form normal
equation, which is how you know the gradients are right.

## Features

- **Four solvers**: full-batch gradient descent, stochastic GD (one sample per
  step), mini-batch GD, and the closed-form **normal equation** as a reference.
- **Ridge (L2) regularisation** through `alpha`, in both GD and closed form.
- **Feature standardisation** (`StandardScaler`), plus `unscale_parameters` to
  turn weights learned on scaled data back into original units.
- **Early stopping** when the loss stops improving, and a clear error when a
  learning rate is too large and training diverges.
- **Metrics**: MSE, RMSE, MAE, R².
- **Plots**: data + fitted line, loss per epoch (all solvers on one chart),
  loss-surface contours with the GD path, and predicted vs actual.
- **CLI** for synthetic data or any numeric CSV.

## Key CS concepts

| Concept | Where |
|---|---|
| Hypothesis `ŷ = Xw + b` and MSE loss `J = (1/n)‖ŷ − y‖² + α‖w‖²` | `model.py` → `loss` |
| Analytic gradients `∂J/∂w = (2/n)Xᵀ(ŷ − y) + 2αw`, `∂J/∂b = (2/n)Σ(ŷ − y)` | `model.py` → `gradients` |
| Gradient descent update `θ ← θ − η∇J` | `model.py` → `fit` |
| Batch vs stochastic vs mini-batch: noise vs cost per step | `solver=` argument |
| Normal equation `θ = (AᵀA)⁻¹Aᵀy` (via `lstsq` for numerical stability) | `model.py` → `_fit_normal` |
| Gradient checking with central finite differences | `tests/test_model.py` |
| Conditioning: why scaling turns a long thin valley into a round bowl | `data.py` → `StandardScaler`, loss-surface plot |
| Bias/variance trade-off with L2 regularisation | `alpha=` argument |
| Vectorisation: the loss surface is computed for a whole grid at once with broadcasting | `plotting.py` → `plot_loss_surface` |

### Why feature scaling matters

On the unscaled synthetic data (x in [0, 10]) the loss surface is a narrow,
tilted valley. Gradient descent shoots across it in the first step, then crawls
slowly along the bottom. That is the `loss_surface.png` you get from
`make demo`. With `--scale` the contours turn almost circular and the same
learning rate converges in far fewer epochs. On the house-price example (square
footage in the thousands) unscaled GD with `--lr 0.1` diverges straight away,
and the CLI tells you so.

## Project layout

```
011-linear-regression-from-scratch/
├── src/linreg/
│   ├── model.py      # LinearRegression: GD solvers, normal equation, ridge
│   ├── data.py       # synthetic data, CSV loader, train/test split, scaler
│   ├── metrics.py    # mse, rmse, mae, r2_score
│   ├── plotting.py   # fit, loss curve, loss surface, predicted-vs-actual
│   └── cli.py        # `linreg` command
├── examples/house_prices.csv   # small synthetic housing dataset (3 features)
├── tests/            # 39 pytest tests
├── pyproject.toml
└── Makefile
```

## Build, run, test

Requires Python 3.10+, NumPy and Matplotlib.

```bash
make dev          # pip install -e '.[dev]'  (numpy, matplotlib, pytest)
make test         # run the test suite
make demo         # compare all solvers on synthetic data, write ./plots/*.png
make run ARGS="--data examples/house_prices.csv --target price --scale --lr 0.05 --epochs 5000"
```

After `make install` the same thing is available as the `linreg` command.

### CLI options

```
data:      --data CSV  --target COL  --samples N  --true-weights W [W ...]
           --true-bias B  --noise S  --test-size F  --seed N
training:  --solver {batch,sgd,minibatch,normal}  --lr F  --epochs N
           --batch-size N  --alpha F  --scale  --compare
output:    --plots DIR
```

### Example: multi-feature CSV

```
$ linreg --data examples/house_prices.csv --scale --lr 0.05 --epochs 5000 --compare
Data: examples/house_prices.csv
      60 samples, 3 feature(s), 48 train / 12 test

solver      epochs   train MSE  test RMSE  test R²
--------------------------------------------------
batch         1174  2.3451e+08      12019   0.9810
sgd           5000  2.7072e+08      12967   0.9779
minibatch     5000  2.3455e+08      12035   0.9809
normal           1  2.3451e+08      12019   0.9810

Learned parameters (batch, original units):
  sqft          119.0733
  bedrooms      9570.2868
  age_years    -611.1795
  (bias)        37596.0009
```

The data was generated with `price ≈ 50000 + 120·sqft + 8000·bedrooms − 900·age`
plus noise. Batch GD stopped early at epoch 1174 once the loss stopped changing.

### Library use

```python
from linreg import LinearRegression, StandardScaler, make_regression, unscale_parameters
from linreg import plotting

ds = make_regression(n_samples=200, weights=[3.0], bias=4.0, noise=2.0)
scaler = StandardScaler()
Xs = scaler.fit_transform(ds.X)

model = LinearRegression(learning_rate=0.1, epochs=1000, solver="minibatch", batch_size=32)
model.fit(Xs, ds.y)
print(model.score(Xs, ds.y))                      # R²
print(unscale_parameters(model.weights_, model.bias_, scaler.mean_, scaler.std_))

plotting.plot_loss_curve({"minibatch": model.history_.loss}, "loss.png")
```

## Tests

39 tests cover:

- recovering known parameters from synthetic data, for every solver;
- batch GD agreeing with the normal equation, with and without ridge;
- analytic gradients matching finite differences;
- the loss never increasing under batch GD, early stopping, and divergence detection;
- metrics on hand-computed values and edge cases (constant targets, negative R²);
- CSV parsing and its error messages, the train/test split, and scaler round-trips;
- the CLI end to end, including checking that the PNG files it writes are valid.

## Possible extensions

- Polynomial features to fit curves while staying linear in the parameters.
- L1 (lasso) regularisation via subgradients or coordinate descent.
- Momentum, RMSProp or Adam optimisers, compared on the loss-surface plot.
- Learning-rate schedules (step decay, 1/t) so SGD settles at the minimum.
- An animated GIF of the line and the GD path moving epoch by epoch.
- k-fold cross-validation to choose `alpha` automatically.
- Logistic regression on the same scaffolding (sigmoid + cross-entropy).
