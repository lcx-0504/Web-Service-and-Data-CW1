def pytest_addoption(parser):
    parser.addoption(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the NutriTrack API (default: http://127.0.0.1:8000)",
    )
