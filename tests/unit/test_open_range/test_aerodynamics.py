# ABOUTME: Unit tests for the aerodynamics module.
# ABOUTME: Tests Reynolds number, drag coefficient, lift coefficient, and air density calculations.
"""Tests for aerodynamics calculations."""

from __future__ import annotations

import pytest

from gc2_connect.open_range.physics.aerodynamics import (
    calculate_air_density,
    calculate_reynolds,
    get_drag_coefficient,
    get_lift_coefficient,
)
from gc2_connect.open_range.physics.constants import (
    BALL_DIAMETER_M,
    CD_HIGH,
    CD_LOW,
    CL_MAX,
    KINEMATIC_VISCOSITY,
    STD_AIR_DENSITY,
)


class TestReynoldsNumber:
    """Tests for Reynolds number calculation."""

    def test_reynolds_at_zero_velocity(self) -> None:
        """Reynolds number should be 0 at zero velocity."""
        re = calculate_reynolds(velocity_ms=0.0, air_density=STD_AIR_DENSITY)
        assert re == 0.0

    def test_reynolds_at_low_speed(self) -> None:
        """Test Reynolds at low speed (35.8 m/s = 80 mph)."""
        # Re = V × D / ν = 35.8 × 0.04267 / 1.5e-5 ≈ 1.02×10^5
        velocity_ms = 35.8  # 80 mph
        re = calculate_reynolds(velocity_ms=velocity_ms, air_density=STD_AIR_DENSITY)
        expected = (velocity_ms * BALL_DIAMETER_M) / KINEMATIC_VISCOSITY
        assert re == pytest.approx(expected, rel=1e-6)
        # Should be around 1.0×10^5 (transition region)
        assert 0.9e5 < re < 1.1e5

    def test_reynolds_at_high_speed(self) -> None:
        """Test Reynolds at high speed (71.5 m/s = 160 mph)."""
        # Re = V × D / ν = 71.5 × 0.04267 / 1.5e-5 ≈ 2.03×10^5
        velocity_ms = 71.5  # 160 mph
        re = calculate_reynolds(velocity_ms=velocity_ms, air_density=STD_AIR_DENSITY)
        # Should be around 2.0×10^5 (turbulent regime)
        assert 1.9e5 < re < 2.2e5

    def test_reynolds_formula(self) -> None:
        """Verify Reynolds formula: Re = V × D / ν."""
        velocity_ms = 50.0
        expected = (velocity_ms * BALL_DIAMETER_M) / KINEMATIC_VISCOSITY
        re = calculate_reynolds(velocity_ms=velocity_ms, air_density=STD_AIR_DENSITY)
        assert re == pytest.approx(expected, rel=1e-6)


class TestDragCoefficient:
    """Tests for drag coefficient calculation."""

    def test_cd_at_low_reynolds(self) -> None:
        """Cd should be ~0.5 at low Reynolds number."""
        # Re < 0.5×10^5
        reynolds = 0.3e5
        cd = get_drag_coefficient(reynolds=reynolds)
        assert cd == pytest.approx(CD_LOW, rel=1e-6)

    def test_cd_at_high_reynolds(self) -> None:
        """Cd should be ~0.21 at high Reynolds number."""
        # Re > 1.0×10^5
        reynolds = 1.5e5
        cd = get_drag_coefficient(reynolds=reynolds)
        assert cd == pytest.approx(CD_HIGH, rel=1e-6)

    def test_cd_in_transition_region(self) -> None:
        """Cd should interpolate in the transition region."""
        # Re = 0.75×10^5 (middle of transition)
        reynolds = 0.75e5
        cd = get_drag_coefficient(reynolds=reynolds)
        # Should be between CD_LOW and CD_HIGH
        assert CD_HIGH < cd < CD_LOW
        # Midpoint should be approximately (0.5 + 0.212) / 2 = 0.356
        expected_mid = (CD_LOW + CD_HIGH) / 2.0
        assert cd == pytest.approx(expected_mid, rel=0.01)

    def test_cd_at_transition_boundary_low(self) -> None:
        """Cd should be CD_LOW at lower boundary of transition."""
        reynolds = 0.5e5  # Exactly at RE_LOW
        cd = get_drag_coefficient(reynolds=reynolds)
        assert cd == pytest.approx(CD_LOW, rel=1e-6)

    def test_cd_at_transition_boundary_high(self) -> None:
        """Cd should be CD_HIGH at upper boundary of transition."""
        reynolds = 1.0e5  # Exactly at RE_HIGH
        cd = get_drag_coefficient(reynolds=reynolds)
        assert cd == pytest.approx(CD_HIGH, rel=1e-6)

    def test_cd_with_spin_term(self) -> None:
        """Cd should include spin-dependent term."""
        reynolds = 1.5e5  # High Re for base CD_HIGH
        spin_factor = 0.2
        cd = get_drag_coefficient(reynolds=reynolds, spin_factor=spin_factor)
        # Cd = CD_HIGH + CD_SPIN × spin_factor = 0.212 + 0.15 × 0.2 = 0.242
        expected = CD_HIGH + 0.15 * spin_factor
        assert cd == pytest.approx(expected, rel=1e-6)

    def test_cd_spin_zero_has_no_effect(self) -> None:
        """Spin factor of 0 should not add to drag."""
        reynolds = 1.0e5
        cd_no_spin = get_drag_coefficient(reynolds=reynolds, spin_factor=0.0)
        cd_with_zero = get_drag_coefficient(reynolds=reynolds)
        assert cd_no_spin == cd_with_zero


class TestLiftCoefficient:
    """Tests for lift coefficient calculation."""

    def test_cl_at_zero_spin(self) -> None:
        """Cl should be 0 at zero spin factor."""
        cl = get_lift_coefficient(spin_factor=0.0)
        assert cl == 0.0

    def test_cl_at_negative_spin(self) -> None:
        """Cl should be 0 for negative spin factor."""
        cl = get_lift_coefficient(spin_factor=-0.1)
        assert cl == 0.0

    def test_cl_quadratic_formula(self) -> None:
        """Test quadratic formula: Cl = 1.990×S - 3.250×S²."""
        spin_factor = 0.15
        expected = 1.990 * spin_factor - 3.250 * spin_factor * spin_factor
        cl = get_lift_coefficient(spin_factor=spin_factor)
        assert cl == pytest.approx(expected, rel=1e-6)

    def test_cl_at_typical_values(self) -> None:
        """Test Cl at typical spin factors."""
        # S = 0.1: Cl = 1.990×0.1 - 3.250×0.01 = 0.199 - 0.0325 = 0.1665
        cl_01 = get_lift_coefficient(spin_factor=0.1)
        assert cl_01 == pytest.approx(0.1665, rel=1e-3)

        # S = 0.2: Cl = 1.990×0.2 - 3.250×0.04 = 0.398 - 0.130 = 0.268
        cl_02 = get_lift_coefficient(spin_factor=0.2)
        assert cl_02 == pytest.approx(0.268, rel=1e-3)

    def test_cl_max_at_threshold(self) -> None:
        """Cl should be capped at CL_MAX (0.305) above threshold."""
        cl = get_lift_coefficient(spin_factor=0.30)
        assert cl == pytest.approx(CL_MAX, rel=1e-6)

    def test_cl_capped_above_threshold(self) -> None:
        """Cl should remain at CL_MAX above threshold spin factor."""
        cl = get_lift_coefficient(spin_factor=0.40)
        assert cl == pytest.approx(CL_MAX, rel=1e-6)

        cl_high = get_lift_coefficient(spin_factor=0.50)
        assert cl_high == pytest.approx(CL_MAX, rel=1e-6)

    def test_cl_increases_with_spin(self) -> None:
        """Cl should increase with spin factor up to threshold."""
        cl_01 = get_lift_coefficient(spin_factor=0.1)
        cl_02 = get_lift_coefficient(spin_factor=0.2)
        assert cl_02 > cl_01


class TestAirDensity:
    """Tests for air density calculation."""

    def test_standard_conditions(self) -> None:
        """Air density at standard conditions should be ~1.194 kg/m³."""
        density = calculate_air_density(
            temp_f=70.0,
            elevation_ft=0.0,
            humidity_pct=50.0,
        )
        assert density == pytest.approx(STD_AIR_DENSITY, rel=0.01)

    def test_denver_elevation(self) -> None:
        """Air density at Denver (5280 ft) should be lower."""
        std_density = calculate_air_density(temp_f=70.0, elevation_ft=0.0, humidity_pct=50.0)
        denver_density = calculate_air_density(temp_f=70.0, elevation_ft=5280.0, humidity_pct=50.0)

        # Denver should have lower air density
        assert denver_density < std_density
        # Roughly 83% of sea level density
        assert denver_density == pytest.approx(std_density * 0.83, rel=0.03)

    def test_high_temperature_lower_density(self) -> None:
        """Higher temperature should result in lower air density."""
        density_70f = calculate_air_density(temp_f=70.0, elevation_ft=0.0, humidity_pct=50.0)
        density_100f = calculate_air_density(temp_f=100.0, elevation_ft=0.0, humidity_pct=50.0)

        assert density_100f < density_70f

    def test_low_temperature_higher_density(self) -> None:
        """Lower temperature should result in higher air density."""
        density_70f = calculate_air_density(temp_f=70.0, elevation_ft=0.0, humidity_pct=50.0)
        density_40f = calculate_air_density(temp_f=40.0, elevation_ft=0.0, humidity_pct=50.0)

        assert density_40f > density_70f

    def test_higher_humidity_lower_density(self) -> None:
        """Higher humidity should result in slightly lower air density.

        Water vapor is lighter than air (molecular weight 18 vs 29).
        """
        density_dry = calculate_air_density(temp_f=70.0, elevation_ft=0.0, humidity_pct=0.0)
        density_humid = calculate_air_density(temp_f=70.0, elevation_ft=0.0, humidity_pct=100.0)

        # Humid air is slightly less dense
        assert density_humid < density_dry

    def test_custom_pressure(self) -> None:
        """Test with custom barometric pressure."""
        density_std = calculate_air_density(
            temp_f=70.0, elevation_ft=0.0, humidity_pct=50.0, pressure_inhg=29.92
        )
        density_low = calculate_air_density(
            temp_f=70.0, elevation_ft=0.0, humidity_pct=50.0, pressure_inhg=29.00
        )

        # Lower pressure = lower density
        assert density_low < density_std

    def test_reasonable_range(self) -> None:
        """Air density should be in reasonable range for all conditions."""
        # Cold, sea level, dry - should be near upper bound
        density_cold = calculate_air_density(temp_f=32.0, elevation_ft=0.0, humidity_pct=0.0)
        assert 1.2 < density_cold < 1.4

        # Hot, high elevation, humid - should be near lower bound
        # 10,000 ft elevation is quite extreme (over 3000m, similar to high mountain)
        # Air density at that altitude can be quite low
        density_hot = calculate_air_density(temp_f=100.0, elevation_ft=10000.0, humidity_pct=100.0)
        assert 0.7 < density_hot < 1.0
