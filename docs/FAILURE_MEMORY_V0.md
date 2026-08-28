# Failure Memory V0

Failure memory is an anti-repeat system, not a blacklist. Each rejected mechanism records:

- the falsifiable hypothesis;
- environment and time/regime context;
- relevant parameter values;
- a controlled failure class;
- evidence event IDs;
- a normalized similarity signature;
- conditions under which retesting could become rational.

## Matching

Wave 0 uses transparent Jaccard overlap on normalized signature tokens. It is deterministic, inspectable, and intentionally conservative. A score at or above the configured threshold emits an anti-repeat warning before investigation. This warning must accompany later work and can cause watch/kill decisions, but similarity alone is not proof of identical failure.

Future matching may combine exact structured filters, embeddings, and regime comparisons. Any learned matcher must retain the deterministic score, expose contributing features, be evaluated on blind holdouts, and support abstention.

## Lifecycle

Memories are append-only with superseding records rather than destructive edits. Retesting requires evidence that at least one documented revival condition holds. Results of retests create new memories linked to the originals, preventing survivorship-biased deletion of failures.

