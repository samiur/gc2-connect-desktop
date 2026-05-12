# ABOUTME: Integration tests for the full shot flow from GC2 to GSPro.
# ABOUTME: Tests data transformation, callback handling, and message delivery.
"""Integration tests for complete shot flow: MockGC2 -> App -> MockGSPro."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from gc2_connect.gc2.usb_reader import MockGC2Reader
from gc2_connect.gspro.client import GSProClient
from gc2_connect.models import GC2ShotData, GSProResponse

if TYPE_CHECKING:
    pass


def get_shot_messages(received_shots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter out heartbeat messages, returning only actual shot messages."""
    return [
        shot
        for shot in received_shots
        if not shot.get("ShotDataOptions", {}).get("IsHeartBeat", False)
    ]


class TestSingleShotFlow:
    """Test single shot flow from GC2 to GSPro."""

    def test_valid_shot_is_sent_to_gspro(
        self, mock_gspro_server, gspro_client: GSProClient, sample_gc2_shot: GC2ShotData
    ):
        """Test that a valid shot from GC2 is correctly sent to GSPro."""
        # Send shot through client
        response = gspro_client.send_shot(sample_gc2_shot)

        # Verify response
        assert response is not None
        assert response.is_success
        assert response.Code == 201  # Mock server returns 201 with player info

        # Verify server received the shot (filter out heartbeat)
        shot_messages = get_shot_messages(mock_gspro_server.received_shots)
        assert len(shot_messages) == 1
        received = shot_messages[0]

        # Verify shot data transformation
        assert received["DeviceID"] == "GC2 Connect"
        assert received["ShotNumber"] == 1
        assert received["BallData"]["Speed"] == sample_gc2_shot.ball_speed
        assert received["BallData"]["VLA"] == sample_gc2_shot.launch_angle
        assert received["BallData"]["HLA"] == sample_gc2_shot.horizontal_launch_angle
        assert received["BallData"]["TotalSpin"] == sample_gc2_shot.total_spin

    def test_shot_with_hmt_includes_club_data(
        self,
        mock_gspro_server,
        gspro_client: GSProClient,
        sample_gc2_shot_with_hmt: GC2ShotData,
    ):
        """Test that shots with HMT data include club data in GSPro message."""
        response = gspro_client.send_shot(sample_gc2_shot_with_hmt)

        assert response is not None
        assert response.is_success

        # Verify club data is included (filter out heartbeat)
        shot_messages = get_shot_messages(mock_gspro_server.received_shots)
        assert len(shot_messages) == 1
        received = shot_messages[0]

        assert received["ShotDataOptions"]["ContainsClubData"] is True
        assert received["ClubData"]["Speed"] == sample_gc2_shot_with_hmt.club_speed
        assert received["ClubData"]["Path"] == sample_gc2_shot_with_hmt.swing_path
        assert received["ClubData"]["AngleOfAttack"] == sample_gc2_shot_with_hmt.angle_of_attack
        assert received["ClubData"]["FaceToTarget"] == sample_gc2_shot_with_hmt.face_to_target

    def test_shot_number_increments(
        self, mock_gspro_server, gspro_client: GSProClient, sample_gc2_shot: GC2ShotData
    ):
        """Test that shot numbers increment correctly."""
        # Send multiple shots
        for expected_num in range(1, 4):
            response = gspro_client.send_shot(sample_gc2_shot)
            assert response is not None
            assert gspro_client.shot_number == expected_num

        # Verify shot numbers on server (filter out heartbeat)
        shot_messages = get_shot_messages(mock_gspro_server.received_shots)
        assert len(shot_messages) == 3
        for i, shot in enumerate(shot_messages, 1):
            assert shot["ShotNumber"] == i

    def test_spin_axis_calculated_correctly(
        self, mock_gspro_server, gspro_client: GSProClient, sample_gc2_shot: GC2ShotData
    ):
        """Test that spin axis is calculated from back/side spin."""
        response = gspro_client.send_shot(sample_gc2_shot)

        assert response is not None
        shot_messages = get_shot_messages(mock_gspro_server.received_shots)
        received = shot_messages[0]

        # Spin axis should match calculated value
        expected_spin_axis = sample_gc2_shot.spin_axis
        assert abs(received["BallData"]["SpinAxis"] - expected_spin_axis) < 0.01


class TestMultipleShotsFlow:
    """Test multiple shots in sequence."""

    def test_multiple_shots_sent_in_order(self, mock_gspro_server, gspro_client: GSProClient):
        """Test that multiple shots are sent and received in order."""
        shots = [
            GC2ShotData(
                shot_id=i,
                ball_speed=140 + i * 5,
                launch_angle=10 + i,
                total_spin=2500,
                back_spin=2400,
                side_spin=100,
            )
            for i in range(1, 6)
        ]

        for shot in shots:
            response = gspro_client.send_shot(shot)
            assert response is not None
            assert response.is_success

        # Verify all shots received (filter out heartbeat)
        shot_messages = get_shot_messages(mock_gspro_server.received_shots)
        assert len(shot_messages) == 5

        # Verify shots are in order by speed
        for i, received in enumerate(shot_messages):
            expected_speed = 140 + (i + 1) * 5
            assert received["BallData"]["Speed"] == expected_speed

    def test_shot_history_with_varying_data(self, mock_gspro_server, gspro_client: GSProClient):
        """Test sending shots with varying ball speeds, spins, and angles."""
        test_data = [
            {"speed": 100, "spin": 6000, "launch": 25, "hla": 0},  # Wedge
            {"speed": 140, "spin": 4000, "launch": 15, "hla": -2},  # Mid-iron
            {"speed": 165, "spin": 2500, "launch": 12, "hla": 5},  # Driver
        ]

        for data in test_data:
            shot = GC2ShotData(
                shot_id=1,
                ball_speed=data["speed"],
                launch_angle=data["launch"],
                horizontal_launch_angle=data["hla"],
                total_spin=data["spin"],
                back_spin=data["spin"] - 200,
                side_spin=200,
            )
            response = gspro_client.send_shot(shot)
            assert response is not None
            assert response.is_success

        # Verify all shots have correct data (filter out heartbeat)
        shot_messages = get_shot_messages(mock_gspro_server.received_shots)
        for i, received in enumerate(shot_messages):
            data = test_data[i]
            assert received["BallData"]["Speed"] == data["speed"]
            assert received["BallData"]["TotalSpin"] == data["spin"]
            assert received["BallData"]["VLA"] == data["launch"]
            assert received["BallData"]["HLA"] == data["hla"]


class TestMockGC2ToGSProFlow:
    """Test complete flow from MockGC2 through callback to GSPro."""

    def test_mock_gc2_shot_callback_to_gspro(
        self, mock_gspro_server, mock_gc2_reader: MockGC2Reader
    ):
        """Test that MockGC2 shots flow through callback to GSPro client."""
        # Create GSPro client
        client = GSProClient(host=mock_gspro_server.host, port=mock_gspro_server.port)
        connected = client.connect()
        assert connected

        try:
            received_shots: list[GC2ShotData] = []

            def on_shot(shot: GC2ShotData) -> None:
                received_shots.append(shot)
                # Send to GSPro
                client.send_shot(shot)

            # Register callback
            mock_gc2_reader.add_shot_callback(on_shot)
            mock_gc2_reader.connect()

            # Wait for heartbeat response to be processed
            time.sleep(0.1)

            # Simulate test shots
            for _ in range(3):
                mock_gc2_reader.send_test_shot()

            # Verify shots received by callback
            assert len(received_shots) == 3

            # Verify shots sent to GSPro (filter out heartbeat)
            shot_messages = get_shot_messages(mock_gspro_server.received_shots)
            assert len(shot_messages) == 3

            # Verify shot numbers are sequential (they may not start at 1 due to heartbeat)
            shot_numbers = [msg["ShotNumber"] for msg in shot_messages]
            assert shot_numbers == sorted(shot_numbers)  # Sequential
            assert len(set(shot_numbers)) == 3  # All unique

        finally:
            client.disconnect()
            mock_gc2_reader.disconnect()

    def test_shot_validation_prevents_sending(
        self, mock_gc2_reader: MockGC2Reader, sample_gc2_shot: GC2ShotData
    ):
        """Test that invalid shots (zero spin) are rejected before sending."""
        valid_shots: list[GC2ShotData] = []
        invalid_shots: list[GC2ShotData] = []

        def on_shot(shot: GC2ShotData) -> None:
            # Only accept valid shots
            if shot.is_valid():
                valid_shots.append(shot)
            else:
                invalid_shots.append(shot)

        mock_gc2_reader.add_shot_callback(on_shot)
        mock_gc2_reader.connect()

        # Create an invalid shot (zero spin)
        invalid_shot = GC2ShotData(
            shot_id=99,
            ball_speed=145,
            launch_angle=12,
            total_spin=0,
            back_spin=0,
            side_spin=0,
        )
        assert not invalid_shot.is_valid()

        # Create a valid shot
        valid_shot = GC2ShotData(
            shot_id=1,
            ball_speed=145,
            launch_angle=12,
            total_spin=2500,
            back_spin=2400,
            side_spin=100,
        )
        assert valid_shot.is_valid()

        # MockGC2 sends valid shots, so send_test_shot() should produce a valid shot
        mock_gc2_reader.send_test_shot()

        # Verify callback received a valid shot
        assert len(valid_shots) == 1
        assert valid_shots[0].is_valid()

        mock_gc2_reader.disconnect()


class TestShotDataTransformation:
    """Test shot data transformation from GC2 to GSPro format."""

    def test_ball_data_mapping(self, mock_gspro_server, gspro_client: GSProClient):
        """Test all ball data fields are correctly mapped."""
        shot = GC2ShotData(
            shot_id=1,
            ball_speed=150.5,
            launch_angle=11.2,
            horizontal_launch_angle=-2.3,
            total_spin=2800,
            back_spin=2700,
            side_spin=-400,
        )

        gspro_client.send_shot(shot)

        shot_messages = get_shot_messages(mock_gspro_server.received_shots)
        received = shot_messages[0]["BallData"]
        assert received["Speed"] == 150.5
        assert received["VLA"] == 11.2
        assert received["HLA"] == -2.3
        assert received["TotalSpin"] == 2800
        assert received["BackSpin"] == 2700
        assert received["SideSpin"] == -400

    def test_club_data_mapping(self, mock_gspro_server, gspro_client: GSProClient):
        """Test all club data fields are correctly mapped."""
        shot = GC2ShotData(
            shot_id=1,
            ball_speed=150,
            launch_angle=11,
            total_spin=2800,
            back_spin=2700,
            side_spin=-400,
            club_speed=105.5,
            swing_path=2.1,
            angle_of_attack=-3.2,
            face_to_target=0.5,
            lie=1.2,
            dynamic_loft=14.5,
            horizontal_impact=5.0,
            vertical_impact=-2.0,
            closure_rate=350.0,
        )

        gspro_client.send_shot(shot)

        shot_messages = get_shot_messages(mock_gspro_server.received_shots)
        received = shot_messages[0]["ClubData"]
        assert received["Speed"] == 105.5
        assert received["Path"] == 2.1
        assert received["AngleOfAttack"] == -3.2
        assert received["FaceToTarget"] == 0.5
        assert received["Lie"] == 1.2
        assert received["Loft"] == 14.5
        assert received["HorizontalFaceImpact"] == 5.0
        assert received["VerticalFaceImpact"] == -2.0
        assert received["ClosureRate"] == 350.0

    def test_shot_options_correct(
        self, mock_gspro_server, gspro_client: GSProClient, sample_gc2_shot: GC2ShotData
    ):
        """Test ShotDataOptions are set correctly."""
        gspro_client.send_shot(sample_gc2_shot)

        shot_messages = get_shot_messages(mock_gspro_server.received_shots)
        options = shot_messages[0]["ShotDataOptions"]
        assert options["ContainsBallData"] is True
        assert options["ContainsClubData"] is False  # No club data in sample shot
        assert options["LaunchMonitorIsReady"] is True
        assert options["LaunchMonitorBallDetected"] is True
        assert options["IsHeartBeat"] is False


class TestResponseHandling:
    """Test handling of GSPro responses."""

    def test_response_callback_invoked(
        self, mock_gspro_server, gspro_client: GSProClient, sample_gc2_shot: GC2ShotData
    ):
        """Test that response callbacks are invoked on shot response."""
        responses: list[GSProResponse] = []

        def on_response(response: GSProResponse) -> None:
            responses.append(response)

        gspro_client.add_response_callback(on_response)

        gspro_client.send_shot(sample_gc2_shot)

        # Give callback time to be invoked (synchronous call)
        assert len(responses) == 1
        assert responses[0].Code == 201  # Mock server returns 201 with player info
        assert responses[0].is_success

    def test_player_info_extracted(
        self, mock_gspro_server, gspro_client: GSProClient, sample_gc2_shot: GC2ShotData
    ):
        """Test that player info is extracted from response."""
        gspro_client.send_shot(sample_gc2_shot)

        # Mock server sends player info
        player = gspro_client.current_player
        assert player is not None
        assert player["Handed"] == "RH"
        assert player["Club"] == "DR"
