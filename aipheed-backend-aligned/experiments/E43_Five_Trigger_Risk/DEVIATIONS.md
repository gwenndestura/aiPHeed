# E43 deviations

## D-1 (after the primary run, before the repeat finished; no result changed)

`runner/e43_lib.py::simulate` gained an optional argument, `components=False`. When it is `True`, the function also returns the hunger-only and price-only path probabilities, which the backend record uses to explain the served SIM-0 forecast.

The default output is unchanged. The random-number calls are identical, and `tests/test_e43.py::test_component_output_does_not_change_the_forecast` checks this.

The byte-identical repeat (`runs/20261015T*` second folder) was started before the edit, so it ran the pre-edit code.
