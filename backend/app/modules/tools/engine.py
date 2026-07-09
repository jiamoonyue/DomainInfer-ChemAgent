"""Chemical engineering tool implementations — ported from DomainInfer ChemAgent."""

import json
import math
import re
from typing import Any

# ============================================================
# Periodic Table / Atomic Weights
# ============================================================
ATOMIC_WEIGHTS = {
    "H": 1.008, "He": 4.0026, "Li": 6.94, "Be": 9.0122, "B": 10.81,
    "C": 12.011, "N": 14.007, "O": 15.999, "F": 18.998, "Ne": 20.180,
    "Na": 22.990, "Mg": 24.305, "Al": 26.982, "Si": 28.085, "P": 30.974,
    "S": 32.06, "Cl": 35.45, "Ar": 39.948, "K": 39.098, "Ca": 40.078,
    "Sc": 44.956, "Ti": 47.867, "V": 50.942, "Cr": 51.996, "Mn": 54.938,
    "Fe": 55.845, "Co": 58.933, "Ni": 58.693, "Cu": 63.546, "Zn": 65.38,
    "Ga": 69.723, "Ge": 72.630, "As": 74.922, "Se": 78.971, "Br": 79.904,
    "Kr": 83.798, "Rb": 85.468, "Sr": 87.62, "Y": 88.906, "Zr": 91.224,
    "Nb": 92.906, "Mo": 95.95, "Tc": 98.0, "Ru": 101.07, "Rh": 102.91,
    "Pd": 106.42, "Ag": 107.87, "Cd": 112.41, "In": 114.82, "Sn": 118.71,
    "Sb": 121.76, "Te": 127.60, "I": 126.90, "Xe": 131.29, "Cs": 132.91,
    "Ba": 137.33, "La": 138.91, "Ce": 140.12, "Pr": 140.91, "Nd": 144.24,
    "Pm": 145.0, "Sm": 150.36, "Eu": 151.96, "Gd": 157.25, "Tb": 158.93,
    "Dy": 162.50, "Ho": 164.93, "Er": 167.26, "Tm": 168.93, "Yb": 173.05,
    "Lu": 174.97, "Hf": 178.49, "Ta": 180.95, "W": 183.84, "Re": 186.21,
    "Os": 190.23, "Ir": 192.22, "Pt": 195.08, "Au": 196.97, "Hg": 200.59,
    "Tl": 204.38, "Pb": 207.2, "Bi": 208.98, "Po": 209.0, "At": 210.0,
    "Rn": 222.0, "Fr": 223.0, "Ra": 226.0, "Ac": 227.0, "Th": 232.04,
    "Pa": 231.04, "U": 238.03, "Np": 237.0, "Pu": 244.0, "Am": 243.0,
}

POLYATOMIC_MASSES = {
    "OH": 17.007, "NO3": 62.005, "SO4": 96.06, "CO3": 60.009,
    "PO4": 94.971, "NH4": 18.039, "MnO4": 118.936, "CrO4": 115.994,
    "Cr2O7": 215.988, "CN": 26.017, "CH3COO": 59.044, "HCO3": 61.017,
}


def _parse_formula(formula: str) -> list[tuple[str, int]]:
    """Parse a chemical formula into list of (element, count)."""
    while "(" in formula:
        formula = re.sub(
            r"\(([^()]+)\)(\d*)",
            lambda m: "".join(
                e + str((int(c) if c else 1) * (int(m.group(2)) if m.group(2) else 1))
                for e, c in re.findall(r"([A-Z][a-z]?)(\d*)", m.group(1))
            ),
            formula,
        )
    parts = re.findall(r"([A-Z][a-z]?)(\d*)", formula)
    return [(elem, int(count) if count else 1) for elem, count in parts]


# ============================================================
# Tool Implementations
# ============================================================

def calculate_molecular_weight(formula: str) -> str:
    """Calculate molecular weight of a chemical formula."""
    try:
        parts = _parse_formula(formula)
        total = 0.0
        details = []
        for elem, count in parts:
            if elem in ATOMIC_WEIGHTS:
                w = ATOMIC_WEIGHTS[elem]
                total += w * count
                details.append(f"{elem}: {w} x {count} = {w*count:.3f}")
            elif elem in POLYATOMIC_MASSES:
                w = POLYATOMIC_MASSES[elem]
                total += w * count
                details.append(f"{elem}(ion): {w} x {count} = {w*count:.3f}")
            else:
                return f"ERROR: Unknown element/ion: {elem}"
        lines = [f"**{formula}** molecular weight:"]
        lines.extend(details)
        lines.append(f"**Total: {total:.3f} g/mol**")
        return "\n".join(lines)
    except Exception as e:
        return f"ERROR: {e}"


def balance_equation(reactants: str, products: str) -> str:
    """Balance a chemical equation."""
    try:
        r_species = [s.strip() for s in reactants.split("+")]
        p_species = [s.strip() for s in products.split("+")]
        all_species = r_species + p_species
        all_elements = set()
        compositions = []
        for sp in all_species:
            parts = _parse_formula(sp)
            comp = {}
            for elem, cnt in parts:
                comp[elem] = comp.get(elem, 0) + cnt
                all_elements.add(elem)
            compositions.append(comp)

        elements = sorted(all_elements)
        n_reactants = len(r_species)
        n_vars = len(all_species)

        from itertools import product
        for coeffs in product(range(1, 21), repeat=n_vars - 1):
            # Build matrix row check
            ok = True
            last_val = None
            for elem in elements:
                s = 0
                for i, comp in enumerate(compositions[:-1]):
                    c = comp.get(elem, 0)
                    if i < n_reactants:
                        s += c * coeffs[i]
                    else:
                        s -= c * coeffs[i]
                last_comp = compositions[-1].get(elem, 0)
                if last_comp == 0:
                    if s != 0:
                        ok = False
                        break
                else:
                    if s % last_comp != 0:
                        ok = False
                        break
                    lc = -s // last_comp
                    if lc <= 0:
                        ok = False
                        break
                    if last_val is None:
                        last_val = lc
                    elif lc != last_val:
                        ok = False
                        break
            if not ok:
                continue

            final = list(coeffs) + [last_val]
            g = final[0]
            for x in final[1:]:
                g = math.gcd(g, x)
            final = [x // g for x in final]

            parts_l = []
            for i, sp in enumerate(r_species):
                c = final[i]
                parts_l.append(f"{c if c > 1 else ''}{sp}")
            left = " + ".join(parts_l)
            parts_r = []
            for i, sp in enumerate(p_species):
                c = final[n_reactants + i]
                parts_r.append(f"{c if c > 1 else ''}{sp}")
            right = " + ".join(parts_r)
            return f"**Balanced:**\n{left} -> {right}\nCoefficients: {final[:n_reactants]} -> {final[n_reactants:]}"

        return "WARNING: No solution found in range 1-20"
    except Exception as e:
        return f"ERROR: {e}"


# Unit conversion tables
_TEMP_CONV = {
    ("C", "F"): lambda v: v * 9/5 + 32,
    ("C", "K"): lambda v: v + 273.15,
    ("F", "C"): lambda v: (v - 32) * 5/9,
    ("F", "K"): lambda v: (v - 32) * 5/9 + 273.15,
    ("K", "C"): lambda v: v - 273.15,
    ("K", "F"): lambda v: (v - 273.15) * 9/5 + 32,
}

_PRESSURE_TO_PA = {
    "Pa": 1, "kPa": 1000, "MPa": 1e6, "atm": 101325,
    "bar": 1e5, "psi": 6894.76, "mmHg": 133.322, "torr": 133.322,
}

_MASS_TO_KG = {"kg": 1, "g": 0.001, "mg": 1e-6, "t": 1000, "ton": 1000, "lb": 0.453592, "oz": 0.0283495}
_VOLUME_TO_L = {"L": 1, "mL": 0.001, "m3": 1000, "cm3": 0.001, "gal": 3.78541, "qt": 0.946353, "pt": 0.473176, "fl_oz": 0.0295735}
_ENERGY_TO_J = {"J": 1, "kJ": 1000, "cal": 4.184, "kcal": 4184, "kWh": 3.6e6, "BTU": 1055.06}


def convert_unit(value: float, from_unit: str, to_unit: str) -> str:
    """Convert between engineering units."""
    fu, tu = from_unit.strip(), to_unit.strip()
    try:
        if (fu, tu) in _TEMP_CONV:
            result = _TEMP_CONV[(fu, tu)](value)
            return f"**{value} {fu} = {result:.4f} {tu}**"
        for table in [_PRESSURE_TO_PA, _MASS_TO_KG, _VOLUME_TO_L, _ENERGY_TO_J]:
            f = table.get(fu); t = table.get(tu)
            if f is not None and t is not None:
                result = value * f / t
                return f"**{value} {fu} = {result:.6g} {tu}**"
        return f"ERROR: Unsupported conversion: {fu} -> {tu}"
    except Exception as e:
        return f"ERROR: {e}"


def calculate_ideal_gas(P: float, V: float, n: float, T: float) -> str:
    """PV=nRT calculation. Pass 0 for the unknown parameter."""
    R = 8.314
    unknowns = sum(1 for x in [P, V, n, T] if x <= 0)
    if unknowns != 1:
        return "ERROR: Exactly one unknown parameter required (value=0)"

    if P <= 0:
        P = n * R * T / V
        return f"**P = nRT/V = {P:.4f} Pa ({P/101325:.4f} atm)**"
    elif V <= 0:
        V = n * R * T / P
        return f"**V = nRT/P = {V:.6f} m3 ({V*1000:.4f} L)**"
    elif n <= 0:
        n = P * V / (R * T)
        return f"**n = PV/RT = {n:.6f} mol**"
    else:
        T = P * V / (n * R)
        return f"**T = PV/nR = {T:.4f} K ({T-273.15:.2f} C)**"


def heat_exchanger_duty(mass_flow: float, cp: float, t_in: float, t_out: float) -> str:
    """Q = m*Cp*deltaT."""
    dT = t_out - t_in
    Q = mass_flow * cp * dT
    direction = "Heating" if dT > 0 else "Cooling"
    return (
        f"**Heat Exchanger Duty:**\n"
        f"Q = m.Cp.deltaT = {mass_flow} x {cp} x ({t_out} - {t_in})\n"
        f"deltaT = {dT:.2f} K\n"
        f"**Q = {Q:.2f} W ({Q/1000:.3f} kW)**\n"
        f"({direction})"
    )


def reynolds_number(density: float, velocity: float, diameter: float, viscosity: float) -> str:
    """Re = rho*v*D/mu."""
    Re = density * velocity * diameter / viscosity
    if Re < 2300:
        regime = "Laminar"
    elif Re < 4000:
        regime = "Transitional"
    else:
        regime = "Turbulent"
    return (
        f"**Reynolds Number:**\n"
        f"Re = rho.v.D/mu = {density} x {velocity} x {diameter} / {viscosity}\n"
        f"**Re = {Re:.2f}**\n"
        f"Flow regime: **{regime}**"
    )


# Tool dispatch registry
TOOL_FUNCTIONS: dict[str, Any] = {
    "calculate_molecular_weight": calculate_molecular_weight,
    "balance_equation": balance_equation,
    "convert_unit": convert_unit,
    "calculate_ideal_gas": calculate_ideal_gas,
    "heat_exchanger_duty": heat_exchanger_duty,
    "reynolds_number": reynolds_number,
}

# Tool definitions (JSON Schema — used for LLM prompt and API docs)
TOOL_DEFINITIONS = [
    {
        "name": "calculate_molecular_weight",
        "description": "Calculate molecular weight / molar mass (g/mol) of a chemical formula. Supports parentheses e.g. Ca(OH)2, Al2(SO4)3.",
        "tool_type": "local",
        "input_schema": {
            "type": "object",
            "properties": {"formula": {"type": "string", "description": "Chemical formula, e.g. H2SO4, NaOH, Ca(OH)2"}},
            "required": ["formula"],
        },
    },
    {
        "name": "balance_equation",
        "description": "Balance a chemical equation and return coefficients.",
        "tool_type": "local",
        "input_schema": {
            "type": "object",
            "properties": {
                "reactants": {"type": "string", "description": "Reactants joined by +, e.g. H2+O2"},
                "products": {"type": "string", "description": "Products joined by +, e.g. H2O"},
            },
            "required": ["reactants", "products"],
        },
    },
    {
        "name": "convert_unit",
        "description": "Convert engineering units. Temperature (C/F/K), Pressure (Pa/kPa/MPa/atm/bar/psi/mmHg), Mass, Volume, Energy.",
        "tool_type": "local",
        "input_schema": {
            "type": "object",
            "properties": {
                "value": {"type": "number", "description": "Value to convert"},
                "from_unit": {"type": "string", "description": "Source unit"},
                "to_unit": {"type": "string", "description": "Target unit"},
            },
            "required": ["value", "from_unit", "to_unit"],
        },
    },
    {
        "name": "calculate_ideal_gas",
        "description": "Ideal gas law (PV=nRT). Provide 3 known values, set unknown to 0.",
        "tool_type": "local",
        "input_schema": {
            "type": "object",
            "properties": {
                "P": {"type": "number", "description": "Pressure (Pa), 0 if unknown"},
                "V": {"type": "number", "description": "Volume (m3), 0 if unknown"},
                "n": {"type": "number", "description": "Moles (mol), 0 if unknown"},
                "T": {"type": "number", "description": "Temperature (K), 0 if unknown"},
            },
            "required": ["P", "V", "n", "T"],
        },
    },
    {
        "name": "heat_exchanger_duty",
        "description": "Calculate heat exchanger duty Q = m*Cp*deltaT.",
        "tool_type": "local",
        "input_schema": {
            "type": "object",
            "properties": {
                "mass_flow": {"type": "number", "description": "Mass flow (kg/s)"},
                "cp": {"type": "number", "description": "Specific heat capacity (J/(kg*K))"},
                "t_in": {"type": "number", "description": "Inlet temperature (K or C)"},
                "t_out": {"type": "number", "description": "Outlet temperature (K or C)"},
            },
            "required": ["mass_flow", "cp", "t_in", "t_out"],
        },
    },
    {
        "name": "reynolds_number",
        "description": "Calculate Reynolds number Re = rho*v*D/mu. Determines laminar/turbulent flow.",
        "tool_type": "local",
        "input_schema": {
            "type": "object",
            "properties": {
                "density": {"type": "number", "description": "Fluid density (kg/m3)"},
                "velocity": {"type": "number", "description": "Flow velocity (m/s)"},
                "diameter": {"type": "number", "description": "Pipe diameter (m)"},
                "viscosity": {"type": "number", "description": "Dynamic viscosity (Pa*s)"},
            },
            "required": ["density", "velocity", "diameter", "viscosity"],
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name. Returns result string."""
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return f"ERROR: Unknown tool: {name}"
    try:
        return fn(**args)
    except TypeError as e:
        return f"ERROR: Invalid arguments for {name}: {e}"
    except Exception as e:
        return f"ERROR: Tool execution failed ({name}): {e}"
