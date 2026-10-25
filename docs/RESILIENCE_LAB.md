# Resilience Lab

An executable design comparison built on the existing confirmed-blueprint workflow. The user specifies budget, a hypothetical flood level, extra clearance, baseline elevations, and the permitted adaptations. A deterministic catalogue search returns distinct options for lowest cost, lowest added carbon, and greatest clearance.

## Demonstrate it

1. Open the welcome screen (Projects in the workspace navigation).
2. Click **Try Resilience Lab · school example**. This creates a synthetic Lyon school with explicit sample geometry and a saved comparison; it does not overwrite an existing project.
3. Under the defaults, the 42 × 28 m school needs a 0.9 m floor raise to reach a 1.1 m target elevation (0.8 m water + 0.3 m clearance).
4. Compare the EUR 190,512 standard-platform option against the EUR 227,556 reduced-carbon mix. These are demo allowances, calculated from 1,058.4 m³ × the editable rates. Added material carbon is 254.016 versus 137.592 tCO2e under the defaults; these are additional quantities, not whole-building emissions savings.
5. Select an option and switch Before/After. The confirmed footprint remains unchanged; floor/platform/equipment elevations change.
6. Raise the challenge slider past the selected option's water-level threshold. The displayed test changes from met to missed without silently modifying the proposal.
7. Click **What if my budget halves?**. A EUR 150,000 budget produces a shortfall of EUR 40,512. No failing design is applied.
8. Restore the budget or use the minimum-budget action, compare again, and apply an option. Open the simulator or export a planning report.
9. Refresh: the last saved comparison and applied elevations reopen. Challenge slider changes alone are temporary; use Redesign to save a new comparison.

To explore an alternative priority, choose **Critical equipment only** and set maximum floor raise to zero. With the default elevations and target, an additional 0.8 m equipment lift costs EUR 3,420. The UI explicitly reports that the floor remains below target.

## Calculation contract

- All elevations are absolute above the same local ground datum, entered by the user.
- Target elevation = selected water level + desired extra clearance.
- A raised floor carries the existing equipment upward by the same amount. Additional mounting is a separate intervention.
- Solid-platform volume = confirmed width × confirmed depth × added floor height.
- Platform cost/carbon = that volume × the selected mix's editable factor.
- Equipment cost/carbon = fixed allowance + additional mounting height × the per-metre factor; zero additional mounting incurs zero mounting allowance.
- For a floor-and-equipment target, both elevations must meet the target. For equipment-only, only equipment is constrained and the floor result remains visible.
- Search increments are 0.1 m. Maximum floor raise is user-limited to 0–3 m; additional equipment mounting is either disabled or searched from 0–1.5 m.
- Budget comparison uses cent-rounded cost. Clearance checks use unrounded inputs with a small numerical tolerance, not formatted display values.
- Repeated winning candidates are combined into one card with multiple objective badges.
- There is no assertion of global physical optimality: results are best within this finite, illustrative catalogue.

The catalogue excludes site-specific foundations, access works, tax, structural constraints, drainage, flood pathways, evacuation, and electrical design. Consequently, a passing vertical-clearance test is not a claim of flood safety. The existing materials points exercise remains separate from this quantified comparison.

## API and persistence

`POST /api/construction-projects/{id}/resilience/solve` accepts the typed `ResilienceInput` schema. It requires ownership of the project and blueprint, a matching project/facility/blueprint link, and confirmed geometry. If a saved conceptual model exists, its footprint and source blueprint must match. It stores an input snapshot, geometry fingerprint, unique study ID, result, and creation time under `project_data_json.resilience`.

`POST /api/construction-projects/{id}/resilience/apply` accepts a study ID and option ID. It rejects replaced studies and changed geometry, recalculates the candidates, and accepts only a currently feasible returned option. It updates project adaptations and flood settings, and saves an applied snapshot under `resilience_applied`. Submitted/stored result prices are not trusted.

A subsequent solve preserves the working design until another option is explicitly applied. The report distinguishes the latest comparison from an applied design originating from an earlier comparison. The existing project PATCH API still permits owner-managed arbitrary JSON: this is not a tamper-proof audit ledger or a multi-editor conflict-resolution system.

No schema migration or API key is required. The existing migration-chain issue documented in `CODEBASE_MAP.md` is unchanged; the app's current demo startup uses `create_all`.

## Files

- `backend/app/resilience.py`: validated inputs, editable assumptions, deterministic search.
- `backend/app/main.py`: owned project API integration and planning report sections.
- `frontend/types/resilience.ts`: frontend request/response contracts and initial assumptions.
- `frontend/components/planner/ResilienceLab.tsx` and `resilience.css`: comparison, constraint editing, challenge interaction, evidence, and apply flow.
- `ProjectPlanner.tsx`: onboarding access, sample launch, save/reopen and project selection.
- `ProjectSimulation.tsx`: adaptive scene framing, raised platform, schematic equipment marker.
- `backend/tests/test_resilience.py`: calculation boundaries, infeasibility, ownership, persistence, confirmation, stale geometry, and recalculation on apply.

Backend tests now use a temporary upload directory so generated test reports do not overwrite development reports. `UPLOAD_DIR` can also override file storage explicitly.

## Verification

The backend suite passes with 24 tests. Frontend TypeScript checking and a production build pass. A separate temporary frontend copy was used for the build to avoid changing the running development server's `.next` directory. The running API exposes both new endpoints, and the frontend returns HTTP 200.

Browser walkthrough and visual QA could not be performed because computer-use access to Chrome was denied. No screenshot-based validation is claimed. The cost/carbon inputs and the calculations were tested; actual engineering suitability and supplier pricing were not.
