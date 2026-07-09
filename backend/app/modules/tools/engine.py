"""Chemical engineering tool implementations + External API tools.

Design doc 5.4: 6 local calculation tools + 4 external API tools.
"""

import hashlib
import html
import json
import math
import re
import ssl
import time
import urllib.parse
import urllib.request
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
# HTTP Client for external APIs (zero deps)
# ============================================================
def _http_get(url: str, timeout: int = 15) -> dict | None:
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AgentForge/1.0"})
            with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            if attempt == 2:
                return None
            time.sleep(1)


# ============================================================
# Local Calculation Tools
# ============================================================

def calculate_molecular_weight(formula: str) -> str:
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
                        ok = False; break
                else:
                    if s % last_comp != 0:
                        ok = False; break
                    lc = -s // last_comp
                    if lc <= 0:
                        ok = False; break
                    if last_val is None:
                        last_val = lc
                    elif lc != last_val:
                        ok = False; break
            if not ok:
                continue
            final = list(coeffs) + [last_val]
            g = final[0]
            for x in final[1:]:
                g = math.gcd(g, x)
            final = [x // g for x in final]
            parts_l = []
            for i, sp in enumerate(r_species):
                c = final[i]; parts_l.append(f"{c if c > 1 else ''}{sp}")
            left = " + ".join(parts_l)
            parts_r = []
            for i, sp in enumerate(p_species):
                c = final[n_reactants + i]; parts_r.append(f"{c if c > 1 else ''}{sp}")
            right = " + ".join(parts_r)
            return f"**Balanced:**\n{left} -> {right}\nCoefficients: {final[:n_reactants]} -> {final[n_reactants:]}"
        return "WARNING: No solution found in range 1-20"
    except Exception as e:
        return f"ERROR: {e}"


_TEMP_CONV = {
    ("C", "F"): lambda v: v * 9/5 + 32, ("C", "K"): lambda v: v + 273.15,
    ("F", "C"): lambda v: (v - 32) * 5/9, ("F", "K"): lambda v: (v - 32) * 5/9 + 273.15,
    ("K", "C"): lambda v: v - 273.15, ("K", "F"): lambda v: (v - 273.15) * 9/5 + 32,
}
_PRESSURE_TO_PA = {"Pa": 1, "kPa": 1000, "MPa": 1e6, "atm": 101325, "bar": 1e5, "psi": 6894.76, "mmHg": 133.322, "torr": 133.322}
_MASS_TO_KG = {"kg": 1, "g": 0.001, "mg": 1e-6, "t": 1000, "ton": 1000, "lb": 0.453592, "oz": 0.0283495}
_VOLUME_TO_L = {"L": 1, "mL": 0.001, "m3": 1000, "cm3": 0.001, "gal": 3.78541, "qt": 0.946353, "pt": 0.473176, "fl_oz": 0.0295735}
_ENERGY_TO_J = {"J": 1, "kJ": 1000, "cal": 4.184, "kcal": 4184, "kWh": 3.6e6, "BTU": 1055.06}


def convert_unit(value: float, from_unit: str, to_unit: str) -> str:
    fu, tu = from_unit.strip(), to_unit.strip()
    try:
        if (fu, tu) in _TEMP_CONV:
            result = _TEMP_CONV[(fu, tu)](value)
            return f"**{value} {fu} = {result:.4f} {tu}**"
        for table in [_PRESSURE_TO_PA, _MASS_TO_KG, _VOLUME_TO_L, _ENERGY_TO_J]:
            f, t = table.get(fu), table.get(tu)
            if f is not None and t is not None:
                result = value * f / t
                return f"**{value} {fu} = {result:.6g} {tu}**"
        return f"ERROR: Unsupported conversion: {fu} -> {tu}"
    except Exception as e:
        return f"ERROR: {e}"


def calculate_ideal_gas(P: float, V: float, n: float, T: float) -> str:
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
    dT = t_out - t_in
    Q = mass_flow * cp * dT
    direction = "Heating" if dT > 0 else "Cooling"
    return (
        f"**Heat Exchanger Duty:**\n"
        f"Q = m * Cp * deltaT = {mass_flow} x {cp} x ({t_out} - {t_in})\n"
        f"deltaT = {dT:.2f} K\n"
        f"**Q = {Q:.2f} W ({Q/1000:.3f} kW)** ({direction})"
    )


def reynolds_number(density: float, velocity: float, diameter: float, viscosity: float) -> str:
    Re = density * velocity * diameter / viscosity
    if Re < 2300:
        regime = "Laminar"
    elif Re < 4000:
        regime = "Transitional"
    else:
        regime = "Turbulent"
    return (
        f"**Reynolds Number:**\n"
        f"Re = rho * v * D / mu = {density} x {velocity} x {diameter} / {viscosity}\n"
        f"**Re = {Re:.2f}**\nFlow regime: **{regime}**"
    )


# ============================================================
# External API Tools (Design doc 5.4)
# ============================================================

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PUBCHEM_PROPS = ["MolecularFormula", "MolecularWeight", "IUPACName", "XLogP"]


def _pubchem_cid(name: str) -> int | None:
    url = f"{PUBCHEM_BASE}/compound/name/{urllib.parse.quote(name)}/cids/JSON"
    data = _http_get(url)
    if data and "IdentifierList" in data:
        cids = data["IdentifierList"].get("CID", [])
        return cids[0] if cids else None
    return None


def pubchem_search(query: str) -> str:
    """从 PubChem (NIH) 实时查询化合物的分子式、分子量、IUPAC名。"""
    cid = _pubchem_cid(query)
    if cid is None:
        return f"[PubChem] Compound not found: {query}"

    props_str = ",".join(PUBCHEM_PROPS)
    url = f"{PUBCHEM_BASE}/compound/cid/{cid}/property/{props_str}/JSON"
    data = _http_get(url)
    if not data or "PropertyTable" not in data:
        return f"[PubChem] Query failed (CID: {cid})"

    props = data["PropertyTable"]["Properties"][0]

    syn_url = f"{PUBCHEM_BASE}/compound/cid/{cid}/synonyms/JSON"
    syn_data = _http_get(syn_url)
    synonyms = []
    if syn_data and "InformationList" in syn_data:
        synonyms = syn_data["InformationList"]["Information"][0].get("Synonym", [])[:3]

    lines = [f"## PubChem: {props.get('IUPACName', query)}"]
    lines.append(f"CID: {cid}")
    for label, key in [("Formula", "MolecularFormula"), ("Molecular Weight", "MolecularWeight"), ("XLogP", "XLogP")]:
        val = props.get(key)
        if val: lines.append(f"- {label}: {val}")
    if synonyms:
        lines.append(f"- Synonyms: {', '.join(synonyms)}")
    lines.append("Source: PubChem (NIH/NLM)")
    return "\n".join(lines)


def pubchem_toxicity(compound_name: str) -> str:
    """查询化合物的 GHS 危险分类和毒性数据。"""
    cid = _pubchem_cid(compound_name)
    if cid is None:
        return f"[PubChem] Compound not found: {compound_name}"

    url = f"{PUBCHEM_BASE}/compound/cid/{cid}/classification/JSON?classification_type=simple"
    data = _http_get(url)
    if not data:
        return f"[PubChem] Could not fetch GHS data for {compound_name}"

    classes = data.get("GHSClassification", [])
    if not classes:
        return f"[PubChem] No GHS classification available for {compound_name}"

    lines = [f"## {compound_name} -- GHS Hazard Classification"]
    for cls in classes:
        code = cls.get("GHSClassificationCode", "")
        name = cls.get("GHSClassificationName", "")
        lines.append(f"- {code}: {name}")
    lines.append("Source: PubChem GHS Classification")
    return "\n".join(lines)


NIST_BASE = "https://webbook.nist.gov/cgi/cbook.cgi"


def nist_thermo(formula: str) -> str:
    """从 NIST Chemistry WebBook 查询化合物的热力学数据。"""
    url = f"{NIST_BASE}?Formula={urllib.parse.quote(formula)}&cTG=on&cTC=on&cTP=on&cTR=on&cTS=on&cTT=on"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgentForge"})
        with urllib.request.urlopen(req, timeout=15, context=ssl.create_default_context()) as resp:
            html_text = resp.read().decode()
    except Exception:
        return f"[NIST] Query timed out: {formula}"

    name_match = re.search(r'<title>(.*?)</title>', html_text)
    name = html.unescape(name_match.group(1)) if name_match else formula

    has_gas = "Gas phase thermochemistry data" in html_text
    has_condensed = "Condensed phase thermochemistry data" in html_text
    has_ir = "IR Spectrum" in html_text

    lines = [f"## NIST WebBook: {name}"]
    available = []
    if has_gas: available.append("Gas phase thermochemistry")
    if has_condensed: available.append("Condensed phase thermochemistry")
    if has_ir: available.append("IR Spectrum")
    if available:
        lines.append("Available data: " + ", ".join(available))
    else:
        lines.append("No thermodynamic data found for this compound")
    lines.append(f"Details: {url}")
    lines.append("Source: NIST Chemistry WebBook")
    return "\n".join(lines)


ARXIV_BASE = "http://export.arxiv.org/api/query"


def arxiv_search(query: str, max_results: int = 3) -> str:
    """从 ArXiv 检索最新的学术论文。"""
    url = (
        f"{ARXIV_BASE}?search_query=all:{urllib.parse.quote(query)}"
        f"&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgentForge"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml = resp.read().decode()
    except Exception:
        return f"[ArXiv] Query timed out: {query}"

    entries = re.findall(r'<entry>(.*?)</entry>', xml, re.DOTALL)
    if not entries:
        return f"[ArXiv] No papers found for: {query}"

    lines = [f"## ArXiv: Latest papers on '{query}'"]
    for entry in entries[:max_results]:
        title = re.search(r'<title>(.*?)</title>', entry)
        published = re.search(r'<published>(\d{4}-\d{2}-\d{2})', entry)
        arxiv_id = re.search(r'<id>.*?/([^/]+)</id>', entry)
        if title:
            t = html.unescape(title.group(1).strip().replace('\n', ' '))
            pub = published.group(1) if published else "?"
            aid = arxiv_id.group(1) if arxiv_id else "?"
            lines.append(f"- [{pub}] {t} (arXiv:{aid})")
    lines.append("Source: ArXiv")
    return "\n".join(lines)


# ============================================================
# Tool Registry
# ============================================================

TOOL_FUNCTIONS: dict[str, Any] = {
    # Local calculation
    "calculate_molecular_weight": calculate_molecular_weight,
    "balance_equation": balance_equation,
    "convert_unit": convert_unit,
    "calculate_ideal_gas": calculate_ideal_gas,
    "heat_exchanger_duty": heat_exchanger_duty,
    "reynolds_number": reynolds_number,
    # External APIs
    "pubchem_search": pubchem_search,
    "pubchem_toxicity": pubchem_toxicity,
    "nist_thermo": nist_thermo,
    "arxiv_search": arxiv_search,
}

TOOL_DEFINITIONS = [
    {
        "name": "calculate_molecular_weight",
        "description": "Calculate molecular weight / molar mass (g/mol). Supports parentheses, e.g. Ca(OH)2.",
        "tool_type": "local",
        "input_schema": {
            "type": "object",
            "properties": {"formula": {"type": "string", "description": "Chemical formula, e.g. H2SO4, NaOH"}},
            "required": ["formula"],
        },
    },
    {
        "name": "balance_equation",
        "description": "Balance a chemical equation, return coefficients.",
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
        "description": "Convert engineering units: temperature (C/F/K), pressure, mass, volume, energy.",
        "tool_type": "local",
        "input_schema": {
            "type": "object",
            "properties": {
                "value": {"type": "number"},
                "from_unit": {"type": "string"},
                "to_unit": {"type": "string"},
            },
            "required": ["value", "from_unit", "to_unit"],
        },
    },
    {
        "name": "calculate_ideal_gas",
        "description": "Ideal gas law PV=nRT. Pass 0 for the unknown value.",
        "tool_type": "local",
        "input_schema": {
            "type": "object",
            "properties": {
                "P": {"type": "number"}, "V": {"type": "number"},
                "n": {"type": "number"}, "T": {"type": "number"},
            },
            "required": ["P", "V", "n", "T"],
        },
    },
    {
        "name": "heat_exchanger_duty",
        "description": "Calculate heat exchanger duty Q = m * Cp * deltaT.",
        "tool_type": "local",
        "input_schema": {
            "type": "object",
            "properties": {
                "mass_flow": {"type": "number"}, "cp": {"type": "number"},
                "t_in": {"type": "number"}, "t_out": {"type": "number"},
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
                "density": {"type": "number"}, "velocity": {"type": "number"},
                "diameter": {"type": "number"}, "viscosity": {"type": "number"},
            },
            "required": ["density", "velocity", "diameter", "viscosity"],
        },
    },
    {
        "name": "pubchem_search",
        "description": "Real-time PubChem (NIH) compound lookup: molecular formula, weight, IUPAC name.",
        "tool_type": "external_api",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Compound name (Chinese or English)"}},
            "required": ["query"],
        },
    },
    {
        "name": "pubchem_toxicity",
        "description": "Query GHS hazard classification and toxicity data from PubChem.",
        "tool_type": "external_api",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Compound name"}},
            "required": ["query"],
        },
    },
    {
        "name": "nist_thermo",
        "description": "Search NIST Chemistry WebBook for thermodynamic data (enthalpy, entropy, heat capacity).",
        "tool_type": "external_api",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Chemical formula, e.g. H2SO4"}},
            "required": ["query"],
        },
    },
    {
        "name": "arxiv_search",
        "description": "Retrieve latest academic papers from ArXiv.",
        "tool_type": "external_api",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search keywords"}},
            "required": ["query"],
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return f"ERROR: Unknown tool: {name}"
    try:
        # Map 'query' arg to function's expected parameter name for external APIs
        if "query" in args and name in ("pubchem_search", "pubchem_toxicity", "nist_thermo", "arxiv_search"):
            return str(fn(args["query"]))
        return str(fn(**args))
    except Exception as e:
        return f"ERROR: Tool execution failed ({name}): {e}"
