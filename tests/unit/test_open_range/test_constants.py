# ABOUTME: Unit tests for Open Range physics constants.
# ABOUTME: Verifies ball properties, atmosphere, and surface values match docs/PHYSICS.md.
"""Tests for Open Range physics constants."""

from __future__ import annotations

import math

import pytest


class TestBallConstants:
    """Tests for golf ball physical properties."""

    def test_ball_mass_kg(self) -> None:
        """Test ball mass matches USGA specs (1.620 oz max = 0.04593 kg)."""
        from gc2_connect.open_range.physics.constants import BALL_MASS_KG

        assert pytest.approx(0.04593, rel=0.001) == BALL_MASS_KG

    def test_ball_diameter_m(self) -> None:
        """Test ball diameter matches USGA specs (1.680 inches min = 0.04267 m)."""
        from gc2_connect.open_range.physics.constants import BALL_DIAMETER_M

        assert pytest.approx(0.04267, rel=0.001) == BALL_DIAMETER_M

    def test_ball_radius_m(self) -> None:
        """Test ball radius is half of diameter."""
        from gc2_connect.open_range.physics.constants import (
            BALL_DIAMETER_M,
            BALL_RADIUS_M,
        )

        assert pytest.approx(BALL_DIAMETER_M / 2.0) == BALL_RADIUS_M
        assert pytest.approx(0.021335, rel=0.001) == BALL_RADIUS_M

    def test_ball_area_m2(self) -> None:
        """Test ball cross-sectional area calculation."""
        from gc2_connect.open_range.physics.constants import BALL_AREA_M2, BALL_RADIUS_M

        expected = math.pi * BALL_RADIUS_M * BALL_RADIUS_M
        assert pytest.approx(expected) == BALL_AREA_M2
        assert pytest.approx(0.001430, rel=0.01) == BALL_AREA_M2


class TestAtmosphereConstants:
    """Tests for standard atmosphere values."""

    def test_standard_temperature_f(self) -> None:
        """Test standard temperature is 70F."""
        from gc2_connect.open_range.physics.constants import STD_TEMP_F

        assert STD_TEMP_F == 70.0

    def test_standard_elevation_ft(self) -> None:
        """Test standard elevation is sea level."""
        from gc2_connect.open_range.physics.constants import STD_ELEVATION_FT

        assert STD_ELEVATION_FT == 0.0

    def test_standard_humidity_pct(self) -> None:
        """Test standard humidity is 50%."""
        from gc2_connect.open_range.physics.constants import STD_HUMIDITY_PCT

        assert STD_HUMIDITY_PCT == 50.0

    def test_standard_pressure_inhg(self) -> None:
        """Test standard pressure is 29.92 inHg."""
        from gc2_connect.open_range.physics.constants import STD_PRESSURE_INHG

        assert pytest.approx(29.92) == STD_PRESSURE_INHG

    def test_standard_air_density(self) -> None:
        """Test standard air density is ~1.194 kg/m3."""
        from gc2_connect.open_range.physics.constants import STD_AIR_DENSITY

        assert pytest.approx(1.194, rel=0.01) == STD_AIR_DENSITY


class TestPhysicsConstants:
    """Tests for general physics constants."""

    def test_gravity(self) -> None:
        """Test gravity is 9.81 m/s^2."""
        from gc2_connect.open_range.physics.constants import GRAVITY_MS2

        assert pytest.approx(9.81, rel=0.001) == GRAVITY_MS2

    def test_spin_decay_rate(self) -> None:
        """Test spin decay rate is 1% per second."""
        from gc2_connect.open_range.physics.constants import SPIN_DECAY_RATE

        assert pytest.approx(0.01) == SPIN_DECAY_RATE

    def test_kinematic_viscosity(self) -> None:
        """Test kinematic viscosity for Reynolds calculation."""
        from gc2_connect.open_range.physics.constants import KINEMATIC_VISCOSITY

        assert pytest.approx(1.5e-5, rel=0.01) == KINEMATIC_VISCOSITY


class TestAerodynamicCoefficients:
    """Tests for aerodynamic coefficient constants."""

    def test_cd_low(self) -> None:
        """Test low Reynolds drag coefficient."""
        from gc2_connect.open_range.physics.constants import CD_LOW

        assert pytest.approx(0.500) == CD_LOW

    def test_cd_high(self) -> None:
        """Test high Reynolds drag coefficient."""
        from gc2_connect.open_range.physics.constants import CD_HIGH

        assert pytest.approx(0.212) == CD_HIGH

    def test_cd_spin(self) -> None:
        """Test spin-dependent drag coefficient."""
        from gc2_connect.open_range.physics.constants import CD_SPIN

        assert pytest.approx(0.15) == CD_SPIN

    def test_reynolds_thresholds(self) -> None:
        """Test Reynolds number thresholds for drag crisis."""
        from gc2_connect.open_range.physics.constants import RE_HIGH, RE_LOW

        assert pytest.approx(0.5) == RE_LOW  # x10^5
        assert pytest.approx(1.0) == RE_HIGH  # x10^5

    def test_cl_linear(self) -> None:
        """Test lift coefficient linear term."""
        from gc2_connect.open_range.physics.constants import CL_LINEAR

        assert pytest.approx(1.990) == CL_LINEAR

    def test_cl_quadratic(self) -> None:
        """Test lift coefficient quadratic term."""
        from gc2_connect.open_range.physics.constants import CL_QUADRATIC

        assert pytest.approx(-3.250) == CL_QUADRATIC

    def test_cl_max(self) -> None:
        """Test maximum lift coefficient."""
        from gc2_connect.open_range.physics.constants import CL_MAX

        assert pytest.approx(0.305) == CL_MAX

    def test_cl_spin_threshold(self) -> None:
        """Test spin factor where Cl caps."""
        from gc2_connect.open_range.physics.constants import CL_SPIN_THRESHOLD

        assert pytest.approx(0.30) == CL_SPIN_THRESHOLD


class TestSimulationParameters:
    """Tests for simulation control parameters."""

    def test_dt(self) -> None:
        """Test time step is 0.01 seconds (10ms)."""
        from gc2_connect.open_range.physics.constants import DT

        assert pytest.approx(0.01) == DT

    def test_max_time(self) -> None:
        """Test max simulation time is 30 seconds."""
        from gc2_connect.open_range.physics.constants import MAX_TIME

        assert pytest.approx(30.0) == MAX_TIME

    def test_max_iterations(self) -> None:
        """Test safety limit on iterations."""
        from gc2_connect.open_range.physics.constants import MAX_ITERATIONS

        assert MAX_ITERATIONS == 3000

    def test_max_trajectory_points(self) -> None:
        """Test memory limit on trajectory points."""
        from gc2_connect.open_range.physics.constants import MAX_TRAJECTORY_POINTS

        assert MAX_TRAJECTORY_POINTS == 600

    def test_stopped_threshold(self) -> None:
        """Test velocity threshold for stopped detection."""
        from gc2_connect.open_range.physics.constants import STOPPED_THRESHOLD

        assert pytest.approx(0.1) == STOPPED_THRESHOLD

    def test_max_bounces(self) -> None:
        """Test maximum number of bounces."""
        from gc2_connect.open_range.physics.constants import MAX_BOUNCES

        assert MAX_BOUNCES == 5


class TestSurfaceProperties:
    """Tests for ground surface properties."""

    def test_surfaces_dict_exists(self) -> None:
        """Test SURFACES dictionary exists with expected keys."""
        from gc2_connect.open_range.physics.constants import SURFACES

        assert "Fairway" in SURFACES
        assert "Green" in SURFACES
        assert "Rough" in SURFACES

    def test_fairway_properties(self) -> None:
        """Test Fairway surface properties match docs/PHYSICS.md."""
        from gc2_connect.open_range.physics.constants import SURFACES

        fairway = SURFACES["Fairway"]
        assert fairway.name == "Fairway"
        assert fairway.cor == pytest.approx(0.60)
        assert fairway.rolling_resistance == pytest.approx(0.10)
        assert fairway.friction == pytest.approx(0.50)

    def test_green_properties(self) -> None:
        """Test Green surface properties match docs/PHYSICS.md."""
        from gc2_connect.open_range.physics.constants import SURFACES

        green = SURFACES["Green"]
        assert green.name == "Green"
        assert green.cor == pytest.approx(0.40)
        assert green.rolling_resistance == pytest.approx(0.05)
        assert green.friction == pytest.approx(0.30)

    def test_rough_properties(self) -> None:
        """Test Rough surface properties match docs/PHYSICS.md."""
        from gc2_connect.open_range.physics.constants import SURFACES

        rough = SURFACES["Rough"]
        assert rough.name == "Rough"
        assert rough.cor == pytest.approx(0.30)
        assert rough.rolling_resistance == pytest.approx(0.30)
        assert rough.friction == pytest.approx(0.70)

    def test_surface_structure(self) -> None:
        """Test that surface objects have correct structure."""
        from gc2_connect.open_range.physics.constants import SURFACES, GroundSurface

        for _name, surface in SURFACES.items():
            assert isinstance(surface, GroundSurface)
            assert hasattr(surface, "name")
            assert hasattr(surface, "cor")
            assert hasattr(surface, "rolling_resistance")
            assert hasattr(surface, "friction")
