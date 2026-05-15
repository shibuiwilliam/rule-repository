# HR Persona Guide

## Overview

The HR persona provides an employee- and workplace-centric view of the Rule Repository, focused on attendance and overtime compliance, conduct policies, and employee event monitoring.

## Getting Started

1. Navigate to the HR dashboard at `/hr`
2. Your default view shows the Employee Event Compliance Dashboard
3. Use the sidebar to access the event review queue, employee profiles, rules, and intelligence

## Key Workflows

### Monitoring Employee Event Compliance
- Review employee events (attendance records, leave requests, conduct reports) in the event review queue
- Submit employee events via `POST /api/v1/submissions` with `kind: "business_event"`
- Events are evaluated against applicable HR rules including computational overtime caps

### Attendance and Overtime Monitoring
- Computational rules automatically calculate overtime hours against legal and policy limits
- The 45h/month cap and 36-agreement clauses are enforced via deterministic evaluation (no LLM needed for numeric checks)
- Alerts surface when employees approach or exceed thresholds

### Managing Conduct Policies
- Browse conduct rules covering harassment, conflict of interest, and social media usage
- Link related policies using the rule graph to track refinements and overrides

### Discovering Rules from HR Policies
- Upload HR policy documents (employee handbooks, labor agreements, regulatory guidance)
- The extraction pipeline identifies normative statements and applicable-employee-class metadata
- Review and approve discovered rule candidates

### Using the Playground
- Test rules against sample employee events or attendance records
- The playground defaults to business event form mode for the HR persona

## Vocabulary
- **Rule** = HR policy, labor regulation, or workplace standard
- **Violation** = Employee event or practice that fails to meet a policy
- **Evaluation** = Event review against applicable HR rules
- **Subject** = Business event (attendance record, leave request, conduct report)

## Templates
- `hr-attendance-jp` -- Japanese attendance and overtime compliance (45h/month cap, 36-agreement clauses, computational rules)
- `hr-conduct` -- Workplace conduct standards (harassment, conflict of interest, social media)
