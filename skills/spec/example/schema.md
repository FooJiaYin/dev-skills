# `attendance`

Per-student status for a specific [`session`](sessions.md).

## Columns

- `id` : UUID [1] {PK} = `gen_random_uuid()`
- `session_id` : UUID [1] {FK -> [sessions.id](sessions.md)}
- `student_id` : UUID [1] {FK -> [students.id](students.md)}
- `class_id` : Text [1] {FK -> [classes.id](classes.md)} (Determines which enrollment to deduct from; differs from `session.class_id` when the student is making up a class)
- `status` : Enum(`PRESENT`, `ABSENT`, `LEAVE`, `UNRECORDED`) [1] = `UNRECORDED`
- `credits_used` : Int [1] = `1` (CHECK: `>= 0`; deducted only when `status = PRESENT`)
- `notes` : Text [0..1]
- `is_makeup` : Boolean [1] = `false` (Auto-set to `true` when `class_id != session.class_id`)
- `created_at` : Timestamptz [1] = `now()`
- `updated_at` : Timestamptz [1] = `now()`

## Constraints & Indexes

- PK: `id`
- Unique: `(session_id, student_id)`
- CHECK: `credits_used >= 0`
- Index: `attendance_session_idx (session_id)`, `attendance_student_idx (student_id)`

## Rules

- Deduct credits from the [`enrollments`](enrollments.md) row matching `attendance.class_id` (not `session.class_id`) — supports make-up flows.
- Allowed transitions: `UNRECORDED → PRESENT | ABSENT | LEAVE`.
- `ABSENT` (無故缺席) increments `enrollments.absence_points` by 1; no credit deduction at the moment of absence.
- `LEAVE` (approved) does not deduct credits.

## JSON example

```json
{
  "id": "38ce9004-dbdb-46fb-8fc4-ade66e66aeec",
  "session_id": "ecf4bf32-2c8e-40c6-989e-407e801cc8e1",
  "student_id": "337059f3-f178-4012-a226-d33fd0df3e0e",
  "class_id": "child_sat_D",
  "status": "UNRECORDED",
  "credits_used": 1,
  "notes": null,
  "is_makeup": false,
  "created_at": "2026-04-25T09:00:07.258548+00:00",
  "updated_at": "2026-04-25T09:00:07.258548+00:00"
}
```
