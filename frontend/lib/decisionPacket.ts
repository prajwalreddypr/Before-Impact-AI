import { SavedDesign, StressResult } from "@/types/studio";

export const money = (n:number) => new Intl.NumberFormat("en-IE", {style:"currency",currency:"EUR",maximumFractionDigits:0}).format(n);
export const tonnes = (n:number) => `${(n/1000).toFixed(2)} tCO₂e`;

export function decisionPacket(projectName:string, designs:SavedDesign[], selected:SavedDesign, stress:StressResult|null) {
  const input=selected.input, option=selected.option, evidence=selected.site_evidence;
  const lines=[`# ${projectName} — decision brief`, `Exported: ${new Date().toISOString()}`, "",
    "Conceptual planning comparison. Prices and carbon factors are editable illustrative assumptions. This document does not establish engineering safety, permission to build, or a flood forecast.", "",
    `## Selected for discussion: ${selected.name}`, `Saved: ${selected.created_at} | Solver: ${selected.solver_version}`, "",
    `Footprint: ${selected.geometry.width_m} × ${selected.geometry.depth_m} m; ${selected.geometry.floors} floors.`,
    `Water scenario: ${input.water_level_m} m; clearance margin: ${input.freeboard_m} m; budget: ${money(input.budget_eur)}.`,
    `Protection target: ${input.protect_floor?"floor and equipment":"equipment only; floor may flood"}. Maximum floor lift: ${input.max_raise_m} m.`,
    `Baseline elevations: floor ${input.baseline_floor_m} m; equipment ${input.baseline_equipment_m} m.`,
    `Proposed elevations: floor ${option.floor_m} m; equipment ${option.equipment_m} m.`,
    `Adaptation estimate: ${money(option.cost_eur)}; added carbon: ${tonnes(option.added_carbon_kg)}.`,
    `Highest water level meeting the chosen margin: ${option.max_water_level_m} m. All elevations use the same local ground datum.`, "",
    "## Site evidence at the time this design was saved"];
  if(evidence) lines.push(`Address: ${evidence.address.label} (${evidence.address.precision}); INSEE ${evidence.address.citycode}.`,
    `Coordinates: ${evidence.address.latitude}, ${evidence.address.longitude}. Retrieved: ${evidence.retrieved_at}.`,
    `Status: ${evidence.status}. ${evidence.scope}`, `IGN address source: ${evidence.address_source}`, `Géorisques source: ${evidence.risk_source}`,
    ...evidence.risks.map(r=>`- ${r}`));
  else lines.push("No official site evidence was attached when this design was saved.");
  lines.push("", "## Saved alternatives", "Each row retains its own geometry, budget, water level and margin. Compare those before drawing conclusions.", "",
    "| Design | Footprint m | Water m | Margin m | Budget EUR | Cost EUR | Added kgCO2e | Target |", "|---|---|---:|---:|---:|---:|---:|---|");
  for(const d of designs) lines.push(`| ${d.name.replace(/[|\n]/g," ")} | ${d.geometry.width_m} × ${d.geometry.depth_m} | ${d.input.water_level_m} | ${d.input.freeboard_m} | ${d.input.budget_eur} | ${d.option.cost_eur} | ${d.option.added_carbon_kg} | ${d.input.protect_floor?"Floor + equipment":"Equipment only"} |`);
  if(stress?.design_id===selected.id) {
    lines.push("", "## Fixed-design stress test", `Tested: ${stress.tested_at}`, stress.notice, `${stress.passing_count}/${stress.total_count} tested combinations meet both constraints. This fraction is not a probability.`,
      "", "| Water m | Cost increase % | Cost EUR | Result |", "|---:|---:|---:|---|");
    for(const c of stress.cells) lines.push(`| ${c.water_m} | ${c.increase_pct} | ${c.cost_eur} | ${c.reason} |`);
  }
  lines.push("", "## Calculation inputs", "Platform volume = footprint × floor lift. Platform cost/carbon = volume × unit factor. Equipment rises with the floor; extra mounting uses fixed plus height-based allowances.",
    ...Object.entries(input.assumptions).map(([key,value])=>`- ${key}: ${value}`), "",
    "## Verification still required", "- Site-specific design flood level and common elevation datum.", "- Surveyed dimensions, structural and foundation design.", "- Drainage, access, evacuation, utilities and planning constraints.", "- Supplier quotes and verified carbon declarations; access works, foundations and tax are excluded.",
    "- Municipal hazard listings do not prove parcel-level exposure or absence of risk.", "", `Geometry fingerprint: ${selected.geometry_fingerprint}`);
  return lines.join("\n");
}

export function downloadPacket(filename:string, content:string) {
  const url=URL.createObjectURL(new Blob([content],{type:"text/markdown;charset=utf-8"}));
  const link=document.createElement("a");link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
