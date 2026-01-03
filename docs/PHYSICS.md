# Golf Ball Physics Specification
# GC2 Connect Unity

## Document Info
| Field | Value |
|-------|-------|
| Version | 1.1.0 |
| Last Updated | December 2025 |
| Based On | Nathan Model, libgolf reference implementation |

---

## 1. Overview

This document specifies the physics model used for golf ball trajectory simulation in GC2 Connect Unity. The model is based on Professor Alan Nathan's trajectory calculator and Washington State University (WSU) aerodynamics research.

### Key References
- Prof. Alan Nathan (UIUC): [Trajectory Calculator](http://baseball.physics.illinois.edu/trajectory-calculator.html)
- [libgolf](https://github.com/gdifiore/libgolf): C++ reference implementation of Nathan model
- WSU Golf Ball Aerodynamics: Smits & Smith wind tunnel data
- USGA Ball Specifications

---

## 2. Coordinate System

```
        Y (up)
        │
        │
        │
        └───────── X (forward/target)
       /
      /
     Z (lateral, + = right)
```

- **X-axis**: Forward toward target (yards in output, meters in simulation)
- **Y-axis**: Vertical (height in feet in output, meters in simulation)
- **Z-axis**: Lateral (+ = right of target, yards in output)

---

## 3. Physical Constants

### 3.1 Ball Properties (USGA Specifications)

```csharp
public static class BallConstants
{
    // Mass: 1.620 oz maximum
    public const float MassKg = 0.04593f;
    
    // Diameter: 1.680 inches minimum
    public const float DiameterM = 0.04267f;
    public const float RadiusM = 0.021335f;
    
    // Cross-sectional area
    public static readonly float AreaM2 = Mathf.PI * RadiusM * RadiusM;
    // = 0.001430 m²
}
```

### 3.2 Standard Atmosphere

```csharp
public static class AtmosphereConstants
{
    public const float StdTempF = 70f;           // 21.1°C
    public const float StdElevationFt = 0f;      // Sea level
    public const float StdHumidityPct = 50f;
    public const float StdPressureInHg = 29.92f; // 1013.25 hPa
    public const float StdAirDensity = 1.194f;   // kg/m³
}
```

### 3.3 Physical Constants

```csharp
public static class PhysicsConstants
{
    public const float GravityMs2 = 9.81f;
    public const float SpinDecayRate = 0.01f;    // Per second
}
```

---

## 4. Aerodynamic Coefficients

The aerodynamic model is calibrated against the [libgolf](https://github.com/gdifiore/libgolf) C++ implementation of the Nathan model.

### 4.1 Drag Coefficient (Cd)

The drag coefficient uses a piecewise linear model based on Reynolds number, with a spin-dependent term:

```csharp
// Drag coefficient constants (from libgolf)
public const float CdLow = 0.500f;      // Low Reynolds (Re < 0.5×10^5)
public const float CdHigh = 0.212f;     // High Reynolds (Re > 1.0×10^5)
public const float CdSpin = 0.15f;      // Spin-dependent drag coefficient
public const float ReLow = 0.5f;        // Low Reynolds threshold (×10^5)
public const float ReHigh = 1.0f;       // High Reynolds threshold (×10^5)

public static float GetDragCoefficient(float reynolds, float spinFactor = 0f)
{
    // Reynolds is in units of 10^5
    float re = reynolds / 100000f;

    // Piecewise linear base drag (drag crisis model)
    float baseCd;
    if (re <= ReLow)
        baseCd = CdLow;
    else if (re >= ReHigh)
        baseCd = CdHigh;
    else
    {
        // Linear interpolation in transition region
        float t = (re - ReLow) / (ReHigh - ReLow);
        baseCd = Mathf.Lerp(CdLow, CdHigh, t);
    }

    // Add spin-dependent drag
    float totalCd = baseCd + CdSpin * spinFactor;

    return totalCd;
}
```

### 4.2 Lift Coefficient (Cl)

Lift coefficient uses a quadratic formula based on spin factor S = (ω × r) / V:

```csharp
// Lift coefficient constants (from libgolf quadratic formula)
public const float ClLinear = 1.990f;        // Linear term
public const float ClQuadratic = -3.250f;    // Quadratic term
public const float ClMax = 0.305f;           // Maximum lift coefficient
public const float ClSpinThreshold = 0.30f;  // Spin factor where Cl maxes out

public static float GetLiftCoefficient(float spinFactor)
{
    if (spinFactor <= 0) return 0f;

    // Above threshold, Cl is capped
    if (spinFactor >= ClSpinThreshold)
        return ClMax;

    // Quadratic formula: Cl = 1.990×S - 3.250×S²
    float cl = ClLinear * spinFactor + ClQuadratic * spinFactor * spinFactor;

    return Mathf.Clamp(cl, 0f, ClMax);
}
```

The quadratic formula provides better accuracy for high-spin shots (wedges) compared to table interpolation.

### 4.3 Reynolds Number Calculation

```csharp
public static float CalculateReynolds(float velocityMs, float airDensity)
{
    // Re = ρ × V × D / μ
    // Using kinematic viscosity ν = μ/ρ ≈ 1.5 × 10^-5 m²/s at standard conditions
    
    const float kinematicViscosity = 1.5e-5f;
    return (velocityMs * BallConstants.DiameterM) / kinematicViscosity;
}
```

---

## 5. Atmospheric Model

### 5.1 Air Density Calculation

```csharp
public static float CalculateAirDensity(
    float tempF, 
    float elevationFt, 
    float humidityPct,
    float pressureInHg = 29.92f)
{
    // Convert temperature
    float tempC = (tempF - 32f) * 5f / 9f;
    float tempK = tempC + 273.15f;
    
    // Pressure adjustment for elevation (barometric formula)
    // P = P0 × exp(-Mgh/RT)
    float elevationM = elevationFt * 0.3048f;
    float pressurePa = pressureInHg * 3386.39f;  // inHg to Pa
    float pressureAtAlt = pressurePa * Mathf.Exp(-0.0001185f * elevationM);
    
    // Saturation vapor pressure (Magnus formula)
    float es = 6.1078f * Mathf.Exp((17.27f * tempC) / (tempC + 237.3f));  // hPa
    float e = (humidityPct / 100f) * es;  // Actual vapor pressure
    float ePa = e * 100f;  // hPa to Pa
    
    // Air density (ideal gas law with humidity correction)
    // ρ = (Pd × Md + Pv × Mv) / (R × T)
    const float Rd = 287.05f;   // Dry air gas constant
    const float Rv = 461.495f;  // Water vapor gas constant
    
    float pd = pressureAtAlt - ePa;  // Partial pressure of dry air
    float density = (pd / (Rd * tempK)) + (ePa / (Rv * tempK));
    
    return density;
}
```

### 5.2 Wind Profile

Wind speed varies with height (logarithmic profile):

```csharp
public Vector3 GetWindAtHeight(float heightM)
{
    if (_windSpeedMph < 0.1f) return Vector3.zero;
    
    float heightFt = heightM * 3.281f;
    
    // Logarithmic wind profile
    // V(h) = V_ref × ln(h/z0) / ln(h_ref/z0)
    const float z0 = 0.01f;        // Roughness length (short grass)
    const float refHeight = 10f;   // Reference height (feet)
    
    float factor = 1f;
    if (heightFt > 0.1f)
    {
        factor = Mathf.Log(heightFt / z0) / Mathf.Log(refHeight / z0);
        factor = Mathf.Clamp(factor, 0f, 2f);
    }
    
    float windSpeedMs = _windSpeedMph * 0.44704f * factor;
    float windDirRad = _windDirDeg * Mathf.Deg2Rad;
    
    // Wind direction: 0° = from north (headwind), 90° = from east (left-to-right)
    return new Vector3(
        -windSpeedMs * Mathf.Cos(windDirRad),  // Headwind component
        0f,
        windSpeedMs * Mathf.Sin(windDirRad)    // Crosswind component
    );
}
```

---

## 6. Force Calculations

### 6.1 Gravity Force

```csharp
Vector3 gravityForce = new Vector3(0, -BallConstants.MassKg * PhysicsConstants.GravityMs2, 0);
```

### 6.2 Drag Force

```csharp
// Relative velocity (accounting for wind)
Vector3 wind = GetWindAtHeight(position.y);
Vector3 relativeVelocity = velocity - wind;
float speed = relativeVelocity.magnitude;

// Dynamic pressure
float q = 0.5f * airDensity * speed * speed;

// Drag force (opposes motion)
float Re = CalculateReynolds(speed, airDensity);
float Cd = GetDragCoefficient(Re);
float dragMagnitude = q * Cd * BallConstants.AreaM2;
Vector3 dragDirection = -relativeVelocity.normalized;
Vector3 dragForce = dragDirection * dragMagnitude;
```

### 6.3 Magnus Force (Lift)

```csharp
// Spin vector (rad/s)
float omegaBack = backspin * 2f * Mathf.PI / 60f;   // rpm to rad/s
float omegaSide = sidespin * 2f * Mathf.PI / 60f;

// Combined spin rate
float omegaTotal = Mathf.Sqrt(omegaBack * omegaBack + omegaSide * omegaSide);

// Spin factor
float S = (omegaTotal * BallConstants.RadiusM) / speed;
float Cl = GetLiftCoefficient(S);

// Magnus force direction: ω × v
// Backspin creates lift, sidespin creates curve
Vector3 spinVector = new Vector3(0, omegaSide, omegaBack);
Vector3 magnusDirection = Vector3.Cross(spinVector, relativeVelocity).normalized;
float magnusMagnitude = q * Cl * BallConstants.AreaM2;
Vector3 magnusForce = magnusDirection * magnusMagnitude;
```

### 6.4 Total Acceleration

```csharp
Vector3 totalForce = gravityForce + dragForce + magnusForce;
Vector3 acceleration = totalForce / BallConstants.MassKg;
```

---

## 7. Numerical Integration (RK4)

Fourth-order Runge-Kutta integration for accuracy:

```csharp
public (Vector3 newPos, Vector3 newVel) RK4Step(
    Vector3 pos, Vector3 vel, float backspin, float sidespin, float dt)
{
    // k1
    Vector3 a1 = CalculateAcceleration(pos, vel, backspin, sidespin);
    Vector3 k1_pos = vel;
    Vector3 k1_vel = a1;
    
    // k2
    Vector3 pos2 = pos + k1_pos * (dt / 2f);
    Vector3 vel2 = vel + k1_vel * (dt / 2f);
    Vector3 a2 = CalculateAcceleration(pos2, vel2, backspin, sidespin);
    Vector3 k2_pos = vel2;
    Vector3 k2_vel = a2;
    
    // k3
    Vector3 pos3 = pos + k2_pos * (dt / 2f);
    Vector3 vel3 = vel + k2_vel * (dt / 2f);
    Vector3 a3 = CalculateAcceleration(pos3, vel3, backspin, sidespin);
    Vector3 k3_pos = vel3;
    Vector3 k3_vel = a3;
    
    // k4
    Vector3 pos4 = pos + k3_pos * dt;
    Vector3 vel4 = vel + k3_vel * dt;
    Vector3 a4 = CalculateAcceleration(pos4, vel4, backspin, sidespin);
    Vector3 k4_pos = vel4;
    Vector3 k4_vel = a4;
    
    // Combine
    Vector3 newPos = pos + (k1_pos + 2*k2_pos + 2*k3_pos + k4_pos) * (dt / 6f);
    Vector3 newVel = vel + (k1_vel + 2*k2_vel + 2*k3_vel + k4_vel) * (dt / 6f);
    
    return (newPos, newVel);
}
```

---

## 8. Ground Physics

### 8.1 Surface Properties

```csharp
public class GroundSurface
{
    public string Name;
    public float COR;              // Coefficient of Restitution
    public float RollingResistance;
    public float Friction;
    
    public static readonly GroundSurface Fairway = new GroundSurface
    {
        Name = "Fairway",
        COR = 0.60f,
        RollingResistance = 0.10f,
        Friction = 0.50f
    };
    
    public static readonly GroundSurface Rough = new GroundSurface
    {
        Name = "Rough",
        COR = 0.30f,
        RollingResistance = 0.30f,
        Friction = 0.70f
    };
    
    public static readonly GroundSurface Green = new GroundSurface
    {
        Name = "Green",
        COR = 0.40f,
        RollingResistance = 0.05f,
        Friction = 0.30f
    };
}
```

### 8.2 Bounce Physics

```csharp
public static (Vector3 pos, Vector3 vel, float spin) Bounce(
    Vector3 pos, Vector3 vel, float backspin, GroundSurface surface)
{
    // Decompose velocity into normal and tangential
    Vector3 normal = Vector3.up;
    float vn = Vector3.Dot(vel, normal);           // Normal component (negative)
    Vector3 vt = vel - normal * vn;                // Tangential component
    
    // Apply coefficient of restitution to normal component
    float vnNew = -vn * surface.COR;
    
    // Apply friction to tangential component
    Vector3 vtNew = vt * (1f - surface.Friction * 0.3f);
    
    // Combine
    Vector3 newVel = vtNew + normal * vnNew;
    
    // Spin reduction on bounce
    float newSpin = backspin * 0.7f;
    
    // Ensure ball is above ground
    Vector3 newPos = new Vector3(pos.x, 0.001f, pos.z);
    
    return (newPos, newVel, newSpin);
}
```

### 8.3 Roll Physics

```csharp
public static (Vector3 pos, Vector3 vel, float spin, Phase phase) RollStep(
    Vector3 pos, Vector3 vel, float backspin, GroundSurface surface, float dt)
{
    float speed = vel.magnitude;
    
    // Stopped threshold
    if (speed < 0.1f)
    {
        return (pos, Vector3.zero, 0, Phase.Stopped);
    }
    
    // Rolling deceleration
    float decel = surface.RollingResistance * PhysicsConstants.GravityMs2;
    decel = Mathf.Max(decel, 0.5f);  // Minimum deceleration
    
    float newSpeed = speed - decel * dt;
    if (newSpeed <= 0)
    {
        return (pos, Vector3.zero, 0, Phase.Stopped);
    }
    
    // Update velocity
    Vector3 direction = vel.normalized;
    Vector3 newVel = direction * newSpeed;
    
    // Update position
    Vector3 newPos = pos + newVel * dt;
    newPos.y = 0;  // Stay on ground
    
    // Spin decay during roll
    float newSpin = backspin * (1f - 0.1f * dt);
    
    return (newPos, newVel, newSpin, Phase.Rolling);
}
```

---

## 9. Simulation Parameters

```csharp
public static class SimulationConstants
{
    public const float Dt = 0.01f;              // Time step (10ms)
    public const float MaxTime = 30f;           // Maximum simulation time
    public const int MaxIterations = 3000;      // Safety limit
    public const int MaxTrajectoryPoints = 600; // Memory limit
    public const float StoppedThreshold = 0.1f; // m/s
    public const int MaxBounces = 5;
}
```

---

## 10. Validation Data

### 10.1 Expected Results (Nathan Model)

| Test | Ball Speed | Launch | Spin | Expected Carry | Tolerance |
|------|------------|--------|------|----------------|-----------|
| Driver High | 167 mph | 10.9° | 2686 rpm | 275 yds | ±5% |
| Driver Mid | 160 mph | 11.0° | 3000 rpm | 259 yds | ±3% |
| 7-Iron | 120 mph | 16.3° | 7097 rpm | 172 yds | ±5% |
| Wedge | 102 mph | 24.2° | 9304 rpm | 136 yds | ±5% |

### 10.2 Validation Test Code

```csharp
[Test]
public void Physics_Validation_DriverHigh()
{
    var sim = new TrajectorySimulator();
    var result = sim.Simulate(
        ballSpeedMph: 167f,
        launchAngleDeg: 10.9f,
        directionDeg: 0f,
        backspinRpm: 2686f,
        sidespinRpm: 0f
    );
    
    float expected = 275f;
    float tolerance = expected * 0.05f;  // 5%
    Assert.AreEqual(expected, result.CarryDistance, tolerance,
        $"Carry: {result.CarryDistance:F1} yds (expected {expected} ±{tolerance:F1})");
}
```

---

## 11. Unit Conversions

```csharp
public static class UnitConversions
{
    // Speed
    public static float MphToMs(float mph) => mph * 0.44704f;
    public static float MsToMph(float ms) => ms / 0.44704f;
    
    // Distance
    public static float YardsToMeters(float yards) => yards * 0.9144f;
    public static float MetersToYards(float meters) => meters / 0.9144f;
    public static float FeetToMeters(float feet) => feet * 0.3048f;
    public static float MetersToFeet(float meters) => meters / 0.3048f;
    
    // Angle
    public static float DegToRad(float deg) => deg * Mathf.Deg2Rad;
    public static float RadToDeg(float rad) => rad * Mathf.Rad2Deg;
    
    // Spin
    public static float RpmToRadS(float rpm) => rpm * 2f * Mathf.PI / 60f;
    public static float RadSToRpm(float radS) => radS * 60f / (2f * Mathf.PI);
    
    // Temperature
    public static float FahrenheitToCelsius(float f) => (f - 32f) * 5f / 9f;
    public static float CelsiusToFahrenheit(float c) => c * 9f / 5f + 32f;
}
```

---

## 12. Output Format

### 12.1 ShotResult

```csharp
public class ShotResult
{
    // Trajectory data
    public List<TrajectoryPoint> Trajectory;
    
    // Summary metrics (all distances in yards, heights in feet)
    public float CarryDistance;      // Where ball first lands
    public float TotalDistance;      // Final resting position
    public float RollDistance;       // Total - Carry
    public float OfflineDistance;    // Lateral distance (+ = right)
    public float MaxHeight;          // Apex in feet
    public float MaxHeightTime;      // Time to apex in seconds
    public float FlightTime;         // Time to first landing
    public float TotalTime;          // Time to stopped
    public int BounceCount;
    
    // Input echo
    public LaunchData LaunchData;
    public Conditions Conditions;
}

public class TrajectoryPoint
{
    public float Time;       // Seconds
    public Vector3 Position; // X=forward (yds), Y=height (ft), Z=lateral (yds)
    public Phase Phase;      // Flight, Bounce, Rolling, Stopped
}

public enum Phase { Flight, Bounce, Rolling, Stopped }
```

---

## 13. References

1. Nathan, A.M. "The Physics of Baseball" - Trajectory calculator methodology
2. gdifiore/libgolf - C++ golf physics library implementing Nathan model: https://github.com/gdifiore/libgolf
3. Smits, A.J. & Smith, D.R. "A New Aerodynamic Model of a Golf Ball in Flight" (WSU)
4. Bearman, P.W. & Harvey, J.K. "Golf Ball Aerodynamics" - Annual Review of Fluid Mechanics
5. USGA Equipment Rules - Ball specifications
6. R&A/USGA Joint Statement on Golf Ball Performance
