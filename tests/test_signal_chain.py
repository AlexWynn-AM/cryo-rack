"""
Tests for the signal chain simulator.

Validates:
  - Component models produce physically reasonable results
  - Thermal noise scales correctly with temperature (4K vs 300K)
  - SNR is positive at nominal AQFP operating point
  - Bandwidth bottleneck identification
  - Sweep produces monotonically increasing SNR with amplitude
  - Friis formula against hand calculation for 2-component chain
  - Default chain runs without errors
  - Minimum detectable signal is below nominal AQFP output

References:
  - scripts/signal_chain.py
  - Johnson-Nyquist noise: P = 4*k*T*B*R
  - Friis formula: F = F1 + (F2-1)/G1 + (F3-1)/(G1*G2) + ...
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

# Add scripts/ to path so we can import signal_chain
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from signal_chain import (
    K_BOLTZMANN,
    AQFPOutput,
    CoaxCable,
    CryoFeedthrough,
    IsolationTransformer,
    PCBTrace,
    RoomTempAmplifier,
    SignalChain,
    SignalState,
    Wirebond,
    default_chain,
)


# ---------------------------------------------------------------------------
# SignalState basic tests
# ---------------------------------------------------------------------------

class TestSignalState:
    """Test the SignalState dataclass properties."""

    def test_snr_calculation(self):
        """SNR = 20*log10(amplitude/noise)."""
        s = SignalState(
            amplitude_A=1e-6, noise_A=1e-9,
            bandwidth_Hz=1e9, temperature_K=4.2, impedance_ohm=50.0,
        )
        # 1 uA / 1 nA = 1000 => 60 dB
        assert abs(s.snr_dB - 60.0) < 0.01

    def test_snr_zero_noise(self):
        """Zero noise should give infinite SNR."""
        s = SignalState(
            amplitude_A=1e-6, noise_A=0.0,
            bandwidth_Hz=1e9, temperature_K=4.2, impedance_ohm=50.0,
        )
        assert s.snr_dB == float("inf")

    def test_voltage_from_current(self):
        """V = I * Z."""
        s = SignalState(
            amplitude_A=10e-6, noise_A=1e-9,
            bandwidth_Hz=1e9, temperature_K=4.2, impedance_ohm=50.0,
        )
        # 10 uA * 50 ohm = 500 uV
        assert abs(s.amplitude_V - 500e-6) < 1e-12


# ---------------------------------------------------------------------------
# Thermal noise: 4K vs 300K
# ---------------------------------------------------------------------------

class TestThermalNoise:
    """Validate that thermal noise scales correctly with temperature."""

    def test_4k_noise_75x_lower_than_300k(self):
        """
        Johnson-Nyquist noise power P = 4*k*T*B*R.
        At 4K vs 300K: ratio is T_hot/T_cold = 300/4 = 75.
        Noise current (sqrt of power) ratio: sqrt(75) ~ 8.66x.

        Generate two AQFP outputs at different temperatures and
        compare their noise currents.
        """
        source_4k = AQFPOutput(temperature_K=4.0, bandwidth_Hz_val=1e9)
        source_300k = AQFPOutput(temperature_K=300.0, bandwidth_Hz_val=1e9)
        dummy = SignalState(
            amplitude_A=0, noise_A=0, bandwidth_Hz=float("inf"),
            temperature_K=4.2, impedance_ohm=50.0,
        )

        state_4k = source_4k.propagate(dummy)
        state_300k = source_300k.propagate(dummy)

        # Noise power ratio should be 300/4 = 75
        noise_power_ratio = (state_300k.noise_A / state_4k.noise_A) ** 2
        assert abs(noise_power_ratio - 75.0) < 1.0, (
            f"Expected noise power ratio ~75, got {noise_power_ratio:.1f}"
        )

    def test_johnson_nyquist_known_value(self):
        """
        Hand calculation: 50 ohm at 300K, 1 GHz bandwidth.
        P = 4 * 1.381e-23 * 300 * 1e9 * 50 = 8.286e-13 W
        V_rms = sqrt(P * R) = sqrt(8.286e-13 * 50) = sqrt(4.143e-11) = 6.44 uV
        I_rms = V_rms / R = 6.44e-6 / 50 = 128.8 nA

        The AQFP source with 50 ohm output impedance at 300K should
        produce approximately this noise level.
        """
        source = AQFPOutput(
            output_impedance_ohm=50.0,
            temperature_K=300.0,
            bandwidth_Hz_val=1.0e9,
        )
        dummy = SignalState(
            amplitude_A=0, noise_A=0, bandwidth_Hz=float("inf"),
            temperature_K=300.0, impedance_ohm=50.0,
        )
        state = source.propagate(dummy)

        # Expected: ~128.8 nA
        expected_noise = math.sqrt(4.0 * K_BOLTZMANN * 300.0 * 1e9 * 50.0) / 50.0
        assert abs(state.noise_A - expected_noise) / expected_noise < 0.01, (
            f"Expected noise ~{expected_noise:.2e} A, got {state.noise_A:.2e} A"
        )


# ---------------------------------------------------------------------------
# Default chain integration tests
# ---------------------------------------------------------------------------

class TestDefaultChain:
    """Integration tests on the default signal chain."""

    @pytest.fixture
    def chain(self) -> SignalChain:
        return default_chain()

    @pytest.fixture
    def states(self, chain: SignalChain) -> list:
        return chain.propagate()

    def test_chain_runs_without_errors(self, chain: SignalChain):
        """Default chain propagation should complete without exceptions."""
        states = chain.propagate()
        assert len(states) == 7  # 7 components in default chain

    def test_all_states_have_positive_signal(self, states: list):
        """Signal amplitude should be positive at every stage."""
        for i, s in enumerate(states):
            assert s.amplitude_A > 0, f"Zero signal at stage {i}"

    def test_all_states_have_positive_noise(self, states: list):
        """Noise should be positive at every stage (no noiseless components)."""
        for i, s in enumerate(states):
            assert s.noise_A > 0, f"Zero noise at stage {i}"

    def test_snr_positive_at_output(self, states: list):
        """SNR should be positive (> 0 dB) at the final stage."""
        final = states[-1]
        assert final.snr_dB > 0, (
            f"Final SNR should be > 0 dB, got {final.snr_dB:.1f} dB"
        )

    def test_snr_above_10dB_at_output(self, states: list):
        """At nominal 10 uA, SNR should exceed 10 dB at the final stage."""
        final = states[-1]
        assert final.snr_dB > 10.0, (
            f"Final SNR should be > 10 dB, got {final.snr_dB:.1f} dB"
        )

    def test_amplifier_increases_signal(self, states: list):
        """The room-temp amplifier should increase signal amplitude."""
        # Amplifier is the last component (index 6)
        pre_amp = states[5]   # after coax
        post_amp = states[6]  # after amplifier
        assert post_amp.amplitude_A > pre_amp.amplitude_A, (
            "Amplifier should increase signal amplitude"
        )

    def test_amplifier_gain_approximately_60dB(self, states: list):
        """Amplifier voltage gain should be approximately 60 dB (1000x)."""
        pre_amp = states[5]
        post_amp = states[6]
        gain = post_amp.amplitude_A / pre_amp.amplitude_A
        gain_dB = 20.0 * math.log10(gain)
        assert 55.0 < gain_dB < 65.0, (
            f"Expected ~60 dB gain, got {gain_dB:.1f} dB"
        )

    def test_passive_components_attenuate(self, states: list):
        """All passive components (1-5) should attenuate the signal."""
        # Stages 1-5 are passive: wirebond, PCB, transformer, feedthrough, coax
        for i in range(1, 6):
            assert states[i].amplitude_A <= states[i - 1].amplitude_A * 1.01, (
                f"Passive component at stage {i} ({states[i].amplitude_A:.2e}) "
                f"should not amplify signal vs stage {i-1} "
                f"({states[i-1].amplitude_A:.2e})"
            )


# ---------------------------------------------------------------------------
# Bandwidth bottleneck tests
# ---------------------------------------------------------------------------

class TestBandwidthBottleneck:
    """Test bandwidth bottleneck identification."""

    def test_default_bottleneck_is_amplifier(self):
        """
        In the default chain, the room-temp amplifier has 1 GHz BW,
        which is narrower than the 5 GHz source and 18 GHz SMA/coax.
        """
        chain = default_chain()
        name, bw = chain.bandwidth_bottleneck()
        assert name == "Room Temp Amplifier", (
            f"Expected amplifier as bottleneck, got '{name}'"
        )
        assert abs(bw - 1.0e9) < 1e6, (
            f"Expected 1 GHz bottleneck, got {bw:.2e} Hz"
        )

    def test_custom_chain_bottleneck(self):
        """Inserting a narrow-band component should change the bottleneck."""
        chain = default_chain()
        # Replace coax with a very narrow-band version
        for i, comp in enumerate(chain.components):
            if isinstance(comp, CoaxCable):
                chain.components[i] = CoaxCable(
                    name="Narrow Coax",
                    bandwidth_Hz_val=100.0e6,  # 100 MHz
                )
                break

        name, bw = chain.bandwidth_bottleneck()
        assert name == "Narrow Coax"
        assert abs(bw - 100.0e6) < 1e3


# ---------------------------------------------------------------------------
# Sweep tests
# ---------------------------------------------------------------------------

class TestSweep:
    """Test the amplitude sweep functionality."""

    def test_sweep_runs(self):
        """Sweep should complete without errors."""
        chain = default_chain()
        result = chain.sweep_aqfp_amplitude()
        assert "amplitudes_A" in result
        assert "snr_dB_final" in result
        assert len(result["amplitudes_A"]) == len(result["snr_dB_final"])

    def test_sweep_monotonically_increasing(self):
        """SNR should increase monotonically with signal amplitude.

        More signal current => higher SNR.  The noise floor is dominated
        by room-temp amplifier noise which is amplitude-independent, so
        SNR should scale linearly with amplitude (in dB: 20 dB per decade).
        """
        chain = default_chain()
        amplitudes = [1e-7, 1e-6, 1e-5, 1e-4]
        result = chain.sweep_aqfp_amplitude(range_A=amplitudes)
        snrs = result["snr_dB_final"]

        for i in range(len(snrs) - 1):
            assert snrs[i + 1] > snrs[i], (
                f"SNR not monotonically increasing: "
                f"{snrs[i]:.1f} dB at {amplitudes[i]:.0e} A >= "
                f"{snrs[i+1]:.1f} dB at {amplitudes[i+1]:.0e} A"
            )

    def test_sweep_20dB_per_decade(self):
        """
        In the noise-dominated regime, SNR should increase ~20 dB
        per decade of amplitude increase (voltage-mode SNR).
        Allow +/- 3 dB tolerance for component interactions.
        """
        chain = default_chain()
        # Use small amplitudes where amplifier noise dominates
        amplitudes = [1e-8, 1e-7]
        result = chain.sweep_aqfp_amplitude(range_A=amplitudes)
        snrs = result["snr_dB_final"]
        delta_snr = snrs[1] - snrs[0]
        assert 17.0 < delta_snr < 23.0, (
            f"Expected ~20 dB per decade, got {delta_snr:.1f} dB"
        )


# ---------------------------------------------------------------------------
# Friis formula tests
# ---------------------------------------------------------------------------

class TestFriisFormula:
    """Test cascaded noise figure using Friis formula."""

    def test_two_component_hand_calculation(self):
        """
        Two-component Friis formula hand check.

        Component 1: amplifier with G1=100 (20 dB), NF1=2 dB (1.585 linear)
        Component 2: attenuator with G2=0.1 (-10 dB), NF2=10 dB (10.0 linear)

        F_total = F1 + (F2-1)/G1
                = 1.585 + (10.0 - 1.0) / 100
                = 1.585 + 0.09
                = 1.675

        NF_total = 10*log10(1.675) = 2.24 dB

        The first-stage noise figure dominates when first-stage gain is high.
        """
        amp = RoomTempAmplifier(
            gain_dB=20.0,
            noise_figure_dB_val=2.0,
            bandwidth_Hz_val=1e9,
        )
        atten = CoaxCable(
            length_m=1.0,
            attenuation_dB_per_m_per_GHz=10.0,  # Force 10 dB loss at 1 GHz
            impedance_ohm=50.0,
            temperature_K=290.0,  # Reference temp for standard Friis
        )

        chain = SignalChain(components=[amp, atten])

        # F1 = amplifier NF = 10^(2/10) = 1.585
        f1 = amp.noise_figure_linear
        g1 = amp.gain_linear  # 10^(20/10) = 100

        # F2 = attenuator NF: for attenuator at T_ref: NF = loss = 10^(10/10) = 10
        f2 = atten.noise_figure_linear
        # (For cable at 290K: NF = 1 + (290/290)*(L-1) = L)
        expected_f2 = 10.0  # 10 dB loss
        assert abs(f2 - expected_f2) < 0.5, (
            f"Expected attenuator NF ~{expected_f2:.1f}, got {f2:.2f}"
        )

        # Friis: F_total = F1 + (F2-1)/G1
        expected_f_total = f1 + (f2 - 1.0) / g1
        expected_nf_dB = 10.0 * math.log10(expected_f_total)

        nf_dB = chain.total_noise_figure()
        assert abs(nf_dB - expected_nf_dB) < 0.1, (
            f"Expected NF {expected_nf_dB:.2f} dB, got {nf_dB:.2f} dB"
        )

    def test_single_component_nf_equals_component_nf(self):
        """For a single component, total NF = component NF."""
        amp = RoomTempAmplifier(
            gain_dB=40.0,
            noise_figure_dB_val=3.0,
            bandwidth_Hz_val=1e9,
        )
        chain = SignalChain(components=[amp])
        nf = chain.total_noise_figure()
        assert abs(nf - 3.0) < 0.01, (
            f"Expected 3.0 dB, got {nf:.2f} dB"
        )


# ---------------------------------------------------------------------------
# Minimum detectable signal tests
# ---------------------------------------------------------------------------

class TestMinimumDetectableSignal:
    """Test the minimum detectable signal calculation."""

    def test_mds_below_nominal(self):
        """MDS should be well below nominal 10 uA AQFP output."""
        chain = default_chain()
        mds = chain.minimum_detectable_signal(target_snr_dB=10.0)
        assert mds < 10e-6, (
            f"MDS ({mds:.2e} A) should be below nominal 10 uA"
        )

    def test_mds_is_positive(self):
        """MDS should be a positive, finite value."""
        chain = default_chain()
        mds = chain.minimum_detectable_signal()
        assert mds > 0
        assert mds < float("inf")

    def test_higher_snr_target_needs_more_signal(self):
        """Higher SNR target should require more signal."""
        chain = default_chain()
        mds_10 = chain.minimum_detectable_signal(target_snr_dB=10.0)
        mds_20 = chain.minimum_detectable_signal(target_snr_dB=20.0)
        assert mds_20 > mds_10, (
            f"20 dB MDS ({mds_20:.2e}) should exceed 10 dB MDS ({mds_10:.2e})"
        )


# ---------------------------------------------------------------------------
# Individual component tests
# ---------------------------------------------------------------------------

class TestWirebond:
    """Test the wirebond component model."""

    def test_inductance_2mm(self):
        """2 mm wirebond should have ~2 nH inductance."""
        wb = Wirebond(length_mm=2.0)
        l = wb._inductance_H()
        assert abs(l - 2e-9) < 1e-12, f"Expected 2 nH, got {l:.2e} H"

    def test_resistance_drops_at_cryo(self):
        """Resistance at 4K should be lower than at 300K."""
        wb_cryo = Wirebond(temperature_K=4.2)
        # At 4K, resistance is reduced by RRR factor
        r = wb_cryo._resistance_ohm()
        # Gold, 2mm, 25um: rho_4K = 2.44e-8 / 30 = 8.13e-10 ohm*m
        # A = pi*(12.5e-6)^2 = 4.91e-10 m^2, L = 2e-3 m
        # R = 8.13e-10 * 2e-3 / 4.91e-10 = 3.31e-3 ohm = 3.3 mohm
        assert r < 0.01, f"Expected < 10 mohm at 4K, got {r:.4f} ohm"
        assert r > 0, "Resistance should be positive (gold is not superconducting)"

    def test_attenuation_small(self):
        """Wirebond attenuation should be very small (< 1%)."""
        wb = Wirebond()
        dummy = SignalState(
            amplitude_A=10e-6, noise_A=1e-9,
            bandwidth_Hz=1e9, temperature_K=4.2, impedance_ohm=50.0,
        )
        out = wb.propagate(dummy)
        attenuation = out.amplitude_A / dummy.amplitude_A
        assert attenuation > 0.99, (
            f"Wirebond attenuation too large: {(1-attenuation)*100:.2f}%"
        )


class TestPCBTrace:
    """Test the PCB trace component model."""

    def test_loss_is_small_at_4k(self):
        """At 4K, copper resistivity is very low; trace loss should be small."""
        trace = PCBTrace(temperature_K=4.2, copper_rrr=50.0)
        loss_dB = trace._conductor_loss_dB()
        assert loss_dB < 1.0, (
            f"Expected < 1 dB loss for 20mm trace at 4K, got {loss_dB:.3f} dB"
        )

    def test_loss_higher_at_300k(self):
        """At 300K, trace loss should be higher than at 4K."""
        trace_4k = PCBTrace(temperature_K=4.2, copper_rrr=50.0)
        trace_300k = PCBTrace(temperature_K=300.0, copper_rrr=1.0)
        loss_4k = trace_4k._conductor_loss_dB()
        loss_300k = trace_300k._conductor_loss_dB()
        assert loss_300k > loss_4k, (
            f"300K loss ({loss_300k:.3f} dB) should exceed 4K loss ({loss_4k:.3f} dB)"
        )

    def test_microstrip_impedance_reasonable(self):
        """Computed impedance should be in a reasonable range for Pyralux."""
        trace = PCBTrace()
        z = trace._microstrip_impedance()
        # For 100 um width on 100 um polyimide (eps_r=3.4), expect ~50-100 ohm
        assert 20.0 < z < 200.0, (
            f"Expected 20-200 ohm microstrip impedance, got {z:.1f} ohm"
        )


class TestIsolationTransformer:
    """Test the isolation transformer model."""

    def test_coupling_loss(self):
        """k=0.95 transformer should pass ~95% of signal (voltage)."""
        xfmr = IsolationTransformer(coupling_coefficient=0.95, insertion_loss_dB=0.0)
        dummy = SignalState(
            amplitude_A=10e-6, noise_A=1e-9,
            bandwidth_Hz=1e9, temperature_K=4.2, impedance_ohm=50.0,
        )
        out = xfmr.propagate(dummy)
        coupling = out.amplitude_A / dummy.amplitude_A
        assert abs(coupling - 0.95) < 0.01, (
            f"Expected ~0.95 coupling, got {coupling:.3f}"
        )

    def test_perfect_transformer(self):
        """k=1.0 transformer with 0 dB IL should pass signal unchanged."""
        xfmr = IsolationTransformer(
            coupling_coefficient=1.0, insertion_loss_dB=0.0,
        )
        dummy = SignalState(
            amplitude_A=10e-6, noise_A=1e-9,
            bandwidth_Hz=1e9, temperature_K=4.2, impedance_ohm=50.0,
        )
        out = xfmr.propagate(dummy)
        assert abs(out.amplitude_A - dummy.amplitude_A) / dummy.amplitude_A < 0.001


class TestCryoFeedthrough:
    """Test the cryogenic feedthrough model."""

    def test_temperature_transition(self):
        """Output temperature should be room temperature."""
        ft = CryoFeedthrough(temperature_out_K=300.0)
        dummy = SignalState(
            amplitude_A=10e-6, noise_A=1e-9,
            bandwidth_Hz=1e9, temperature_K=4.2, impedance_ohm=50.0,
        )
        out = ft.propagate(dummy)
        assert out.temperature_K == 300.0

    def test_insertion_loss(self):
        """0.5 dB insertion loss should attenuate by ~5.6%."""
        ft = CryoFeedthrough(insertion_loss_dB=0.5)
        dummy = SignalState(
            amplitude_A=10e-6, noise_A=1e-9,
            bandwidth_Hz=1e9, temperature_K=4.2, impedance_ohm=50.0,
        )
        out = ft.propagate(dummy)
        expected = 10e-6 * 10 ** (-0.5 / 20.0)
        assert abs(out.amplitude_A - expected) / expected < 0.01


class TestRoomTempAmplifier:
    """Test the room-temperature amplifier model."""

    def test_gain_applied(self):
        """60 dB gain should multiply signal by ~1000x."""
        amp = RoomTempAmplifier(gain_dB=60.0)
        dummy = SignalState(
            amplitude_A=1e-6, noise_A=1e-9,
            bandwidth_Hz=1e9, temperature_K=300.0, impedance_ohm=50.0,
        )
        out = amp.propagate(dummy)
        gain = out.amplitude_A / dummy.amplitude_A
        assert abs(gain - 1000.0) < 1.0, (
            f"Expected 1000x gain, got {gain:.1f}x"
        )

    def test_amplifier_adds_noise(self):
        """Amplifier with NF > 0 dB should add noise beyond thermal."""
        amp = RoomTempAmplifier(noise_figure_dB_val=2.0)
        # Very low input noise to see amplifier contribution clearly
        dummy = SignalState(
            amplitude_A=1e-6, noise_A=1e-15,
            bandwidth_Hz=1e9, temperature_K=300.0, impedance_ohm=50.0,
        )
        out = amp.propagate(dummy)
        # Output noise should be much larger than input noise * gain
        gain = 10.0 ** (60.0 / 20.0)
        amplified_input_noise = dummy.noise_A * gain
        assert out.noise_A > amplified_input_noise * 10, (
            "Amplifier should add significant noise beyond amplified input noise"
        )


# ---------------------------------------------------------------------------
# Table and JSON output tests
# ---------------------------------------------------------------------------

class TestOutput:
    """Test text and JSON output generation."""

    def test_table_output_contains_all_components(self):
        """Table output should mention every component."""
        chain = default_chain()
        table = chain.to_table()
        assert "AQFP Output" in table
        assert "Wirebond" in table
        assert "PCB Trace" in table
        assert "Isolation Transformer" in table
        assert "Feedthrough" in table
        assert "Coax Cable" in table
        assert "Room Temp Amplifier" in table

    def test_table_contains_summary(self):
        """Table should contain summary metrics."""
        chain = default_chain()
        table = chain.to_table()
        assert "Cascaded noise figure" in table
        assert "Bandwidth bottleneck" in table
        assert "Min detectable signal" in table

    def test_json_output_structure(self):
        """JSON output should have expected keys."""
        from signal_chain import chain_to_dict
        chain = default_chain()
        d = chain_to_dict(chain)
        assert "stages" in d
        assert "summary" in d
        assert len(d["stages"]) == 7
        assert "cascaded_noise_figure_dB" in d["summary"]
        assert "minimum_detectable_signal_A" in d["summary"]
        assert "final_snr_dB" in d["summary"]


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

class TestCLI:
    """Smoke test the CLI entry point."""

    def test_main_default_no_crash(self):
        """Running main with default args should not crash."""
        from signal_chain import main
        import io
        import contextlib

        # Capture stdout; main() should print to stdout
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            sys.argv = ["signal_chain.py"]
            main()
        output = f.getvalue()
        assert "SIGNAL CHAIN ANALYSIS" in output
