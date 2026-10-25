# Decision Studio

Decision Studio connects five features around the same saved construction project. Open **Try Decision Studio · school example** on the welcome screen, or select **Decision Studio** in an existing workspace.

## Five features

1. **Brief copilot.** Describe an adaptation budget, hypothetical water level, clearance margin, maximum floor lift, and equipment-only protection. Review and edit extracted constraints before solving. The local English parser handles explicit labels, euros, `k`/`million`, metres and centimetres. It leaves unmentioned settings unchanged and lists recognized fields. Optional AI parsing uses OpenAI Responses structured output; enable the checkbox to send only the brief to OpenAI. Missing keys, refusal or provider errors fall back to the local parser. Neither parser computes costs or invents site-specific flood levels.
2. **Official site evidence.** Search French addresses through IGN Géoplateforme and attach the municipality's Géorisques GASPAR hazard inventory. The server revalidates the selected search result and records the address, coordinates, precision, INSEE code, retrieval time and source links. Provider failure and no municipal record are distinct states. This does not relocate the existing fictional plot, update its synthetic scores, or establish parcel exposure.
3. **Design library.** Save up to 20 named alternatives. Each contains the solver inputs, confirmed geometry, recalculated quantities, geometry fingerprint, solver version and site evidence captured when saved. A later comparison or evidence update leaves earlier snapshots intact. Reopening regenerates a comparison; it never silently applies elevations. Changed or unlinked geometry blocks restoration. Historical snapshots remain available for comparison and stress testing.
4. **Fixed-design stress grid.** Evaluate one saved design against up to 12 water levels and eight cost-increase values; the UI uses 24 combinations. Cells separately report water-clearance failure, budget failure, both, or neither. Inputs and geometry regenerate quantities rather than trusting saved price labels. Exact water and budget boundaries are inclusive. A zero-cost proposal has no finite cost-escalation threshold. The latest grid and timestamp persist with the design. Scenario counts are not probabilities.
5. **Decision story and export.** Present five keyboard-navigable scenes: brief, sources, alternatives, selected proposal and challenge. Arrow keys navigate; Escape exits and returns focus. The dialog traps focus, and the layout supports smaller screens. Export a Markdown decision brief with saved alternatives, source links, original inputs, calculation factors, the selected design's stress grid and verification gaps. A design selected for discussion is distinct from the applied 3D design.

## A two-minute demo

1. Launch the school example. Review the prefilled brief and generate alternatives.
2. Search `Lyon` in Site evidence and attach the official municipality record.
3. Save the lowest-cost and lowest-added-carbon alternatives in the library.
4. Select one and run 24 scenarios. Explain the first water or budget failure.
5. Open Decision story, present the proposal, and download the sourced brief.
6. Optionally reopen an alternative, open Resilience Lab, and apply it to the 3D simulator.

The initial school dimensions and prices remain illustrative. Municipality records do not validate the fictional school site. Water level and margin are explicit scenario choices.

## Implementation

- `backend/app/studio.py`: validated briefs, bounded provider clients, library and stress routes.
- `frontend/components/planner/DecisionStudio.tsx` and `studio.css`: five-feature workspace and presentation.
- `frontend/lib/decisionPacket.ts`: downloadable decision brief.
- `frontend/types/studio.ts`: shared frontend contracts.
- `backend/tests/test_studio.py`: parsing, provider handling, ownership, snapshot recovery, tampered price recalculation and boundary tests.
- `frontend/tests/studio.test.tsx`: reviewed brief, source attachment/error states, alternative saving, stress grid, keyboard presentation and export tests using jsdom.

Routes require authentication; project routes enforce ownership before external calls or mutation. Storage uses the existing project JSON column; no database migration is needed. Parent project saves retain Studio fields. Reusable design assumptions remain editable project data, not cryptographically signed evidence.

Optional configuration: `OPENAI_API_KEY` and `OPENAI_BRIEF_MODEL` (falls back to `OPENAI_BLUEPRINT_MODEL`). An AI key is not necessary for any of the five workflows. Official source lookup requires network access; stored evidence remains readable offline.

Official endpoints:

- [IGN geocoding](https://data.geopf.fr/geocodage/search?q=Lyon&limit=1)
- [Géorisques municipality hazards](https://www.georisques.gouv.fr/api/v1/gaspar/risques?code_insee=69123&page_size=100)
- [OpenAI structured output format](https://developers.openai.com/api/docs/guides/structured-outputs)

## Checks and limits

Run `python -m pytest` from `backend`, then `npm test`, `npm run typecheck` and `npm run build` from `frontend`. Tests mock optional AI and public providers; live provider shapes were separately checked against Lyon. Automated component tests do not establish pixel-level browser quality. The live OpenAI path requires a configured, authorized model and was not exercised against a billed account.

The solver checks conceptual vertical clearance. It excludes structural design, foundations, access, drainage, evacuation, site-specific engineering, tax and validated carbon declarations. Equipment-only protection can leave occupied floors exposed. Every alternative retains its own footprint, water scenario, margin and budget; differences between incompatible scenarios must not be presented as like-for-like savings.
