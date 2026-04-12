"""
Tests for the cryogenic thermal budget calculator.

Validates individual heat load calculations against hand calculations
and published reference values. Ensures the calculator produces
physically reasonable results consistent with docs/thermal-budget.md.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

# Add scripts/ to path so we can import thermal_budget
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from thermal_budget import (
    HeatLoad,
    ThermalBudget,
    compute_budget,
    conduction_heat_load,
    load_inputs,
    radiation_heat_load,
    thermal_conductivity_integral,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUTS = REPO_ROOT / "data" / "thermal_inputs.yaml"


@pytest.fixture
def inputs():
    """Load the default thermal inputs."""
    return load_inputs(DEFAULT_INPUTS)


@pytest.fixture
def budget(inputs):
    """Compute the full budget from default inputs."""
    return compute_budget(inputs)


@pytest.fixture
def materials(inputs):
    """Return the materials dict from inputs."""
    return inputs["materials"]


# ---------------------------------------------------------------------------
# Thermal conductivity integral tests
# ---------------------------------------------------------------------------

class TestThermalConductivityIntegral:
    """Test the thermal conductivity integral interpolation."""

    def test_ss304_integral_4k_to_300k(self, materials):
        """
        SS304: integral from 4K to 300K should be ~3000 W/m.

        Literature reference: NIST Cryogenic Materials DB gives
        ~1.6 W*cm/cm^2 for the 'conductance integral' which in SI is:
        1.6 W*cm/cm^2 = 1.6 * 0.01 / 0.0001 = 160 W/m ... wait, let's
        be careful with units.

        Actually the literature states the thermal conductivity integral
        (integral of k dT) from 4K to 300K for SS304 is approximately
        3000 W/m. This is what we use.

        More precisely, the 'conductivity integral' I = integral(k(T) dT)
        has units of W*K/m * K = W/m when evaluated between two temperatures.
        For SS304, k averages roughly 10 W/(m*K) over 4-300K, giving
        I ~ 10 * 296 = 2960 W/m, consistent with our value.
        """
        integral = thermal_conductivity_integral(
            materials["ss304"], t_cold_k=4.0, t_hot_k=300.0,
        )
        # Should be ~3000 W/m (tabulated value is 3000 - 0.5 = 2999.5)
        assert 2500 < integral < 3500, f"SS304 integral 4->300K = {integral} W/m, expected ~3000"

    def test_ss304_integral_4k_to_45k(self, materials):
        """SS304 integral from 4K to 45K: much smaller than 4K->300K."""
        integral = thermal_conductivity_integral(
            materials["ss304"], t_cold_k=4.0, t_hot_k=45.0,
        )
        # Tabulated: 185 - 0.5 = 184.5 W/m
        assert 100 < integral < 300, f"SS304 integral 4->45K = {integral} W/m, expected ~185"

    def test_phosphor_bronze_integral_4k_to_300k(self, materials):
        """PhBr integral from 4K to 300K should be ~6200 W/m."""
        integral = thermal_conductivity_integral(
            materials["phosphor_bronze"], t_cold_k=4.0, t_hot_k=300.0,
        )
        assert 5000 < integral < 8000, f"PhBr integral 4->300K = {integral} W/m"

    def test_integral_symmetry(self, materials):
        """Integral from A->B should equal -(B->A) in magnitude."""
        i_forward = thermal_conductivity_integral(
            materials["ss304"], t_cold_k=45.0, t_hot_k=300.0,
        )
        i_reverse = thermal_conductivity_integral(
            materials["ss304"], t_cold_k=300.0, t_hot_k=45.0,
        )
        assert abs(i_forward + i_reverse) < 1e-6, "Integral should be antisymmetric"

    def test_integral_additivity(self, materials):
        """Integral 4->300 should equal integral 4->45 + integral 45->300."""
        i_full = thermal_conductivity_integral(
            materials["ss304"], t_cold_k=4.0, t_hot_k=300.0,
        )
        i_low = thermal_conductivity_integral(
            materials["ss304"], t_cold_k=4.0, t_hot_k=45.0,
        )
        i_high = thermal_conductivity_integral(
            materials["ss304"], t_cold_k=45.0, t_hot_k=300.0,
        )
        assert abs(i_full - (i_low + i_high)) < 1e-6, (
            f"Additivity failed: {i_full} != {i_low} + {i_high}"
        )


# ---------------------------------------------------------------------------
# Conduction heat load tests
# ---------------------------------------------------------------------------

class TestConductionHeatLoad:
    """Test conduction heat load calculations against hand calculations."""

    def test_single_ss304_coax_45k_to_4k(self, materials):
        """
        Hand calculation: 1 SS304 coax, 40K->4K segment.
        A = 1.7e-6 m^2, L = 0.3 m
        integral(k, 4K, 45K) ~ 184.5 W/m
        Q = (1.7e-6 / 0.3) * 184.5 = 5.67e-6 * 184.5 ~ 1.05e-3 W = 1.05 mW

        docs/thermal-budget.md says 4 coax = ~2.0 mW at 4K, so 1 coax ~ 0.5 mW.
        The doc uses k_avg ~ 2.5 W/(m*K) for 40K->4K which gives:
          Q = A/L * k_avg * dT = 1.7e-6/0.3 * 2.5 * 36 = 0.51 mW
        Our integral-based calc gives a somewhat different value because
        the integral method is more accurate than a single average k.
        Accept if within factor of 3 of the doc's 0.5 mW estimate.
        """
        q = conduction_heat_load(
            materials["ss304"],
            cross_section_m2=1.7e-6,
            length_m=0.3,
            t_cold_k=4.2,
            t_hot_k=45.0,
        )
        # Should be ~1 mW based on integral; doc estimate ~0.5 mW (avg k method)
        assert 0.1e-3 < q < 3.0e-3, f"Single coax 45->4K: {q*1e3:.3f} mW, expected ~0.5-1 mW"

    def test_single_phbr_wire_300k_to_45k(self, materials):
        """
        Hand calculation: 1 PhBr 36AWG wire, 300K->45K segment.
        A = 1.27e-8 m^2, L = 0.5 m
        integral(k, 45K, 300K) ~ 6200 - 470 = 5730 W/m
        Q = (1.27e-8 / 0.5) * 5730 = 2.54e-8 * 5730 ~ 1.46e-4 W = 0.146 mW

        docs/thermal-budget.md says 16 wires = ~3 mW, so 1 wire ~ 0.19 mW.
        Our calculation gives ~0.15 mW — consistent.
        """
        q = conduction_heat_load(
            materials["phosphor_bronze"],
            cross_section_m2=1.27e-8,
            length_m=0.5,
            t_cold_k=45.0,
            t_hot_k=300.0,
        )
        assert 0.05e-3 < q < 0.5e-3, f"Single PhBr wire 300->45K: {q*1e3:.3f} mW"

    def test_zero_length_raises_or_inf(self, materials):
        """Zero-length conductor should raise or give infinity."""
        with pytest.raises((ZeroDivisionError, ValueError)):
            conduction_heat_load(
                materials["ss304"],
                cross_section_m2=1e-6,
                length_m=0.0,
                t_cold_k=4.0,
                t_hot_k=300.0,
            )

    def test_zero_area_gives_zero(self, materials):
        """Zero cross-section should give zero heat load."""
        q = conduction_heat_load(
            materials["ss304"],
            cross_section_m2=0.0,
            length_m=0.3,
            t_cold_k=4.0,
            t_hot_k=300.0,
        )
        assert q == 0.0


# ---------------------------------------------------------------------------
# Radiation heat load tests
# ---------------------------------------------------------------------------

class TestRadiationHeatLoad:
    """Test radiation heat load calculations."""

    def test_bare_radiation_300k_to_4k(self):
        """
        Blackbody radiation from 300K to 4K:
        Q = eps * sigma * A * (300^4 - 4^4)
        With eps=0.05, A=0.08 m^2:
        Q = 0.05 * 5.67e-8 * 0.08 * (300^4 - 4^4)
          = 0.05 * 5.67e-8 * 0.08 * 8.1e9
          ~ 1.84 W

        docs/thermal-budget.md says ~1800 mW without MLI. Consistent.
        """
        sigma = 5.670374419e-8
        q = radiation_heat_load(
            sigma=sigma,
            emissivity=0.05,
            area_m2=0.08,
            t_hot_k=300.0,
            t_cold_k=40.0,  # Using 40K as in the doc
        )
        assert 1.5 < q < 2.2, f"Bare radiation 300->40K = {q:.3f} W, expected ~1.8 W"

    def test_radiation_40k_to_4k(self):
        """
        Radiation from 40K shield to 4K sample stage:
        Q = 0.1 * 5.67e-8 * 0.005 * (40^4 - 4^4)
          = 0.1 * 5.67e-8 * 0.005 * 2.56e6
          ~ 7.3e-5 W = 0.073 mW

        Very small. The doc says ~0.3 mW for a larger area (0.02 m^2).
        """
        sigma = 5.670374419e-8
        q = radiation_heat_load(
            sigma=sigma,
            emissivity=0.1,
            area_m2=0.005,
            t_hot_k=40.0,
            t_cold_k=4.0,
        )
        assert 0 < q < 0.5e-3, f"Radiation 40->4K = {q*1e3:.4f} mW"

    def test_radiation_zero_at_equal_temps(self):
        """No radiation if T_hot == T_cold."""
        sigma = 5.670374419e-8
        q = radiation_heat_load(
            sigma=sigma,
            emissivity=0.5,
            area_m2=1.0,
            t_hot_k=100.0,
            t_cold_k=100.0,
        )
        assert q == 0.0

    def test_stefan_boltzmann_blackbody(self):
        """
        Validate against known blackbody flux.
        Total flux from a 300K blackbody: sigma * T^4 = 459 W/m^2
        """
        sigma = 5.670374419e-8
        flux = sigma * 300.0**4
        assert 458 < flux < 460, f"Blackbody flux at 300K: {flux:.1f} W/m^2"


# ---------------------------------------------------------------------------
# Full budget integration tests
# ---------------------------------------------------------------------------

class TestFullBudget:
    """Integration tests on the complete thermal budget."""

    def test_budget_loads_not_empty(self, budget):
        """Budget should have multiple heat loads."""
        assert len(budget.loads) > 0

    def test_total_equals_sum_of_parts(self, budget):
        """Total for each stage must equal sum of individual loads."""
        for stage in ["1st stage", "2nd stage"]:
            total = budget.total_by_stage(stage)
            individual_sum = sum(h.load_w for h in budget.loads_by_stage(stage))
            assert abs(total - individual_sum) < 1e-15, (
                f"{stage}: total={total}, sum={individual_sum}"
            )

    def test_all_loads_positive(self, budget):
        """Every heat load should be non-negative."""
        for h in budget.loads:
            assert h.load_w >= 0, f"Negative load: {h.name} = {h.load_w} W"

    def test_2nd_stage_within_capacity(self, budget):
        """2nd stage load must be well within 100 mW capacity."""
        total_2nd = budget.total_by_stage("2nd stage")
        capacity = budget.stage_capacities["2nd stage"]
        assert total_2nd < capacity, (
            f"2nd stage overloaded: {total_2nd*1e3:.1f} mW > {capacity*1e3:.0f} mW"
        )

    def test_1st_stage_within_capacity(self, budget):
        """1st stage load must be within capacity."""
        total_1st = budget.total_by_stage("1st stage")
        capacity = budget.stage_capacities["1st stage"]
        assert total_1st < capacity, (
            f"1st stage overloaded: {total_1st*1e3:.1f} mW > {capacity*1e3:.0f} mW"
        )

    def test_2nd_stage_utilization_reasonable(self, budget):
        """
        2nd stage utilization should be low (< 50%).
        docs/thermal-budget.md shows ~2.4% for the basic build.
        With mechanical supports + alumina disk it may be higher,
        but still should be well under 50%.
        """
        util = budget.utilization_fraction("2nd stage")
        assert util < 0.5, f"2nd stage utilization {util*100:.1f}% is surprisingly high"

    def test_1st_stage_utilization_reasonable(self, budget):
        """1st stage utilization should be < 70% with MLI."""
        util = budget.utilization_fraction("1st stage")
        assert util < 0.7, f"1st stage utilization {util*100:.1f}% exceeds 70%"

    def test_dominant_2nd_stage_load_is_conduction(self, budget):
        """
        At the 2nd stage, conduction (coax + mechanical supports) should
        dominate over radiation. This is consistent with docs/thermal-budget.md
        which shows RF coax as the dominant 4K load.
        """
        stage_2_loads = budget.loads_by_stage("2nd stage")
        conduction_loads = [
            h for h in stage_2_loads
            if h.subsystem in ("wiring_rf", "wiring_dc", "mechanical", "ground_isolation")
        ]
        radiation_loads = [
            h for h in stage_2_loads
            if h.subsystem == "radiation"
        ]
        total_cond = sum(h.load_w for h in conduction_loads)
        total_rad = sum(h.load_w for h in radiation_loads)
        assert total_cond > total_rad, (
            f"Expected conduction > radiation at 4K: "
            f"cond={total_cond*1e3:.2f} mW, rad={total_rad*1e3:.4f} mW"
        )

    def test_cryocooler_model_populated(self, budget):
        """Cryocooler model should be set from inputs."""
        assert "RDK-101D" in budget.cryocooler_model

    def test_margin_is_complement_of_utilization(self, budget):
        """margin + utilization should equal 1.0 for each stage."""
        for stage in ["1st stage", "2nd stage"]:
            m = budget.margin_fraction(stage)
            u = budget.utilization_fraction(stage)
            assert abs(m + u - 1.0) < 1e-10, f"{stage}: margin={m}, util={u}"


# ---------------------------------------------------------------------------
# YAML inputs validation
# ---------------------------------------------------------------------------

class TestInputsValidity:
    """Validate the YAML inputs file structure and sanity."""

    def test_yaml_loads(self, inputs):
        """Inputs file should parse as valid YAML."""
        assert isinstance(inputs, dict)

    def test_required_sections(self, inputs):
        """All required top-level sections must exist."""
        required = [
            "cryocooler", "temperatures", "materials",
            "dc_wiring", "rf_coax", "radiation",
            "mechanical_supports", "ground_isolation",
        ]
        for section in required:
            assert section in inputs, f"Missing section: {section}"

    def test_temperatures_physical(self, inputs):
        """Temperature values should be physically reasonable."""
        temps = inputs["temperatures"]
        assert temps["room"] == 300.0
        assert 30 < temps["first_stage"] < 80
        assert 3 < temps["second_stage"] < 10

    def test_stefan_boltzmann_constant(self, inputs):
        """Stefan-Boltzmann constant should be correct."""
        sigma = inputs["radiation"]["stefan_boltzmann_constant"]
        assert abs(sigma - 5.670374419e-8) < 1e-15

    def test_no_hardcoded_numbers_in_script(self):
        """
        The thermal_budget.py script should not contain hardcoded physical
        constants (sigma, k values) or geometry (areas, lengths).
        We check that the Stefan-Boltzmann constant does not appear as a
        literal in the script source.
        """
        script_path = REPO_ROOT / "scripts" / "thermal_budget.py"
        source = script_path.read_text()
        # The SB constant should NOT be hardcoded
        assert "5.670" not in source, (
            "Stefan-Boltzmann constant appears hardcoded in thermal_budget.py"
        )
        # No hardcoded wire counts
        assert "= 16" not in source or "16" not in source.split("wire")[0], (
            "Check for hardcoded wire count in script"
        )


# ---------------------------------------------------------------------------
# Report format tests
# ---------------------------------------------------------------------------

class TestReportFormat:
    """Test that the report output is well-formed."""

    def test_report_contains_stage_headers(self, budget):
        """Report should contain headers for both stages."""
        from thermal_budget import format_report
        report = format_report(budget)
        assert "1ST STAGE" in report
        assert "2ND STAGE" in report

    def test_report_contains_utilization(self, budget):
        """Report should contain utilization percentages."""
        from thermal_budget import format_report
        report = format_report(budget)
        assert "Utilization:" in report
        assert "Margin:" in report

    def test_report_contains_cryocooler(self, budget):
        """Report should name the cryocooler model."""
        from thermal_budget import format_report
        report = format_report(budget)
        assert "RDK-101D" in report

    def test_json_output_structure(self, budget):
        """JSON output should have expected structure."""
        from thermal_budget import budget_to_dict
        d = budget_to_dict(budget)
        assert "cryocooler_model" in d
        assert "stages" in d
        assert "1st stage" in d["stages"]
        assert "2nd stage" in d["stages"]
        for stage_data in d["stages"].values():
            assert "capacity_w" in stage_data
            assert "total_load_w" in stage_data
            assert "utilization" in stage_data
            assert "margin" in stage_data
            assert "loads" in stage_data
