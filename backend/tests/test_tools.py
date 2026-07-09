"""Tests for tool execution — non-DB, pure Python."""

import pytest
from app.modules.tools.engine import execute_tool, _parse_formula


class TestFormulaParser:
    def test_simple_formula(self):
        parts = _parse_formula("H2O")
        assert ("H", 2) in parts
        assert ("O", 1) in parts

    def test_parentheses(self):
        parts = _parse_formula("Ca(OH)2")
        assert ("Ca", 1) in parts
        assert ("O", 2) in parts
        assert ("H", 2) in parts

    def test_complex_formula(self):
        parts = _parse_formula("Al2(SO4)3")
        assert ("Al", 2) in parts
        assert ("S", 3) in parts
        assert ("O", 12) in parts


class TestMolecularWeight:
    def test_h2so4(self):
        result = execute_tool("calculate_molecular_weight", {"formula": "H2SO4"})
        assert "98" in result
        assert "g/mol" in result

    def test_calcium_hydroxide(self):
        result = execute_tool("calculate_molecular_weight", {"formula": "Ca(OH)2"})
        assert "74" in result

    def test_nacl(self):
        result = execute_tool("calculate_molecular_weight", {"formula": "NaCl"})
        assert "58" in result

    def test_unknown_element(self):
        result = execute_tool("calculate_molecular_weight", {"formula": "Xyz2"})
        assert "Unknown" in result


class TestUnitConversion:
    def test_celsius_to_fahrenheit(self):
        result = execute_tool("convert_unit", {"value": 100, "from_unit": "C", "to_unit": "F"})
        assert "212" in result

    def test_celsius_to_kelvin(self):
        result = execute_tool("convert_unit", {"value": 0, "from_unit": "C", "to_unit": "K"})
        assert "273.15" in result

    def test_pressure_conversion(self):
        result = execute_tool("convert_unit", {"value": 1, "from_unit": "atm", "to_unit": "kPa"})
        assert "101" in result


class TestIdealGas:
    def test_volume_unknown(self):
        result = execute_tool("calculate_ideal_gas", {"P": 101325, "V": 0, "n": 1, "T": 273})
        assert "m3" in result or "m³" in result

    def test_two_unknowns(self):
        result = execute_tool("calculate_ideal_gas", {"P": 0, "V": 0, "n": 1, "T": 273})
        assert "Exactly one" in result


class TestReynoldsNumber:
    def test_turbulent(self):
        result = execute_tool("reynolds_number", {
            "density": 1000, "velocity": 2, "diameter": 0.05, "viscosity": 0.001
        })
        assert "100000" in result
        assert "Turbulent" in result

    def test_laminar(self):
        result = execute_tool("reynolds_number", {
            "density": 1000, "velocity": 0.001, "diameter": 0.01, "viscosity": 0.01
        })
        assert "Laminar" in result
