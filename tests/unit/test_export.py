# ABOUTME: Unit tests for the CSV export functionality.
# ABOUTME: Tests export_to_csv function with various shot data scenarios.
"""Tests for the CSV export module."""

import csv
from datetime import datetime
from pathlib import Path

from gc2_connect.models import GC2ShotData
from gc2_connect.services.export import export_to_csv, generate_export_filename


class TestGenerateExportFilename:
    """Tests for the generate_export_filename function."""

    def test_default_filename_format(self) -> None:
        """Test that default filename follows expected format."""
        filename = generate_export_filename()
        assert filename.startswith("gc2_session_")
        assert filename.endswith(".csv")

    def test_filename_contains_timestamp(self) -> None:
        """Test that filename contains a timestamp."""
        filename = generate_export_filename()
        # Extract timestamp part (gc2_session_YYYYMMDD_HHMMSS.csv)
        timestamp_part = filename.replace("gc2_session_", "").replace(".csv", "")
        # Should have format YYYYMMDD_HHMMSS
        assert len(timestamp_part) == 15  # 8 + 1 + 6
        assert "_" in timestamp_part


class TestExportToCsv:
    """Tests for the export_to_csv function."""

    def test_export_empty_shots_creates_file_with_headers(self, tmp_path: Path) -> None:
        """Test that exporting with no shots creates a file with headers only."""
        filepath = tmp_path / "empty.csv"
        shots: list[GC2ShotData] = []

        export_to_csv(shots, filepath)

        assert filepath.exists()
        with open(filepath) as f:
            reader = csv.reader(f)
            rows = list(reader)
            # Should have exactly one row (headers)
            assert len(rows) == 1
            # Check expected headers are present
            headers = rows[0]
            assert "Shot #" in headers
            assert "Timestamp" in headers
            assert "Ball Speed (mph)" in headers
            assert "Launch Angle (°)" in headers
            assert "Total Spin (RPM)" in headers

    def test_export_ball_only_shots(self, tmp_path: Path) -> None:
        """Test exporting shots with ball data only (no HMT)."""
        filepath = tmp_path / "ball_only.csv"
        shot = GC2ShotData(
            shot_id=1,
            timestamp=datetime(2026, 1, 3, 10, 30, 0),
            ball_speed=145.2,
            launch_angle=11.8,
            horizontal_launch_angle=1.5,
            total_spin=2650,
            back_spin=2480,
            side_spin=-320,
        )

        export_to_csv([shot], filepath)

        assert filepath.exists()
        with open(filepath) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            row = rows[0]
            assert row["Shot #"] == "1"
            assert row["Ball Speed (mph)"] == "145.20"
            assert row["Launch Angle (°)"] == "11.80"
            assert row["H. Launch Angle (°)"] == "1.50"
            assert row["Total Spin (RPM)"] == "2650"
            assert row["Back Spin (RPM)"] == "2480"
            assert row["Side Spin (RPM)"] == "-320"
            # HMT columns should be empty
            assert row["Club Speed (mph)"] == ""
            assert row["Path (°)"] == ""

    def test_export_shots_with_hmt_data(self, tmp_path: Path) -> None:
        """Test exporting shots with HMT (club) data."""
        filepath = tmp_path / "with_hmt.csv"
        shot = GC2ShotData(
            shot_id=2,
            timestamp=datetime(2026, 1, 3, 10, 31, 0),
            ball_speed=150.5,
            launch_angle=12.3,
            horizontal_launch_angle=2.1,
            total_spin=2800,
            back_spin=2650,
            side_spin=-400,
            club_speed=105.2,
            swing_path=3.1,
            angle_of_attack=-4.2,
            face_to_target=1.5,
            lie=0.5,
            dynamic_loft=15.2,
            has_hmt=True,
        )

        export_to_csv([shot], filepath)

        assert filepath.exists()
        with open(filepath) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            row = rows[0]
            # Check club data
            assert row["Club Speed (mph)"] == "105.20"
            assert row["Path (°)"] == "3.10"
            assert row["Attack Angle (°)"] == "-4.20"
            assert row["Face to Target (°)"] == "1.50"
            assert row["Lie (°)"] == "0.50"
            assert row["Dynamic Loft (°)"] == "15.20"

    def test_export_multiple_shots(self, tmp_path: Path) -> None:
        """Test exporting multiple shots maintains correct order."""
        filepath = tmp_path / "multiple.csv"
        shots = [
            GC2ShotData(
                shot_id=1,
                timestamp=datetime(2026, 1, 3, 10, 30, 0),
                ball_speed=145.2,
                launch_angle=11.8,
                horizontal_launch_angle=1.5,
                total_spin=2650,
                back_spin=2480,
                side_spin=-320,
            ),
            GC2ShotData(
                shot_id=2,
                timestamp=datetime(2026, 1, 3, 10, 31, 0),
                ball_speed=150.0,
                launch_angle=12.0,
                horizontal_launch_angle=2.0,
                total_spin=2700,
                back_spin=2550,
                side_spin=-350,
            ),
            GC2ShotData(
                shot_id=3,
                timestamp=datetime(2026, 1, 3, 10, 32, 0),
                ball_speed=155.0,
                launch_angle=10.5,
                horizontal_launch_angle=-0.5,
                total_spin=2800,
                back_spin=2600,
                side_spin=-400,
            ),
        ]

        export_to_csv(shots, filepath)

        with open(filepath) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 3
            # Verify order matches input order
            assert rows[0]["Shot #"] == "1"
            assert rows[1]["Shot #"] == "2"
            assert rows[2]["Shot #"] == "3"

    def test_export_csv_is_valid_and_readable(self, tmp_path: Path) -> None:
        """Test that exported CSV is properly formatted and readable."""
        filepath = tmp_path / "valid.csv"
        shot = GC2ShotData(
            shot_id=1,
            timestamp=datetime(2026, 1, 3, 10, 30, 0),
            ball_speed=145.2,
            launch_angle=11.8,
            horizontal_launch_angle=1.5,
            total_spin=2650,
            back_spin=2480,
            side_spin=-320,
        )

        export_to_csv([shot], filepath)

        # Verify CSV can be read by standard csv module
        with open(filepath, newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)
            # Should have header + 1 data row
            assert len(rows) == 2
            # Each row should have the same number of columns
            assert len(rows[0]) == len(rows[1])

    def test_export_handles_spin_axis_calculation(self, tmp_path: Path) -> None:
        """Test that spin axis is correctly calculated and included."""
        filepath = tmp_path / "spin_axis.csv"
        shot = GC2ShotData(
            shot_id=1,
            timestamp=datetime(2026, 1, 3, 10, 30, 0),
            ball_speed=145.2,
            launch_angle=11.8,
            horizontal_launch_angle=1.5,
            total_spin=2650,
            back_spin=2480,
            side_spin=-320,
        )

        export_to_csv([shot], filepath)

        with open(filepath) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            row = rows[0]
            # spin_axis should be calculated and present
            assert "Spin Axis (°)" in row
            spin_axis = float(row["Spin Axis (°)"])
            # Expected value: atan2(-320, 2480) in degrees ≈ -7.36
            assert -8.0 < spin_axis < -7.0

    def test_export_string_filepath(self, tmp_path: Path) -> None:
        """Test that export works with string filepath."""
        filepath_str = str(tmp_path / "string_path.csv")
        shot = GC2ShotData(
            shot_id=1,
            timestamp=datetime(2026, 1, 3, 10, 30, 0),
            ball_speed=145.2,
            launch_angle=11.8,
            horizontal_launch_angle=1.5,
            total_spin=2650,
            back_spin=2480,
            side_spin=-320,
        )

        export_to_csv([shot], filepath_str)

        assert Path(filepath_str).exists()

    def test_export_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that export creates parent directories if they don't exist."""
        filepath = tmp_path / "subdir" / "nested" / "export.csv"
        shot = GC2ShotData(
            shot_id=1,
            timestamp=datetime(2026, 1, 3, 10, 30, 0),
            ball_speed=145.2,
            launch_angle=11.8,
            horizontal_launch_angle=1.5,
            total_spin=2650,
            back_spin=2480,
            side_spin=-320,
        )

        export_to_csv([shot], filepath)

        assert filepath.exists()

    def test_export_number_formatting(self, tmp_path: Path) -> None:
        """Test that numbers are formatted with appropriate decimal places."""
        filepath = tmp_path / "formatting.csv"
        shot = GC2ShotData(
            shot_id=1,
            timestamp=datetime(2026, 1, 3, 10, 30, 0),
            ball_speed=145.123456,  # Should be formatted to 2 decimal places
            launch_angle=11.876543,
            horizontal_launch_angle=1.5,
            total_spin=2650.789,  # Spin values should be integers
            back_spin=2480.123,
            side_spin=-320.456,
        )

        export_to_csv([shot], filepath)

        with open(filepath) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            row = rows[0]
            # Ball speed should have 2 decimal places
            assert row["Ball Speed (mph)"] == "145.12"
            # Spin should be integers
            assert row["Total Spin (RPM)"] == "2651"

    def test_export_timestamp_format(self, tmp_path: Path) -> None:
        """Test that timestamp is formatted correctly."""
        filepath = tmp_path / "timestamp.csv"
        shot = GC2ShotData(
            shot_id=1,
            timestamp=datetime(2026, 1, 3, 10, 30, 45),
            ball_speed=145.2,
            launch_angle=11.8,
            horizontal_launch_angle=1.5,
            total_spin=2650,
            back_spin=2480,
            side_spin=-320,
        )

        export_to_csv([shot], filepath)

        with open(filepath) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            row = rows[0]
            # Timestamp should be in ISO format or readable format
            timestamp_str = row["Timestamp"]
            assert "2026" in timestamp_str
            assert "10:30" in timestamp_str or "10-30" in timestamp_str

    def test_export_mixed_hmt_shots(self, tmp_path: Path) -> None:
        """Test exporting a mix of shots with and without HMT data."""
        filepath = tmp_path / "mixed.csv"
        shots = [
            GC2ShotData(
                shot_id=1,
                timestamp=datetime(2026, 1, 3, 10, 30, 0),
                ball_speed=145.2,
                launch_angle=11.8,
                horizontal_launch_angle=1.5,
                total_spin=2650,
                back_spin=2480,
                side_spin=-320,
                # No HMT data
            ),
            GC2ShotData(
                shot_id=2,
                timestamp=datetime(2026, 1, 3, 10, 31, 0),
                ball_speed=150.5,
                launch_angle=12.3,
                horizontal_launch_angle=2.1,
                total_spin=2800,
                back_spin=2650,
                side_spin=-400,
                club_speed=105.2,
                swing_path=3.1,
                has_hmt=True,
            ),
        ]

        export_to_csv(shots, filepath)

        with open(filepath) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            # First shot should have empty HMT columns
            assert rows[0]["Club Speed (mph)"] == ""
            # Second shot should have HMT data
            assert rows[1]["Club Speed (mph)"] == "105.20"
