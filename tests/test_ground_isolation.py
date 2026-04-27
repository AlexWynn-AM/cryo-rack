"""
Tests for the ground isolation analysis.

Validates:
  - Parallel-plate capacitance formula against known values
  - Capacitive impedance calculation
  - Transformer CMRR interpolation
  - Full analysis integration (physical reasonableness)

References:
  - decisions/004-ground-isolation.md (ADR-004)
  - Alumina epsilon_r ~ 9.8 (polycrystalline Al2O3)
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

# Add scripts/ to path so we can import ground_isolation
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from ground_isolation import (
    EPSILON_0,
    AnalysisParams,
    AnalysisResult,
    DiskBreakParams,
    TransformerParams,
    analyze_ground_isolation,
    capacitive_impedance,
    interpolate_cmrr_db,
    parallel_plate_capacitance,
)


# ---------------------------------------------------------------------------
# Parallel-plate capacitance tests
# ---------------------------------------------------------------------------

class TestParallelPlateCapacitance:
    """Validate the parallel-plate capacitance formula C = eps0 * eps_r * A / d."""

    def test_vacuum_capacitor_known_value(self):
        """
        Two 1 m^2 plates separated by 1 m in vacuum:
        C = eps0 * 1 * 1 / 1 = 8.854e-12 F = 8.854 pF.
        """
        c = parallel_plate_capacitance(EPSILON_0, 1.0, 1.0, 1.0)
        assert abs(c - 8.854187817e-12) < 1e-18

    def test_alumina_disk_25mm_3mm(self):
        """
        25 mm diameter, 3 mm thick alumina (eps_r = 9.8):
        A = pi * (0.0125)^2 = 4.909e-4 m^2
        C = 8.854e-12 * 9.8 * 4.909e-4 / 0.003
        C = 8.854e-12 * 4.810e-3 / 0.003
        C = 8.854e-12 * 1.603 = 1.419e-11 F = 14.19 pF

        Hand calculation cross-check:
        eps0 * eps_r = 8.854e-12 * 9.8 = 8.677e-11 F/m
        A/d = 4.909e-4 / 0.003 = 0.1636 m
        C = 8.677e-11 * 0.1636 = 1.420e-11 F ~ 14.2 pF
        """
        area = math.pi * (0.025 / 2.0) ** 2
        c = parallel_plate_capacitance(EPSILON_0, 9.8, area, 0.003)
        c_pf = c * 1e12
        # Should be ~14.2 pF
        assert 13.5 < c_pf < 15.0, f"Expected ~14.2 pF, got {c_pf:.2f} pF"

    def test_scales_linearly_with_area(self):
        """Doubling area should double capacitance."""
        c1 = parallel_plate_capacitance(EPSILON_0, 9.8, 1e-4, 0.001)
        c2 = parallel_plate_capacitance(EPSILON_0, 9.8, 2e-4, 0.001)
        assert abs(c2 / c1 - 2.0) < 1e-10

    def test_scales_inversely_with_thickness(self):
        """Doubling thickness should halve capacitance."""
        c1 = parallel_plate_capacitance(EPSILON_0, 9.8, 1e-4, 0.001)
        c2 = parallel_plate_capacitance(EPSILON_0, 9.8, 1e-4, 0.002)
        assert abs(c1 / c2 - 2.0) < 1e-10

    def test_scales_linearly_with_epsilon_r(self):
        """Doubling epsilon_r should double capacitance."""
        c1 = parallel_plate_capacitance(EPSILON_0, 5.0, 1e-4, 0.001)
        c2 = parallel_plate_capacitance(EPSILON_0, 10.0, 1e-4, 0.001)
        assert abs(c2 / c1 - 2.0) < 1e-10

    def test_zero_separation_raises(self):
        """Zero plate separation should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            parallel_plate_capacitance(EPSILON_0, 9.8, 1e-4, 0.0)

    def test_negative_separation_raises(self):
        """Negative plate separation should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            parallel_plate_capacitance(EPSILON_0, 9.8, 1e-4, -0.001)

    def test_textbook_example_air_capacitor(self):
        """
        Textbook: Two circular plates, 10 cm radius, 1 mm apart in air (eps_r=1).
        A = pi * 0.1^2 = 0.03142 m^2
        C = 8.854e-12 * 1.0 * 0.03142 / 0.001 = 2.782e-10 F = 278.2 pF
        """
        area = math.pi * 0.1**2
        c = parallel_plate_capacitance(EPSILON_0, 1.0, area, 0.001)
        c_pf = c * 1e12
        assert 277 < c_pf < 280, f"Expected ~278 pF, got {c_pf:.1f} pF"

    def test_1inch_disk_1mm_alumina(self):
        """
        1 inch (25.4 mm) diameter, 1 mm thick alumina:
        A = pi * (0.0127)^2 = 5.067e-4 m^2
        C = 8.854e-12 * 9.8 * 5.067e-4 / 0.001 = 4.396e-11 F ~ 43.96 pF

        Thinner disk = much more capacitance. This is why 3mm is chosen
        over 1mm: thicker disk trades thermal resistance for less parasitic C.
        """
        area = math.pi * (0.0254 / 2.0) ** 2
        c = parallel_plate_capacitance(EPSILON_0, 9.8, area, 0.001)
        c_pf = c * 1e12
        assert 43.0 < c_pf < 45.0, f"Expected ~44 pF, got {c_pf:.1f} pF"


# ---------------------------------------------------------------------------
# Capacitive impedance tests
# ---------------------------------------------------------------------------

class TestCapacitiveImpedance:
    """Validate Z = 1 / (2*pi*f*C)."""

    def test_known_impedance(self):
        """
        1 pF at 1 GHz:
        Z = 1 / (2*pi * 1e9 * 1e-12) = 1 / (6.283e-3) = 159.15 ohm
        """
        z = capacitive_impedance(1e-12, 1e9)
        assert 158 < z < 161, f"Expected ~159 ohm, got {z:.1f}"

    def test_14pf_at_1hz(self):
        """
        14 pF at 1 Hz:
        Z = 1 / (2*pi * 1 * 14e-12) = 1.137e10 ohm ~ 11.4 Gohm
        """
        z = capacitive_impedance(14e-12, 1.0)
        assert 1.1e10 < z < 1.2e10, f"Expected ~11.4 Gohm, got {z:.2e}"

    def test_14pf_at_5ghz(self):
        """
        14 pF at 5 GHz:
        Z = 1 / (2*pi * 5e9 * 14e-12) = 1 / (0.4398) = 2.27 ohm
        """
        z = capacitive_impedance(14e-12, 5e9)
        assert 2.0 < z < 2.6, f"Expected ~2.3 ohm, got {z:.2f}"

    def test_zero_frequency_returns_inf(self):
        """DC: impedance should be infinite."""
        z = capacitive_impedance(1e-12, 0.0)
        assert z == float("inf")

    def test_zero_capacitance_returns_inf(self):
        """Zero capacitance: impedance should be infinite."""
        z = capacitive_impedance(0.0, 1e6)
        assert z == float("inf")

    def test_impedance_inversely_proportional_to_freq(self):
        """Doubling frequency should halve impedance."""
        z1 = capacitive_impedance(1e-12, 1e6)
        z2 = capacitive_impedance(1e-12, 2e6)
        assert abs(z1 / z2 - 2.0) < 1e-10


# ---------------------------------------------------------------------------
# Transformer CMRR interpolation tests
# ---------------------------------------------------------------------------

class TestCMRRInterpolation:
    """Test log-linear interpolation of CMRR vs frequency."""

    def test_at_calibration_point(self):
        """CMRR at a calibration point should return exact value."""
        freqs = [1e3, 100e3, 1e6]
        cmrrs = [140.0, 100.0, 80.0]
        assert interpolate_cmrr_db(1e3, freqs, cmrrs) == 140.0
        assert interpolate_cmrr_db(100e3, freqs, cmrrs) == 100.0
        assert interpolate_cmrr_db(1e6, freqs, cmrrs) == 80.0

    def test_midpoint_interpolation(self):
        """
        At geometric midpoint between 1 kHz and 100 kHz (= 10 kHz),
        CMRR should be midpoint of 140 and 100 = 120 dB (log-linear).
        """
        freqs = [1e3, 100e3, 1e6]
        cmrrs = [140.0, 100.0, 80.0]
        # 10 kHz is the geometric midpoint of 1 kHz and 100 kHz
        cmrr = interpolate_cmrr_db(10e3, freqs, cmrrs)
        assert abs(cmrr - 120.0) < 0.1, f"Expected 120 dB, got {cmrr:.1f}"

    def test_below_range_clamps(self):
        """Below lowest frequency should return lowest CMRR value."""
        freqs = [1e3, 100e3, 1e6]
        cmrrs = [140.0, 100.0, 80.0]
        cmrr = interpolate_cmrr_db(100.0, freqs, cmrrs)
        assert cmrr == 140.0

    def test_above_range_clamps(self):
        """Above highest frequency should return highest CMRR value."""
        freqs = [1e3, 100e3, 1e6]
        cmrrs = [140.0, 100.0, 80.0]
        cmrr = interpolate_cmrr_db(10e6, freqs, cmrrs)
        assert cmrr == 80.0

    def test_monotonic_decrease(self):
        """CMRR should decrease monotonically with increasing frequency."""
        freqs = [1e3, 100e3, 1e6]
        cmrrs = [140.0, 100.0, 80.0]
        test_freqs = [1e3, 5e3, 10e3, 50e3, 100e3, 500e3, 1e6]
        values = [interpolate_cmrr_db(f, freqs, cmrrs) for f in test_freqs]
        for i in range(len(values) - 1):
            assert values[i] >= values[i + 1], (
                f"CMRR not monotonically decreasing: {values[i]} < {values[i+1]} "
                f"at {test_freqs[i]:.0e} -> {test_freqs[i+1]:.0e} Hz"
            )

    def test_mismatched_lengths_raises(self):
        """Mismatched frequency and CMRR lists should raise."""
        with pytest.raises(ValueError, match="equal length"):
            interpolate_cmrr_db(1e3, [1e3, 100e3], [140.0])

    def test_single_point_raises(self):
        """Need at least two calibration points."""
        with pytest.raises(ValueError, match="at least two"):
            interpolate_cmrr_db(1e3, [1e3], [140.0])


# ---------------------------------------------------------------------------
# Full analysis integration tests
# ---------------------------------------------------------------------------

class TestFullAnalysis:
    """Integration tests on the complete ground isolation analysis."""

    @pytest.fixture
    def result(self) -> AnalysisResult:
        """Run analysis with default parameters."""
        return analyze_ground_isolation()

    def test_capacitance_physical_range(self, result: AnalysisResult):
        """
        25 mm alumina disk, 3 mm thick: expect 10-20 pF.
        This is the parallel-plate approximation; fringing fields add
        maybe 10-20% but the parallel-plate model is conservative
        (underestimates) for isolation analysis.
        """
        assert 10 < result.parasitic_capacitance_pf < 20, (
            f"Expected 10-20 pF, got {result.parasitic_capacitance_pf:.2f} pF"
        )

    def test_low_freq_impedance_is_high(self, result: AnalysisResult):
        """At 1 Hz compressor frequency, impedance should be > 1 Gohm."""
        comp_z = result.impedance_results[0]
        assert comp_z.frequency_hz == 1.0
        assert comp_z.impedance_ohm > 1e9, (
            f"Expected > 1 Gohm at 1 Hz, got {comp_z.impedance_ohm:.2e} ohm"
        )

    def test_coupled_current_at_1hz_below_threshold(self, result: AnalysisResult):
        """
        At 1 Hz with 500 mV transient, coupled current should be << 100 nA.
        Z ~ 11 Gohm, so I = 0.5 / 11e9 ~ 45 fA. Way below threshold.
        """
        comp_result = result.impedance_results[0]
        assert comp_result.coupled_current_a < 100e-9, (
            f"Coupled current at 1 Hz: {comp_result.coupled_current_a:.2e} A "
            f"exceeds 100 nA threshold"
        )

    def test_coupled_current_at_60hz_below_threshold(self, result: AnalysisResult):
        """At 60 Hz mains with 1V CM, coupled current should be << 100 nA."""
        mains_result = result.impedance_results[1]
        assert mains_result.frequency_hz == 60.0
        assert mains_result.coupled_current_a < 100e-9

    def test_ghz_impedance_is_low(self, result: AnalysisResult):
        """At 5 GHz, impedance should be only a few ohms (not an isolator)."""
        ghz_result = result.impedance_results[3]
        assert ghz_result.frequency_hz == 5e9
        assert ghz_result.impedance_ohm < 10, (
            f"Expected < 10 ohm at 5 GHz, got {ghz_result.impedance_ohm:.2f}"
        )

    def test_isolation_adequate(self, result: AnalysisResult):
        """Default parameters should yield adequate isolation."""
        assert result.isolation_adequate is True

    def test_assessment_has_pass_notes(self, result: AnalysisResult):
        """Assessment should contain PASS notes for compressor and mains."""
        pass_notes = [n for n in result.assessment_notes if n.startswith("PASS")]
        assert len(pass_notes) >= 2, (
            f"Expected at least 2 PASS notes, got {len(pass_notes)}"
        )

    def test_custom_disk_parameters(self):
        """Analysis with custom disk parameters should reflect them."""
        disk = DiskBreakParams(diameter_m=0.050, thickness_m=0.001, epsilon_r=9.8)
        result = analyze_ground_isolation(disk=disk)
        # 50 mm dia, 1 mm thick: ~4x area, 3x less thickness = ~12x more C
        # vs default 25mm/3mm. Expect ~170 pF.
        assert result.parasitic_capacitance_pf > 100, (
            f"Expected > 100 pF for 50mm/1mm disk, got "
            f"{result.parasitic_capacitance_pf:.1f} pF"
        )

    def test_json_output_has_expected_keys(self, result: AnalysisResult):
        """JSON output structure should have all expected keys."""
        from ground_isolation import result_to_dict
        d = result_to_dict(result)
        assert "disk_break" in d
        assert "impedance_vs_frequency" in d
        assert "transformer" in d
        assert "assessment" in d
        assert "parasitic_capacitance_pf" in d["disk_break"]
        assert "isolation_adequate" in d["assessment"]


# ---------------------------------------------------------------------------
# Sensitivity / parametric tests
# ---------------------------------------------------------------------------

class TestSensitivity:
    """Test how isolation metrics respond to parameter changes."""

    def test_thicker_disk_less_capacitance(self):
        """Thicker disk should have less parasitic capacitance."""
        thin = DiskBreakParams(thickness_m=0.001)
        thick = DiskBreakParams(thickness_m=0.005)
        r_thin = analyze_ground_isolation(disk=thin)
        r_thick = analyze_ground_isolation(disk=thick)
        assert r_thick.parasitic_capacitance_pf < r_thin.parasitic_capacitance_pf

    def test_larger_disk_more_capacitance(self):
        """Larger diameter disk should have more parasitic capacitance."""
        small = DiskBreakParams(diameter_m=0.020)
        large = DiskBreakParams(diameter_m=0.040)
        r_small = analyze_ground_isolation(disk=small)
        r_large = analyze_ground_isolation(disk=large)
        assert r_large.parasitic_capacitance_pf > r_small.parasitic_capacitance_pf

    def test_2inch_disk_still_adequate_at_low_freq(self):
        """Even a 2-inch disk (more capacitance) should pass at low freq."""
        big_disk = DiskBreakParams(diameter_m=0.0508, thickness_m=0.003)
        result = analyze_ground_isolation(disk=big_disk)
        # More capacitance but still huge impedance at 1 Hz
        comp_result = result.impedance_results[0]
        assert comp_result.coupled_current_a < 100e-9
