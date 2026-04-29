#!/usr/bin/env python3
"""
Signal Chain Simulator: AQFP Chip Output to Room-Temperature Measurement

Models signal propagation from the AQFP die at 4K through the cryogenic
system to room-temperature test equipment.  Computes signal amplitude,
noise, SNR, and bandwidth at each stage of the chain.

Signal chain (default configuration):

  1. AQFP output amplifier at 4K  (~10 uA into a few ohm)
  2. Wirebond: Au, ~2 mm          (~2 nH inductance, low R at 4K)
  3. Flex PCB trace: Pyralux, 4K   (50 ohm microstrip, 20 mm)
  4. Isolation transformer         (1:1, k=0.95, 10 GHz BW)
  5. SMA feedthrough               (50 ohm, 0.5 dB insertion loss)
  6. Coaxial cable at 300K         (50 ohm, 1 m semi-rigid)
  7. Room-temp low-noise amplifier (60 dB gain, 2 dB NF, 1 GHz BW)

Physics:
  - Johnson-Nyquist thermal noise:  P = 4*k*T*B*R  (per stage temp)
  - Friis cascaded noise figure:    F = F1 + (F2-1)/G1 + ...
  - Bandwidth limited by narrowest component

All inputs are parameterized via dataclass defaults or CLI overrides.
No hardcoded physics constants in computation functions.

Usage:
    python scripts/signal_chain.py
    python scripts/signal_chain.py --json
    python scripts/signal_chain.py --sweep
    python scripts/signal_chain.py --aqfp-current 20e-6

References:
    - decisions/004-ground-isolation.md  (isolation transformer)
    - data/thermal_inputs.yaml           (Pyralux PCB, coax specs)
    - docs/system-architecture.md        (signal path description)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from typing import Any, List, Tuple


# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

K_BOLTZMANN = 1.380649e-23  # J/K, Boltzmann constant (exact, 2019 SI)


# ---------------------------------------------------------------------------
# Signal state
# ---------------------------------------------------------------------------

@dataclass
class SignalState:
    """Signal state at a point in the chain.

    Represents the electrical signal condition after passing through
    a component (or at the chain input).
    """
    amplitude_A: float      # Signal current amplitude (A)
    noise_A: float          # RMS noise current (A)
    bandwidth_Hz: float     # -3 dB bandwidth (Hz)
    temperature_K: float    # Local temperature (K)
    impedance_ohm: float    # Characteristic impedance at this point (ohm)

    @property
    def amplitude_V(self) -> float:
        """Signal voltage amplitude: V = I * Z."""
        return self.amplitude_A * self.impedance_ohm

    @property
    def noise_V(self) -> float:
        """RMS noise voltage: V = I * Z."""
        return self.noise_A * self.impedance_ohm

    @property
    def snr_linear(self) -> float:
        """Signal-to-noise ratio (linear)."""
        if self.noise_A <= 0:
            return float("inf")
        return self.amplitude_A / self.noise_A

    @property
    def snr_dB(self) -> float:
        """Signal-to-noise ratio in dB."""
        s = self.snr_linear
        if s == float("inf"):
            return float("inf")
        if s <= 0:
            return float("-inf")
        return 20.0 * math.log10(s)


# ---------------------------------------------------------------------------
# Component base class
# ---------------------------------------------------------------------------

class Component:
    """Base class for signal chain components."""

    name: str = "Component"

    def propagate(self, signal: SignalState) -> SignalState:
        """Propagate a signal through this component.

        Returns a new SignalState representing the signal after passing
        through the component.
        """
        raise NotImplementedError

    @property
    def gain_linear(self) -> float:
        """Power gain (linear).  < 1 for lossy components."""
        return 1.0

    @property
    def noise_figure_linear(self) -> float:
        """Noise figure (linear).  1.0 = ideal (no added noise)."""
        return 1.0

    @property
    def noise_figure_dB(self) -> float:
        """Noise figure in dB."""
        nf = self.noise_figure_linear
        if nf <= 0:
            return float("-inf")
        return 10.0 * math.log10(nf)

    @property
    def bandwidth_Hz(self) -> float:
        """Component -3 dB bandwidth in Hz."""
        return float("inf")


# ---------------------------------------------------------------------------
# Component models
# ---------------------------------------------------------------------------

@dataclass
class AQFPOutput(Component):
    """AQFP output amplifier at 4K.

    Generates the initial signal state.  The AQFP output is a current
    source driving into a low output impedance.
    """
    name: str = "AQFP Output (4K)"
    signal_current_A: float = 10.0e-6   # 10 uA typical
    output_impedance_ohm: float = 5.0   # Few ohm output Z
    temperature_K: float = 4.2          # Operating at 4K
    bandwidth_Hz_val: float = 5.0e9     # 5 GHz AC clock

    def propagate(self, signal: SignalState) -> SignalState:
        """Generate the initial signal state from the AQFP output."""
        # Johnson-Nyquist noise at 4K from the output impedance
        noise_power = 4.0 * K_BOLTZMANN * self.temperature_K * self.bandwidth_Hz_val * self.output_impedance_ohm
        noise_current = math.sqrt(noise_power) / self.output_impedance_ohm

        return SignalState(
            amplitude_A=self.signal_current_A,
            noise_A=noise_current,
            bandwidth_Hz=self.bandwidth_Hz_val,
            temperature_K=self.temperature_K,
            impedance_ohm=self.output_impedance_ohm,
        )

    @property
    def gain_linear(self) -> float:
        return 1.0

    @property
    def noise_figure_linear(self) -> float:
        return 1.0

    @property
    def bandwidth_Hz(self) -> float:
        return self.bandwidth_Hz_val


@dataclass
class Wirebond(Component):
    """Gold or aluminum wirebond.

    Model: inductance ~1 nH/mm, resistance depends on temp and material.
    At 4K: gold is not superconducting; resistance drops by the residual
    resistivity ratio (RRR) factor from room temperature.
    """
    name: str = "Wirebond"
    length_mm: float = 2.0              # 2 mm bond wire
    diameter_um: float = 25.0           # 25 um (1 mil) standard
    material: str = "Au"                # "Au" or "Al"
    temperature_K: float = 4.2          # Local temperature

    # Material properties at 300K
    _RESISTIVITY_300K = {"Au": 2.44e-8, "Al": 2.65e-8}  # ohm*m
    _RRR = {"Au": 30.0, "Al": 10.0}  # Residual resistivity ratio
    _INDUCTANCE_PER_MM_NH = 1.0  # nH/mm, standard rule of thumb

    def _resistance_ohm(self) -> float:
        """Compute wirebond resistance at operating temperature.

        At cryogenic temperatures, resistance drops by the RRR factor
        from its room-temperature value.  Gold at 4K: RRR ~ 30 for
        bonding wire (not ultra-pure single crystal).
        """
        rho_300k = self._RESISTIVITY_300K[self.material]
        rrr = self._RRR[self.material]
        # Scale resistivity: at 4K, rho ~ rho_300K / RRR
        # (simplified; real curve is Bloch-Gruneisen but RRR ratio
        # is adequate for the low-temperature residual resistance)
        rho = rho_300k / rrr
        area_m2 = math.pi * (self.diameter_um * 1e-6 / 2.0) ** 2
        length_m = self.length_mm * 1e-3
        return rho * length_m / area_m2

    def _inductance_H(self) -> float:
        """Wirebond inductance: ~1 nH/mm."""
        return self.length_mm * self._INDUCTANCE_PER_MM_NH * 1e-9

    def propagate(self, signal: SignalState) -> SignalState:
        """Propagate signal through the wirebond."""
        r = self._resistance_ohm()
        l = self._inductance_H()

        # Loss: resistive dissipation.  Voltage drop across R reduces
        # the current delivered to the next impedance.
        # Model as series resistance: I_out = I_in * Z_load / (Z_load + R)
        z_load = signal.impedance_ohm  # downstream impedance
        attenuation = z_load / (z_load + r)

        # Bandwidth limitation from L: f_3dB = R_total / (2*pi*L)
        # where R_total is the total circuit resistance seen by L
        r_total = z_load + r
        if l > 0:
            bw_wirebond = r_total / (2.0 * math.pi * l)
        else:
            bw_wirebond = float("inf")

        # Thermal noise from the wirebond resistance
        bw = min(signal.bandwidth_Hz, bw_wirebond)
        noise_power_added = 4.0 * K_BOLTZMANN * self.temperature_K * bw * r
        noise_current_added = math.sqrt(noise_power_added) / z_load if z_load > 0 else 0.0

        # Combine noise: existing noise attenuated + new noise added
        noise_out = math.sqrt((signal.noise_A * attenuation) ** 2 + noise_current_added ** 2)

        return SignalState(
            amplitude_A=signal.amplitude_A * attenuation,
            noise_A=noise_out,
            bandwidth_Hz=bw,
            temperature_K=self.temperature_K,
            impedance_ohm=signal.impedance_ohm,
        )

    @property
    def gain_linear(self) -> float:
        # Approximate for Friis: use nominal 50 ohm load
        r = self._resistance_ohm()
        return 50.0 / (50.0 + r)  # power ratio

    @property
    def noise_figure_linear(self) -> float:
        r = self._resistance_ohm()
        # For a resistive attenuator at temperature T in a T_ref system:
        # NF = 1 + T/T_ref * (L - 1), where L = 1/gain
        # For a passive resistor at 4K in a 290K reference system:
        t_ref = 290.0
        loss = 1.0 / self.gain_linear
        return 1.0 + (self.temperature_K / t_ref) * (loss - 1.0)

    @property
    def bandwidth_Hz(self) -> float:
        l = self._inductance_H()
        if l <= 0:
            return float("inf")
        r = self._resistance_ohm()
        r_total = 50.0 + r  # nominal
        return r_total / (2.0 * math.pi * l)


@dataclass
class PCBTrace(Component):
    """Flex PCB microstrip trace (Pyralux AP 8541).

    At 4K: copper resistance drops dramatically.  RA (rolled-annealed)
    copper has RRR ~ 50-100.  We model the trace as a lossy microstrip
    with temperature-dependent conductor loss.
    """
    name: str = "PCB Trace (4K)"
    length_mm: float = 20.0             # 20 mm trace
    width_um: float = 100.0             # 100 um trace width
    substrate_thickness_um: float = 100.0  # 4 mil polyimide (Pyralux)
    copper_thickness_um: float = 17.5   # 1/2 oz copper = 17.5 um
    temperature_K: float = 4.2
    impedance_target_ohm: float = 50.0
    # Pyralux AP 8541 polyimide: eps_r ~ 3.4
    epsilon_r: float = 3.4
    # RA copper RRR
    copper_rrr: float = 50.0
    # Copper resistivity at 300K
    copper_rho_300k: float = 1.68e-8    # ohm*m

    def _conductor_loss_dB(self) -> float:
        """Conductor loss for the microstrip trace.

        At 4K, copper resistivity drops by RRR factor.
        Loss (dB/m) = R_s / (Z0 * w) * 8.686, where R_s is surface
        resistance per unit length.
        """
        rho = self.copper_rho_300k / self.copper_rrr
        # DC sheet resistance: R_sheet = rho / thickness
        t_m = self.copper_thickness_um * 1e-6
        w_m = self.width_um * 1e-6
        # Resistance per unit length: R/L = rho / (w * t)
        r_per_m = rho / (w_m * t_m)
        # Loss in dB for total length
        length_m = self.length_mm * 1e-3
        # Attenuation: alpha = R / (2 * Z0) [Np/m]
        alpha_np_per_m = r_per_m / (2.0 * self.impedance_target_ohm)
        alpha_dB_per_m = alpha_np_per_m * 8.686
        return alpha_dB_per_m * length_m

    def _microstrip_impedance(self) -> float:
        """Approximate microstrip impedance.

        Using the Hammerstad-Jensen formula for w/h ratio.
        """
        w = self.width_um * 1e-6
        h = self.substrate_thickness_um * 1e-6
        er = self.epsilon_r
        u = w / h

        if u <= 1:
            z0 = (60.0 / math.sqrt(er)) * math.log(8.0 / u + u / 4.0)
        else:
            z0 = (120.0 * math.pi) / (math.sqrt(er) * (u + 1.393 + 0.667 * math.log(u + 1.444)))
        return z0

    def propagate(self, signal: SignalState) -> SignalState:
        """Propagate signal through the PCB trace."""
        loss_dB = self._conductor_loss_dB()
        loss_linear = 10.0 ** (-loss_dB / 20.0)  # voltage ratio

        z_trace = self._microstrip_impedance()

        # Impedance mismatch loss (simplified: reflection at boundaries)
        z_in = signal.impedance_ohm
        # Reflection coefficient
        if (z_trace + z_in) > 0:
            gamma = abs(z_trace - z_in) / (z_trace + z_in)
        else:
            gamma = 0.0
        mismatch_loss = 1.0 - gamma ** 2  # power transmission
        mismatch_voltage = math.sqrt(mismatch_loss)

        total_attenuation = loss_linear * mismatch_voltage

        # Noise from the trace resistance at 4K
        bw = signal.bandwidth_Hz
        r_per_m = self.copper_rho_300k / self.copper_rrr / (self.width_um * 1e-6 * self.copper_thickness_um * 1e-6)
        r_total = r_per_m * (self.length_mm * 1e-3)
        noise_power_added = 4.0 * K_BOLTZMANN * self.temperature_K * bw * r_total
        z_out = self.impedance_target_ohm
        noise_current_added = math.sqrt(noise_power_added) / z_out if z_out > 0 else 0.0

        noise_out = math.sqrt((signal.noise_A * total_attenuation) ** 2 + noise_current_added ** 2)

        return SignalState(
            amplitude_A=signal.amplitude_A * total_attenuation,
            noise_A=noise_out,
            bandwidth_Hz=bw,
            temperature_K=self.temperature_K,
            impedance_ohm=self.impedance_target_ohm,
        )

    @property
    def gain_linear(self) -> float:
        loss_dB = self._conductor_loss_dB()
        return 10.0 ** (-loss_dB / 10.0)  # power gain < 1

    @property
    def noise_figure_linear(self) -> float:
        t_ref = 290.0
        loss = 1.0 / self.gain_linear
        return 1.0 + (self.temperature_K / t_ref) * (loss - 1.0)

    @property
    def bandwidth_Hz(self) -> float:
        return float("inf")  # Trace BW >> operating frequency for these lengths


@dataclass
class IsolationTransformer(Component):
    """Ground isolation transformer (per ADR-004).

    Located at the 4K stage between the PCB and the feedthrough.
    Purpose: break ground loop between cryostat ground domains.
    Model: turns ratio, coupling coefficient, bandwidth.
    """
    name: str = "Isolation Transformer"
    turns_ratio: float = 1.0            # 1:1
    coupling_coefficient: float = 0.95  # k = 0.95
    bandwidth_Hz_val: float = 10.0e9    # 10 GHz
    insertion_loss_dB: float = 0.5      # Small additional loss
    temperature_K: float = 4.2          # At 4K stage

    def propagate(self, signal: SignalState) -> SignalState:
        """Propagate signal through the isolation transformer."""
        # Coupling loss: signal transmitted = k * turns_ratio
        coupling_attenuation = self.coupling_coefficient * self.turns_ratio

        # Insertion loss
        il_linear = 10.0 ** (-self.insertion_loss_dB / 20.0)
        total_attenuation = coupling_attenuation * il_linear

        bw = min(signal.bandwidth_Hz, self.bandwidth_Hz_val)

        # Noise: transformer is passive at 4K, adds minimal thermal noise
        # Model as attenuator noise contribution
        r_equiv = signal.impedance_ohm * (1.0 - coupling_attenuation ** 2) / coupling_attenuation ** 2
        if r_equiv > 0:
            noise_power_added = 4.0 * K_BOLTZMANN * self.temperature_K * bw * r_equiv
            noise_current_added = math.sqrt(noise_power_added) / signal.impedance_ohm
        else:
            noise_current_added = 0.0

        noise_out = math.sqrt((signal.noise_A * total_attenuation) ** 2 + noise_current_added ** 2)

        return SignalState(
            amplitude_A=signal.amplitude_A * total_attenuation,
            noise_A=noise_out,
            bandwidth_Hz=bw,
            temperature_K=self.temperature_K,
            impedance_ohm=signal.impedance_ohm / self.turns_ratio,
        )

    @property
    def gain_linear(self) -> float:
        g = (self.coupling_coefficient * self.turns_ratio) ** 2
        il = 10.0 ** (-self.insertion_loss_dB / 10.0)
        return g * il

    @property
    def noise_figure_linear(self) -> float:
        t_ref = 290.0
        loss = 1.0 / self.gain_linear
        return 1.0 + (self.temperature_K / t_ref) * (loss - 1.0)

    @property
    def bandwidth_Hz(self) -> float:
        return self.bandwidth_Hz_val


@dataclass
class CryoFeedthrough(Component):
    """SMA feedthrough from 4K to room temperature.

    The signal passes through a hermetic SMA connector that bridges
    the cryostat wall.  Thermal gradient: 4K inside to 300K outside.
    """
    name: str = "Cryo Feedthrough (4K->300K)"
    insertion_loss_dB: float = 0.5      # 0.5 dB typical
    impedance_ohm: float = 50.0        # 50 ohm SMA
    temperature_out_K: float = 300.0    # Exit temperature
    bandwidth_Hz_val: float = 18.0e9   # SMA good to 18 GHz

    def propagate(self, signal: SignalState) -> SignalState:
        """Propagate signal through the feedthrough."""
        il_linear = 10.0 ** (-self.insertion_loss_dB / 20.0)

        bw = min(signal.bandwidth_Hz, self.bandwidth_Hz_val)

        # Noise contribution: model as lossy element at average temperature
        # The feedthrough spans a thermal gradient; use average T for noise
        t_avg = (signal.temperature_K + self.temperature_out_K) / 2.0
        # Equivalent noise resistance from the insertion loss
        loss_power = 10.0 ** (self.insertion_loss_dB / 10.0)
        r_equiv = self.impedance_ohm * (loss_power - 1.0)
        if r_equiv > 0:
            noise_power_added = 4.0 * K_BOLTZMANN * t_avg * bw * r_equiv
            noise_current_added = math.sqrt(noise_power_added) / self.impedance_ohm
        else:
            noise_current_added = 0.0

        noise_out = math.sqrt((signal.noise_A * il_linear) ** 2 + noise_current_added ** 2)

        return SignalState(
            amplitude_A=signal.amplitude_A * il_linear,
            noise_A=noise_out,
            bandwidth_Hz=bw,
            temperature_K=self.temperature_out_K,
            impedance_ohm=self.impedance_ohm,
        )

    @property
    def gain_linear(self) -> float:
        return 10.0 ** (-self.insertion_loss_dB / 10.0)

    @property
    def noise_figure_linear(self) -> float:
        # Feedthrough at average temperature
        t_avg = (4.2 + self.temperature_out_K) / 2.0
        t_ref = 290.0
        loss = 10.0 ** (self.insertion_loss_dB / 10.0)
        return 1.0 + (t_avg / t_ref) * (loss - 1.0)

    @property
    def bandwidth_Hz(self) -> float:
        return self.bandwidth_Hz_val


@dataclass
class CoaxCable(Component):
    """Coaxial cable from cryostat to room-temperature instruments.

    Standard room-temperature semi-rigid or flexible coax.
    """
    name: str = "Coax Cable (300K)"
    length_m: float = 1.0               # 1 meter
    attenuation_dB_per_m_per_GHz: float = 0.5  # Typical semi-rigid
    impedance_ohm: float = 50.0         # 50 ohm
    temperature_K: float = 300.0
    bandwidth_Hz_val: float = 18.0e9   # Limited by connectors, not cable

    def _attenuation_dB(self, freq_GHz: float) -> float:
        """Total cable attenuation at a given frequency.

        Attenuation in coax scales as sqrt(f) for skin-effect dominated
        loss, but we use a linear approximation over the operating range.
        """
        return self.attenuation_dB_per_m_per_GHz * self.length_m * freq_GHz

    def propagate(self, signal: SignalState) -> SignalState:
        """Propagate signal through the coax cable."""
        # Use 1 GHz as representative frequency for broadband signal
        freq_GHz = min(signal.bandwidth_Hz / 1e9, 10.0)
        if freq_GHz < 0.001:
            freq_GHz = 0.001
        loss_dB = self._attenuation_dB(freq_GHz)
        loss_linear = 10.0 ** (-loss_dB / 20.0)

        bw = min(signal.bandwidth_Hz, self.bandwidth_Hz_val)

        # Noise from cable at room temperature
        loss_power = 10.0 ** (loss_dB / 10.0)
        r_equiv = self.impedance_ohm * (loss_power - 1.0)
        if r_equiv > 0:
            noise_power_added = 4.0 * K_BOLTZMANN * self.temperature_K * bw * r_equiv
            noise_current_added = math.sqrt(noise_power_added) / self.impedance_ohm
        else:
            noise_current_added = 0.0

        noise_out = math.sqrt((signal.noise_A * loss_linear) ** 2 + noise_current_added ** 2)

        return SignalState(
            amplitude_A=signal.amplitude_A * loss_linear,
            noise_A=noise_out,
            bandwidth_Hz=bw,
            temperature_K=self.temperature_K,
            impedance_ohm=self.impedance_ohm,
        )

    @property
    def gain_linear(self) -> float:
        loss_dB = self._attenuation_dB(1.0)  # at 1 GHz
        return 10.0 ** (-loss_dB / 10.0)

    @property
    def noise_figure_linear(self) -> float:
        t_ref = 290.0
        loss = 1.0 / self.gain_linear
        return 1.0 + (self.temperature_K / t_ref) * (loss - 1.0)

    @property
    def bandwidth_Hz(self) -> float:
        return self.bandwidth_Hz_val


@dataclass
class RoomTempAmplifier(Component):
    """Room temperature low-noise amplifier.

    Typical: Stanford Research SRS-560 or similar LNA.
    """
    name: str = "Room Temp Amplifier"
    gain_dB: float = 60.0               # 60 dB = 1000x voltage gain
    noise_figure_dB_val: float = 2.0    # 2 dB noise figure
    bandwidth_Hz_val: float = 1.0e9     # 1 GHz bandwidth
    input_impedance_ohm: float = 50.0   # 50 ohm input

    def propagate(self, signal: SignalState) -> SignalState:
        """Propagate signal through the amplifier."""
        gain_voltage = 10.0 ** (self.gain_dB / 20.0)

        bw = min(signal.bandwidth_Hz, self.bandwidth_Hz_val)

        # Amplifier noise: from noise figure
        # NF = (SNR_in / SNR_out), so noise added such that
        # output noise = gain * sqrt(input_noise^2 + added_noise^2)
        # where NF = 1 + added_noise^2 / input_noise_ref^2
        nf_linear = 10.0 ** (self.noise_figure_dB_val / 10.0)
        # Reference input noise (thermal at 290K into input impedance)
        ref_noise_power = K_BOLTZMANN * 290.0 * bw  # per unit resistance
        ref_noise_current = math.sqrt(4.0 * ref_noise_power / self.input_impedance_ohm)
        # Added noise current (referred to input)
        added_noise_current = ref_noise_current * math.sqrt(nf_linear - 1.0)

        # Total output noise: gain * sqrt(input^2 + added^2)
        input_noise = signal.noise_A
        total_input_noise = math.sqrt(input_noise ** 2 + added_noise_current ** 2)
        output_noise = total_input_noise * gain_voltage

        return SignalState(
            amplitude_A=signal.amplitude_A * gain_voltage,
            noise_A=output_noise,
            bandwidth_Hz=bw,
            temperature_K=300.0,
            impedance_ohm=self.input_impedance_ohm,
        )

    @property
    def gain_linear(self) -> float:
        return 10.0 ** (self.gain_dB / 10.0)  # power gain

    @property
    def noise_figure_linear(self) -> float:
        return 10.0 ** (self.noise_figure_dB_val / 10.0)

    @property
    def bandwidth_Hz(self) -> float:
        return self.bandwidth_Hz_val


# ---------------------------------------------------------------------------
# Signal chain analysis
# ---------------------------------------------------------------------------

@dataclass
class SignalChain:
    """Cascade of components from AQFP output to measurement equipment."""

    components: List[Component] = field(default_factory=list)

    def propagate(self, initial: SignalState | None = None) -> List[SignalState]:
        """Propagate signal through all components.

        Returns signal state after each component.  The first entry
        is the state after the first component (which for AQFPOutput
        is the generated signal).

        Parameters
        ----------
        initial : SignalState or None
            If None, the first component must be an AQFPOutput that
            generates the initial signal.  Otherwise, this signal is
            fed into the first component.
        """
        states: List[SignalState] = []
        if initial is None:
            # Use a dummy input for the AQFPOutput source
            initial = SignalState(
                amplitude_A=0.0, noise_A=0.0, bandwidth_Hz=float("inf"),
                temperature_K=4.2, impedance_ohm=50.0,
            )

        signal = initial
        for component in self.components:
            signal = component.propagate(signal)
            states.append(signal)
        return states

    def snr_at_each_stage(self) -> List[Tuple[str, float]]:
        """SNR in dB at each point in the chain.

        Returns list of (component_name, snr_dB) tuples.
        """
        states = self.propagate()
        return [
            (comp.name, state.snr_dB)
            for comp, state in zip(self.components, states)
        ]

    def total_noise_figure(self) -> float:
        """Cascaded noise figure using Friis formula.

        F_total = F1 + (F2-1)/G1 + (F3-1)/(G1*G2) + ...

        Returns noise figure in dB.
        """
        if not self.components:
            return 0.0

        # Skip the source (AQFPOutput) for Friis -- start from component index 1
        cascade_components = self.components[1:] if isinstance(self.components[0], AQFPOutput) else self.components

        if not cascade_components:
            return 0.0

        f_total = cascade_components[0].noise_figure_linear
        cumulative_gain = cascade_components[0].gain_linear

        for comp in cascade_components[1:]:
            nf = comp.noise_figure_linear
            if cumulative_gain > 0:
                f_total += (nf - 1.0) / cumulative_gain
            cumulative_gain *= comp.gain_linear

        if f_total <= 0:
            return float("-inf")
        return 10.0 * math.log10(f_total)

    def bandwidth_bottleneck(self) -> Tuple[str, float]:
        """Identify the component limiting overall bandwidth.

        Returns (component_name, bandwidth_Hz) of the narrowest component.
        """
        if not self.components:
            return ("(none)", float("inf"))

        min_bw = float("inf")
        bottleneck_name = "(none)"
        for comp in self.components:
            bw = comp.bandwidth_Hz
            if bw < min_bw:
                min_bw = bw
                bottleneck_name = comp.name

        return (bottleneck_name, min_bw)

    def sweep_aqfp_amplitude(
        self,
        range_A: List[float] | None = None,
    ) -> dict:
        """Sweep AQFP output amplitude, compute SNR vs amplitude.

        Parameters
        ----------
        range_A : list of float or None
            AQFP output current amplitudes to sweep.  If None, uses
            a default logarithmic sweep from 0.1 uA to 100 uA.

        Returns
        -------
        dict with keys:
            "amplitudes_A": list of input amplitudes
            "snr_dB_final": list of final-stage SNR for each amplitude
            "snr_dB_all": list of lists, SNR at every stage for each amplitude
        """
        if range_A is None:
            # Default: 0.1 uA to 100 uA, 20 points logarithmic
            range_A = [10 ** x for x in _linspace(-7, -4, 20)]

        snr_final: List[float] = []
        snr_all: List[List[float]] = []

        for amp in range_A:
            # Modify the AQFP source amplitude
            chain_copy = self._with_aqfp_amplitude(amp)
            states = chain_copy.propagate()
            if states:
                snr_final.append(states[-1].snr_dB)
                snr_all.append([s.snr_dB for s in states])
            else:
                snr_final.append(float("-inf"))
                snr_all.append([])

        return {
            "amplitudes_A": range_A,
            "snr_dB_final": snr_final,
            "snr_dB_all": snr_all,
        }

    def minimum_detectable_signal(self, target_snr_dB: float = 10.0) -> float:
        """Minimum AQFP output current for a target SNR at the final stage.

        Uses bisection search over AQFP amplitude.

        Parameters
        ----------
        target_snr_dB : float
            Target SNR in dB at the final measurement stage.

        Returns
        -------
        float
            Minimum AQFP output current in amperes.
        """
        # Bisection between 1e-12 A (1 pA) and 1e-3 A (1 mA)
        lo = 1e-12
        hi = 1e-3

        for _ in range(80):  # ~80 iterations gives ~1e-24 precision
            mid = math.sqrt(lo * hi)  # geometric midpoint for log scale
            chain = self._with_aqfp_amplitude(mid)
            states = chain.propagate()
            if not states:
                return float("inf")
            snr = states[-1].snr_dB
            if snr < target_snr_dB:
                lo = mid
            else:
                hi = mid

        return math.sqrt(lo * hi)

    def to_table(self) -> str:
        """Formatted table showing signal at each stage."""
        states = self.propagate()
        lines: List[str] = []
        lines.append("=" * 100)
        lines.append("SIGNAL CHAIN ANALYSIS")
        lines.append("=" * 100)
        lines.append("")

        header = (
            f"  {'Component':<28s}  {'I_sig':>10s}  {'I_noise':>10s}  "
            f"{'SNR(dB)':>8s}  {'BW':>10s}  {'T(K)':>6s}  {'Z(ohm)':>8s}"
        )
        lines.append(header)
        sep = (
            f"  {'-'*28}  {'-'*10}  {'-'*10}  "
            f"{'-'*8}  {'-'*10}  {'-'*6}  {'-'*8}"
        )
        lines.append(sep)

        for comp, state in zip(self.components, states):
            lines.append(
                f"  {comp.name:<28s}  {_fmt_current(state.amplitude_A):>10s}  "
                f"{_fmt_current(state.noise_A):>10s}  "
                f"{state.snr_dB:>8.1f}  {_fmt_freq(state.bandwidth_Hz):>10s}  "
                f"{state.temperature_K:>6.1f}  {state.impedance_ohm:>8.1f}"
            )

        lines.append(sep)

        # Summary
        lines.append("")
        bottleneck_name, bottleneck_bw = self.bandwidth_bottleneck()
        nf = self.total_noise_figure()
        mds = self.minimum_detectable_signal()

        lines.append(f"  Cascaded noise figure:       {nf:.2f} dB")
        lines.append(f"  Bandwidth bottleneck:        {bottleneck_name} ({_fmt_freq(bottleneck_bw)})")
        lines.append(f"  Min detectable signal (10dB): {_fmt_current(mds)}")
        lines.append(f"  Nominal AQFP output:         {_fmt_current(self.components[0].signal_current_A if isinstance(self.components[0], AQFPOutput) else 0)}")

        if isinstance(self.components[0], AQFPOutput):
            margin_dB = states[-1].snr_dB - 10.0
            lines.append(f"  SNR margin over 10 dB:       {margin_dB:.1f} dB")

        lines.append("")
        lines.append("=" * 100)
        return "\n".join(lines)

    def _with_aqfp_amplitude(self, amplitude_A: float) -> "SignalChain":
        """Return a copy of this chain with a modified AQFP amplitude."""
        import copy
        chain = copy.deepcopy(self)
        for comp in chain.components:
            if isinstance(comp, AQFPOutput):
                comp.signal_current_A = amplitude_A
                break
        return chain


# ---------------------------------------------------------------------------
# Default chain configuration
# ---------------------------------------------------------------------------

def default_chain() -> SignalChain:
    """Build the default signal chain matching the cryo-rack architecture.

    Configuration based on:
    - CONTEXT.md: ground isolation, optical I/O architecture
    - thermal_inputs.yaml: Pyralux AP 8541, SS304 coax
    - system-architecture.md: signal path description
    """
    return SignalChain(components=[
        AQFPOutput(
            signal_current_A=10.0e-6,    # 10 uA typical
            output_impedance_ohm=5.0,    # Few ohm
            temperature_K=4.2,
            bandwidth_Hz_val=5.0e9,      # 5 GHz AC clock
        ),
        Wirebond(
            length_mm=2.0,               # 2 mm gold wirebond
            diameter_um=25.0,            # 1 mil standard
            material="Au",
            temperature_K=4.2,
        ),
        PCBTrace(
            length_mm=20.0,              # 20 mm Pyralux trace
            width_um=100.0,
            substrate_thickness_um=100.0,  # 4 mil polyimide
            copper_thickness_um=17.5,    # 1/2 oz copper
            temperature_K=4.2,
            impedance_target_ohm=50.0,
            epsilon_r=3.4,               # Pyralux polyimide
            copper_rrr=50.0,
        ),
        IsolationTransformer(
            turns_ratio=1.0,
            coupling_coefficient=0.95,
            bandwidth_Hz_val=10.0e9,
            insertion_loss_dB=0.5,
            temperature_K=4.2,
        ),
        CryoFeedthrough(
            insertion_loss_dB=0.5,
            impedance_ohm=50.0,
            temperature_out_K=300.0,
            bandwidth_Hz_val=18.0e9,
        ),
        CoaxCable(
            length_m=1.0,
            attenuation_dB_per_m_per_GHz=0.5,
            impedance_ohm=50.0,
            temperature_K=300.0,
            bandwidth_Hz_val=18.0e9,
        ),
        RoomTempAmplifier(
            gain_dB=60.0,               # 60 dB = 1000x
            noise_figure_dB_val=2.0,    # 2 dB NF
            bandwidth_Hz_val=1.0e9,     # 1 GHz
            input_impedance_ohm=50.0,
        ),
    ])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _linspace(start: float, stop: float, n: int) -> List[float]:
    """Generate n evenly spaced values from start to stop (inclusive)."""
    if n <= 1:
        return [start]
    step = (stop - start) / (n - 1)
    return [start + i * step for i in range(n)]


def _fmt_current(i: float) -> str:
    """Format current with appropriate unit prefix."""
    if i == 0:
        return "0"
    ai = abs(i)
    if ai < 1e-12:
        return f"{i*1e15:.2f} fA"
    if ai < 1e-9:
        return f"{i*1e12:.2f} pA"
    if ai < 1e-6:
        return f"{i*1e9:.2f} nA"
    if ai < 1e-3:
        return f"{i*1e6:.2f} uA"
    if ai < 1.0:
        return f"{i*1e3:.2f} mA"
    return f"{i:.3f} A"


def _fmt_freq(f: float) -> str:
    """Format frequency with appropriate unit prefix."""
    if f == float("inf"):
        return "inf"
    if f >= 1e9:
        return f"{f/1e9:.1f} GHz"
    if f >= 1e6:
        return f"{f/1e6:.1f} MHz"
    if f >= 1e3:
        return f"{f/1e3:.1f} kHz"
    return f"{f:.1f} Hz"


def chain_to_dict(chain: SignalChain) -> dict[str, Any]:
    """Convert chain analysis result to a JSON-serializable dict."""
    states = chain.propagate()
    bottleneck_name, bottleneck_bw = chain.bandwidth_bottleneck()
    mds = chain.minimum_detectable_signal()

    stages = []
    for comp, state in zip(chain.components, states):
        stages.append({
            "component": comp.name,
            "amplitude_A": state.amplitude_A,
            "noise_A": state.noise_A,
            "snr_dB": state.snr_dB,
            "bandwidth_Hz": state.bandwidth_Hz,
            "temperature_K": state.temperature_K,
            "impedance_ohm": state.impedance_ohm,
        })

    return {
        "stages": stages,
        "summary": {
            "cascaded_noise_figure_dB": chain.total_noise_figure(),
            "bandwidth_bottleneck": bottleneck_name,
            "bandwidth_bottleneck_Hz": bottleneck_bw,
            "minimum_detectable_signal_A": mds,
            "final_snr_dB": states[-1].snr_dB if states else None,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Signal chain analysis: AQFP chip output to room-temperature "
            "measurement equipment.  Computes signal, noise, SNR, and "
            "bandwidth at each stage of the measurement chain."
        ),
    )
    parser.add_argument(
        "--json", "-j", action="store_true",
        help="Output machine-readable JSON instead of text table",
    )
    parser.add_argument(
        "--sweep", "-s", action="store_true",
        help="Sweep AQFP output amplitude and print SNR vs amplitude",
    )
    parser.add_argument(
        "--aqfp-current", type=float, default=None,
        help="AQFP output current in amperes (default: 10e-6 = 10 uA)",
    )
    args = parser.parse_args()

    chain = default_chain()

    if args.aqfp_current is not None:
        for comp in chain.components:
            if isinstance(comp, AQFPOutput):
                comp.signal_current_A = args.aqfp_current
                break

    if args.sweep:
        result = chain.sweep_aqfp_amplitude()
        if args.json:
            out = {
                "amplitudes_A": result["amplitudes_A"],
                "snr_dB_final": result["snr_dB_final"],
            }
            print(json.dumps(out, indent=2))
        else:
            print("AQFP Output Amplitude Sweep: SNR at Final Stage")
            print("=" * 50)
            print(f"  {'Amplitude':>12s}  {'SNR (dB)':>10s}")
            print(f"  {'-'*12}  {'-'*10}")
            for amp, snr in zip(result["amplitudes_A"], result["snr_dB_final"]):
                print(f"  {_fmt_current(amp):>12s}  {snr:>10.1f}")
        return

    if args.json:
        print(json.dumps(chain_to_dict(chain), indent=2))
    else:
        print(chain.to_table())


if __name__ == "__main__":
    main()
