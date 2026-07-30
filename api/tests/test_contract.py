import json
from pathlib import Path

from src.main import app


def test_project_routes_match_api_contract() -> None:
    contract_path = Path(__file__).parents[1] / "api-contract.json"
    contract = json.loads(contract_path.read_text())
    generated = app.openapi()

    expected_paths = {path for path in contract["paths"] if path.startswith("/api/v1/projects")}
    generated_paths = {path for path in generated["paths"] if path.startswith("/api/v1/projects")}
    assert generated_paths == expected_paths

    for path in expected_paths:
        expected_methods = set(contract["paths"][path]) - {"parameters"}
        generated_methods = set(generated["paths"][path]) - {"parameters"}
        assert generated_methods == expected_methods


def test_account_routes_match_api_contract() -> None:
    contract_path = Path(__file__).parents[1] / "api-contract.json"
    contract = json.loads(contract_path.read_text())
    generated = app.openapi()
    prefixes = ("/api/v1/auth", "/api/v1/companies", "/api/v1/me")

    expected_paths = {path for path in contract["paths"] if path.startswith(prefixes)}
    generated_paths = {path for path in generated["paths"] if path.startswith(prefixes)}
    assert generated_paths == expected_paths

    for path in expected_paths:
        expected_methods = set(contract["paths"][path]) - {"parameters"}
        generated_methods = set(generated["paths"][path]) - {"parameters"}
        assert generated_methods == expected_methods
