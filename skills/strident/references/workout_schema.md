# Garmin Connect Structured Workout JSON Schema

This reference defines the JSON payload structure required by Garmin Connect's workout service (`POST https://connectapi.garmin.com/workout-service/workout`) and enforced by [`push_workout.py`](../scripts/push_workout.py).

---

## 1. Top-Level Payload Structure

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `workoutName` | `string` | Yes | Non-empty display title shown on the watch and calendar. |
| `description` | `string` | No | Coaching notes or session summary. |
| `sportType` | `object` | Yes | Sport descriptor (`sportTypeId: 1`, `sportTypeKey: "running"`). |
| `workoutSegments` | `array` | Yes | Non-empty list of segment objects containing `workoutSteps`. |

```json
{
  "workoutName": "Strident: 6x 1km Threshold",
  "description": "6x 1000m @ 4:05-4:10/km with 75s active jog recovery.",
  "sportType": {
    "sportTypeId": 1,
    "sportTypeKey": "running",
    "displayOrder": 1
  },
  "workoutSegments": [
    {
      "segmentOrder": 1,
      "sportType": {
        "sportTypeId": 1,
        "sportTypeKey": "running",
        "displayOrder": 1
      },
      "workoutSteps": []
    }
  ]
}
```

---

## 2. Step Objects (`workoutSteps`)

Every element in `workoutSteps` must have `"type"` set to either `"ExecutableStepDTO"` or `"RepeatGroupDTO"`.

### 2.1 `ExecutableStepDTO` (Single Step)
Required fields:
- `type`: `"ExecutableStepDTO"`
- `stepOrder`: `int` ($\ge 1$)
- `stepType`: `{"stepTypeId": int, "stepTypeKey": string}`
  - `1`: `"warmup"`
  - `2`: `"cooldown"`
  - `3`: `"interval"`
  - `4`: `"recovery"`
  - `5`: `"rest"`
- `endCondition`: `{"conditionTypeId": int, "conditionTypeKey": string}`
  - `1`: `"lap.button"` (open step)
  - `2`: `"time"` (`endConditionValue` in seconds)
  - `3`: `"distance"` (`endConditionValue` in meters)
- `targetType`: `{"workoutTargetTypeId": int, "workoutTargetTypeKey": string}`
  - `1`: `"no.target"`
  - `4`: `"heart.rate.zone"` (`targetValueOne` = low bpm, `targetValueTwo` = high bpm)
  - `6`: `"pace.zone"` (`targetValueOne` = slow boundary in $\text{m/s}$, `targetValueTwo` = fast boundary in $\text{m/s}$, where `targetValueOne <= targetValueTwo`)

### 2.2 `RepeatGroupDTO` (Interval Repeat Block)
Required fields:
- `type`: `"RepeatGroupDTO"`
- `stepOrder`: `int` ($\ge 1$)
- `stepType`: `{"stepTypeId": 6, "stepTypeKey": "repeat", "displayOrder": 6}`
- `numberOfIterations`: `int` ($\ge 1$)
- `workoutSteps`: Non-empty array of child `ExecutableStepDTO` or `RepeatGroupDTO` items.

---

## 3. Pace Conversion Formula

Garmin expects pace targets in **meters per second ($\text{m/s}$)**:
$$\text{speed}_{\text{m/s}} = \frac{1000}{\text{minutes} \times 60 + \text{seconds}}$$
- `targetValueOne`: Slower pace boundary (lower $\text{m/s}$ value, e.g., `4:10/km` $\rightarrow 4.000\text{ m/s}$).
- `targetValueTwo`: Faster pace boundary (higher $\text{m/s}$ value, e.g., `4:05/km` $\rightarrow 4.082\text{ m/s}$).
