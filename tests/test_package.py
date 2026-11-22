from weather_api.models import placeholder_model_name


def test_package_imports() -> None:
    assert placeholder_model_name() == "weather"
