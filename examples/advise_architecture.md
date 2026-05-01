# Advise: Architecture Decision

```
We need to choose between:
A) Monolith with well-defined modules, deploy as single unit
B) Microservices with separate repos, CI/CD per service

Context: Team of 3 engineers. Product is early (< 100 users).
We have 6 months of runway. Speed of iteration is priority #1.
Compliance requirements are minimal (no SOC2, no HIPAA).

What should we pick? Give me CONCLUSION, REASONING, WATCH OUT.
```

Expected: Advisor recommends A (monolith) with clear reasoning about team size, stage, iteration speed, and flags the migration path when the time comes.
