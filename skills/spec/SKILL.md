---
description: Generate engineering specification.
---

Generate a complete engineering specification for the described system or given requirements. The specification should cover the following areas:

## Overall
- Stack Choices
- Architecture Diagram
- Data Models, relations and constraints
  - Suggest different naming choices for tables and columns
- Data Flow, state & lifecycle
- Scenario & Behavior Specifications
  - Define scenario with EARS notation, for example: WHEN <trigger> THEN <result>, WHILE <state-change> THEN <result>
  - List down mentioned cases and their expected behavior in Given-When-Then format
- Project Folder Structure

## Frontend Specifications
- Key Pages / Views and components
- State Management Strategy (for frontend)

## Backend Specifications
- Module Breakdown
- Service Responsibilities
- API / Webhook Specifications (endpoints, methods, request/response formats)

## Output Rules:
- Save the output as `docs/specification.md`.
- Output must include the following sections with clear explanations, tables, diagrams (as text or mermaid). 
- Keep it high-level without over explaining obvious thing, but detailed enough to be directly implementable by engineers.
- Do not assume or invent new features or requirements unless they are clearly implied.