# StyleMate: What Was Added After The Early MVP

This repository is significantly ahead of the early MVP state.

## Main improvements

- added local vision inference instead of relying only on an external tunnel-based service
- introduced a fallback-capable vision service layer with `local / remote / auto` modes
- expanded outfit generation logic with stronger scenario rules and more stable candidate ranking
- added formality detection for events and scenarios
- improved robustness against broken, conflicting, and prompt-injection-like user requests
- added anti-repeat logic so the same items do not dominate recommendations
- added gender-aware soft personalization
- added support for multiple item sources: user wardrobe, shop catalog, mixed mode
- added user wardrobe isolation through anonymous per-browser owner tokens
- added wardrobe editing, single delete, bulk delete, and clear-all actions
- improved public demo workflow with backend and tunnel helper scripts
- integrated safer catalog expansion tooling and parser-related utilities

## Product impact

Compared to the early MVP, the system is now much closer to a real product demo:

- the wardrobe can be populated and corrected by the user
- the recommendation pipeline is more scenario-aware
- the system is more resilient to noisy inputs
- the demo can be exposed outside the local network
- the local AI stack is stronger and less dependent on unstable external services
