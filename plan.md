# GC2 Connect Desktop - Implementation Plan

> **Related Documentation:**
> - `docs/PRD.md` - Product requirements (v1.0)
> - `docs/TRD.md` - Technical requirements (v1.0)
> - `docs/PRD_OPEN_RANGE.md` - Open Range feature requirements
> - `docs/TRD_OPEN_RANGE.md` - Open Range technical requirements
> - `docs/PHYSICS.md` - Golf ball physics specification
> - `docs/GC2_PROTOCOL.md` - USB protocol specification
> - `todo.md` - Implementation tracking

## Project Summary

GC2 Connect Desktop is a Python application that reads shot data from a Foresight GC2 golf launch monitor via USB and sends it to GSPro golf simulation software over the network. Version 1.1 adds Open Range - a built-in driving range simulator with physics-accurate ball flight visualization.

## Implementation Phases

### Phase 1: Foundation & Testing Infrastructure ✅
### Phase 2: Configuration & Settings ✅
### Phase 3: Reliability & Error Handling ✅
### Phase 4: GSPro Features ✅
### Phase 5: Open Range Feature ✅
### Phase 5b: OpenGolfCoach Integration (IN PROGRESS)
### Phase 5c: Enhanced Driving Range Visuals (PLANNED)
### Phase 5d: Minigames Framework (PLANNED)
### Phase 6: Polish & Release ✅

---

# Completed Prompts (Details Omitted)

- **Prompt 1**: Project Setup & Testing Infrastructure ✅
- **Prompt 2**: Add ABOUTME Comments ✅
- **Prompt 3**: Unit Tests for Data Models ✅
- **Prompt 4**: Unit Tests for GC2 Protocol ✅
- **Prompt 5**: Unit Tests for GSPro Client ✅
- **Prompt 6**: Settings Module Implementation ✅
- **Prompt 7**: Integrate Settings into UI ✅
- **Prompt 7b**: GSPro Clean Disconnect Handling ✅
- **Prompt 7c**: GSPro Response Reader Loop ✅
- **Prompt 7d**: GSPro Match State and Heartbeat Timer ✅
- **Prompt 8**: Auto-Reconnection Logic ✅
- **Prompt 9**: Integration Tests ✅
- **Prompt 10**: Shot History Improvements ✅
- **Prompt 11**: CSV Export ✅
- **Prompt 12**: Open Range Data Models & Constants ✅
- **Prompt 13**: Aerodynamics Module ✅
- **Prompt 14**: Trajectory Simulation (RK4) ✅
- **Prompt 15**: Ground Physics (Bounce/Roll) ✅
- **Prompt 16**: Physics Engine Integration ✅
- **Prompt 17**: Mode Selection & Shot Router ✅
- **Prompt 18**: Open Range Settings ✅
- **Prompt 19**: 3D Driving Range Visualization ✅
- **Prompt 20**: Open Range UI Panel ✅
- **Prompt 21**: Open Range Integration ✅
- **Prompt 21b**: Ball Trajectory Tracing ✅
- **Prompt 21c**: Add OpenGolfCoach Dependency ✅
- **Prompt 21d**: Integrate OpenGolfCoach into ShotSummary ✅
- **Prompt 21e**: Update OpenRangeEngine to Use OpenGolfCoach ✅
- **Prompt 22**: End-to-End Tests ✅
- **Prompt 23**: Type Checking & Linting ✅
- **Prompt 24**: Documentation & Release ✅

---

# Active Prompts

## Prompt 21d: Integrate OpenGolfCoach into ShotSummary ✅

```text
Extend ShotSummary and ShotResult models to include OpenGolfCoach derived values.

CONTEXT:
- OpenGolfCoach provides additional values not in our current models:
  - Shot classification (shot_name: "Straight", "Push Slice", etc.)
  - Shot ranking (shot_rank: S+, S, A, B, C, D, E)
  - Shot color for UI (shot_color_rgb: hex color)
  - Smash factor
  - Estimated club data
- These should be optional to maintain backwards compatibility
- The existing physics engine can still be used for trajectory (flight path)
- OpenGolfCoach provides carry/total distance which we can compare to our physics

TASK:

1. First, write tests in tests/unit/test_open_range/test_extended_models.py:
   - Test ShotSummary with new optional fields
   - Test ShotSummary without new fields (backwards compatible)
   - Test DerivedShotData model creation
   - Test ShotResult includes derived data when available

2. Update src/gc2_connect/open_range/models.py:
```python
# Add new model for OpenGolfCoach derived values
class DerivedShotData(BaseModel):
    """Shot data derived from OpenGolfCoach calculations."""

    # Shot classification
    shot_name: Annotated[str, Field(description="Human-readable shot classification")] = "Unknown"
    shot_rank: Annotated[str, Field(description="Shot quality rank (S+, S, A, B, C, D, E)")] = "D"
    shot_color_rgb: Annotated[str, Field(description="Hex color for UI display")] = "#808080"

    # Performance metrics
    smash_factor: Annotated[float | None, Field(description="Ball speed / club speed ratio")] = None

    # Estimated club data (from ball data)
    estimated_club_speed_mph: Annotated[float | None, Field(description="Estimated club speed")] = None
    estimated_club_path_deg: Annotated[float | None, Field(description="Estimated club path")] = None
    estimated_face_angle_deg: Annotated[float | None, Field(description="Estimated face angle")] = None

    # OpenGolfCoach distance calculations (for comparison)
    ogc_carry_distance: Annotated[float | None, Field(description="Carry distance from OpenGolfCoach")] = None
    ogc_total_distance: Annotated[float | None, Field(description="Total distance from OpenGolfCoach")] = None


# Update ShotResult to include derived data
class ShotResult(BaseModel):
    """Complete simulation result."""

    trajectory: Annotated[list[TrajectoryPoint], Field(description="List of trajectory points")]
    summary: Annotated[ShotSummary, Field(description="Shot summary metrics")]
    launch_data: Annotated[LaunchData, Field(description="Input launch conditions")]
    conditions: Annotated[Conditions, Field(description="Environmental conditions")]
    derived: Annotated[DerivedShotData | None, Field(description="OpenGolfCoach derived values")] = None
```

3. Create factory function to populate derived data:
```python
# In opengolfcoach_wrapper.py or a new enrichment module
def enrich_shot_result(result: ShotResult, gc2_shot: GC2ShotData) -> ShotResult:
    """Add OpenGolfCoach derived values to a ShotResult."""
    try:
        ogc_result = calculate_shot_from_gc2(gc2_shot)
        derived = DerivedShotData(
            shot_name=ogc_result.shot_name,
            shot_rank=ogc_result.shot_rank,
            shot_color_rgb=ogc_result.shot_color_rgb,
            smash_factor=ogc_result.smash_factor,
            estimated_club_speed_mph=ogc_result.club_speed_meters_per_second * 2.23694 if ogc_result.club_speed_meters_per_second else None,
            estimated_club_path_deg=ogc_result.club_path_degrees,
            estimated_face_angle_deg=ogc_result.club_face_to_target_degrees,
            ogc_carry_distance=ogc_result.carry_distance_yards,
            ogc_total_distance=ogc_result.total_distance_yards,
        )
        return result.model_copy(update={"derived": derived})
    except Exception:
        return result
```

4. Run tests: uv run pytest tests/unit/test_open_range/test_extended_models.py -v

REQUIREMENTS:
- Backwards compatible - existing code works without derived data
- Graceful fallback if OpenGolfCoach fails
- Use Annotated[Type, Field(...)] for new Pydantic fields
```

---

## Prompt 21e: Update OpenRangeEngine to Use OpenGolfCoach ✅

Completed: Added OpenGolfCoach integration to OpenRangeEngine:
- Added `_enrich_with_opengolfcoach()` method
- `simulate_shot()`, `simulate_manual()`, and `simulate_test_shot()` now enrich results
- Graceful fallback when OpenGolfCoach unavailable or fails
- Trajectory still comes from physics engine
- 16 new tests in `test_engine_integration.py`

---

## Prompt 21f: Update Open Range UI for Shot Classification ← NEXT

```text
Update the Open Range UI to display shot classification and ranking from OpenGolfCoach.

TASK:

1. Write tests in tests/integration/test_open_range_classification_ui.py
2. Update src/gc2_connect/ui/components/open_range_view.py:
   - Add _build_shot_classification_panel() with shot_name and rank badge
   - Add _update_shot_classification() with rank color coding
   - Rank colors: S+=gold, S=silver, A=green, B=blue, C=purple, D=orange, E=red

3. Run tests: uv run pytest tests/integration/test_open_range_classification_ui.py -v

REQUIREMENTS:
- UI gracefully handles missing derived data
- Rank colors are visually distinct and intuitive
```

---

## Prompt 21g: Validate OpenGolfCoach vs Physics Engine

```text
Create validation tests comparing OpenGolfCoach distances with our physics engine.

TASK:

1. Write tests in tests/unit/test_open_range/test_physics_comparison.py:
   - Compare driver, 7-iron, wedge shots
   - Both engines should be within 15% tolerance
   - Tests skip gracefully if OpenGolfCoach not installed

2. Add distance comparison logging utility in engine.py

3. Run tests: uv run pytest tests/unit/test_open_range/test_physics_comparison.py -v
```

---

# Future Prompts (Phase 5c: Enhanced Visuals)

## Prompt 25: Procedural Terrain and Atmosphere
- Add terrain undulations, vertex color blending, atmospheric fog, boundary trees
- Test performance stays above 30fps

## Prompt 26: Multiple Camera Views and Minimap
- Camera presets (behind, follow, overhead, side, green)
- Minimap component, smooth transitions

---

# Future Prompts (Phase 5d: Minigames)

## Prompt 27: Minigames Base Architecture
- BaseMinigame, GameType, GameScore, GameManager
- Wire into ShotRouter

## Prompt 28: Putting Green Minigame
- Stimpmeter physics, putting visualization

## Prompt 29: Target Range Minigame
- Concentric scoring zones, game modes (Practice, Challenge, Ladder)

## Prompt 30: Golf Darts Minigame
- VLA/HLA to dartboard mapping, 301/501/Cricket modes

## Prompt 31: Minigames UI and Game Selector
- GameSelector dialog, game switching

---

# Implementation Order Summary

## Completed ✅
- Phase 1-4: Foundation, Settings, Reliability, GSPro Features
- Phase 5: Open Range Feature (12-21b)
- Phase 5b: Prompt 21c (OpenGolfCoach wrapper)
- Phase 6: E2E tests, type checking, documentation

## In Progress
- **Prompt 21f**: Update Open Range UI for Shot Classification ← NEXT
- **Prompt 21g**: Validate OpenGolfCoach vs Physics Engine

## Planned
- Phase 5c: Enhanced Visuals (25-26)
- Phase 5d: Minigames (27-31)
