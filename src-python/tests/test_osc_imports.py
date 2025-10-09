def test_import_osc_module():
    try:
        import importlib
        importlib.import_module('models.osc.osc')
    except Exception as e:
        raise AssertionError(f"Failed importing models.osc.osc: {e}")
