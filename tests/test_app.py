from streamlit.testing.v1 import AppTest


def test_app_loads_all_tabs_without_exception():
    at = AppTest.from_file("src/app.py", default_timeout=120)
    at.run()
    assert not at.exception
    assert len(at.tabs) == 7


def test_app_sidebar_controls_present():
    at = AppTest.from_file("src/app.py", default_timeout=120)
    at.run()
    button_labels = {b.label for b in at.sidebar.button}
    assert "Reset Filters" in button_labels
    assert "Run Simulation Step" in button_labels


def test_trust_horizon_metric_renders_in_calibration_tab():
    at = AppTest.from_file("src/app.py", default_timeout=120)
    at.run()
    assert not at.exception
    metric_labels = {m.label for m in at.metric}
    assert "Recommended Autonomous Billing Cutoff" in metric_labels
