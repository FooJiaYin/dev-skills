---
description: Evaluate whether the data models and Given-When-Then behavior scenarios. 

---

Evaluate the clarity, completeness, and consistency of a given `specification.md` file.
Focus on *data model* correctness and *system behavior* completeness.
If something is unclear, ask questions.
If something is reasonable to assume, add it with explicit notation.
Follow the instructions strictly.

---

## **1. Check Coverage of Scenarios & Behavior**

For every data entity, relation, operation, or state transition described in the spec:

* Identify **all possible scenarios** that may occur now or in future extensions.
* Ask:

  * For each data model, what are the possible scenarios for a data, fields or relations to be **created**, **updated**, **deleted**, **undone**, **merged**, **archived**, **expired** or **transferred**?
  * Are there predefined options or patterns that might require **customization** later?
  * Future extensibility (custom fields, configurable patterns, additional states)
  * After each action, what **other data** must be updated?

**If anything is missing**, add it to the spec using this format:
* `[Added]` for safe and reasonable assumptions
* `[Question]` for ambiguous and unclear cases

---

## **2. Check Given–When–Then Completeness**

Examine all existing cases under a scenario.

* Are all **roles** covered?
* Are all **data states** covered?
* Are all **error / boundary cases** covered?
* Are alternative flows missing?
* Are boundary situations considered (e.g., duplicates, conflicting states, expired data, invalid transitions)?

If missing, add new Given-When-Then blocks with appropriate note tags:
* `[Added]` for safe and reasonable assumptions
* `[Question]` for ambiguous and unclear cases

---

## **3. Data Model Format Validation**

Check all data models follow the required format:

```
name : type [multiplicity] = defaultValue {propertyString}
```

Check for:

* Are any data classes mentioned in the scenario or as FK of other data classes, but not defined in the spec?
* Are any attributes required by scenarios missing?
* Are any relations missing to support behaviors?
* Are constraints (unique, nullable, indexes, lifecycle) clearly stated?
* Are multiplicities correct (1, 0..1, 1..*, etc.)?
* Are naming conventions consistent?
* Ambiguities in data lifecycle or ownership
* Cardinality mismatches
* Temporal attributes (createdAt, updatedAt, effectiveFrom, expiresAt, etc.)
* Enumerations and whether they support all necessary future state transitions

**If needed**, update the data model accordingly:
* Add new fields/relations with `[Updated]` if safe and reasonable 
* Add questions with `[Question]` if clarification is needed

---

## **4. Data Model Integrity & Normalization Review**

Check whether the model supports:

* Correct read/write patterns described in scenarios
* Data integrity
* Clear ownership of relations
* Proper normalization (to avoid data inconsistencies)
* Proper denormalization (if scenarios require faster reads)
* Is the data model needed for the system? Or it can actually combined with other data models?

If optimization is needed, revise the model and explain why.
Compare different solution and list the pros and cons for the human to make a final decision.

---

## **5. Update the Data Models in `specification.md`**

After identifying missing scenarios and constraints:

* Add new attributes, constraints, relations when clearly needed
* For each addition:

  * If based on clear logic → add with note `⚠️ Assumed`
  * If unclear → add `❓ Question` entries inside the spec
* Do not modify existing sections except data models and scenario lists
* Maintain original tone and structure

---

## **Final Output**
Output the revised `specification.md` file with all changes and questions clearly marked.

## **Important Rules**

* Ambiguous assumptions must be written as questions.
