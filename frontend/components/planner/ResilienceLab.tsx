"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Check, CheckCircle2, ChevronDown, CircleHelp, Download, FlaskConical, Leaf, Loader2, RotateCcw, ShieldCheck, SlidersHorizontal, Waves } from "lucide-react";
import { api } from "@/lib/api";
import { ConceptModel, ConstructionProject } from "@/types";
import { defaultResilienceInput, ResilienceAssumptions, ResilienceInput, ResilienceStudy } from "@/types/resilience";
import { ProjectSimulation } from "./ProjectSimulation";
import "./resilience.css";

const money = (n: number) => new Intl.NumberFormat("en-IE", {style: "currency", currency: "EUR", maximumFractionDigits: 0}).format(n);
const metres = (n: number) => `${n.toFixed(2)} m`;
const carbon = (kg: number) => `${(kg / 1000).toLocaleString("en", {maximumFractionDigits: 2})} tCO₂e`;
function signature(input: ResilienceInput) {
  return JSON.stringify(Object.entries(input).sort().map(([k,v]) => [k, typeof v === "object" ? Object.entries(v).sort() : v]));
}

type Props = {
  project: ConstructionProject; model: ConceptModel; blueprintId: number; siteName: string;
  study: ResilienceStudy | null; onPrepare: () => Promise<unknown>;
  onProjectUpdated: (project: ConstructionProject) => void;
  onSimulator: () => void; onReports: () => void;
};

export function ResilienceLab({project, model, blueprintId, siteName, study, onPrepare, onProjectUpdated, onSimulator, onReports}: Props) {
  const [form, setForm] = useState<ResilienceInput>(study?.input || defaultResilienceInput(blueprintId));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [challengeWater, setChallengeWater] = useState(study?.input.water_level_m ?? .8);
  const [showOriginal, setShowOriginal] = useState(false);
  useEffect(() => {
    setForm(study?.input || defaultResilienceInput(blueprintId));
    setSelectedId(study?.applied_option_id || study?.result.options[0]?.id || "");
    setChallengeWater(study?.input.water_level_m ?? .8);
  }, [study?.id, blueprintId]);
  const result = study?.result;
  const selected = result?.options.find(option => option.id === selectedId) || result?.options[0];
  const dirty = Boolean(study && signature(form) !== signature(study.input));
  const applied = selected && study?.applied_option_id === selected.id;
  const passesChallenge = Boolean(selected && challengeWater <= selected.max_water_level_m + 1e-8);
  const baseline = study?.input || form;
  const protectedLevel = selected ? (baseline.protect_floor ? Math.min(selected.floor_m, selected.equipment_m) : selected.equipment_m) : 0;

  function update<K extends keyof ResilienceInput>(key: K, value: ResilienceInput[K]) { setForm(current => ({...current, [key]: value})); }
  async function compare(override: Partial<ResilienceInput> = {}) {
    const input = {...form, ...override, blueprint_id: blueprintId};
    setForm(input); setBusy(true); setError("");
    try {
      await onPrepare();
      const updated = await api<ConstructionProject>(`/api/construction-projects/${project.id}/resilience/solve`, {method:"POST", body:JSON.stringify(input)});
      onProjectUpdated(updated);
    } catch (e) { setError(e instanceof Error ? e.message : "Comparison failed. Please try again."); }
    finally { setBusy(false); }
  }
  async function apply() {
    if (!study || !selected || dirty) return;
    setBusy(true); setError("");
    try {
      const updated = await api<ConstructionProject>(`/api/construction-projects/${project.id}/resilience/apply`, {method:"POST", body:JSON.stringify({study_id:study.id, option_id:selected.id})});
      onProjectUpdated(updated);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not apply this design."); }
    finally { setBusy(false); }
  }

  return <div className="resilience-lab">
    <header className="rl-hero">
      <div><span className="rl-eyebrow"><FlaskConical size={15}/> RESILIENCE LAB</span><h1>A better design.<br/><em>Within your budget.</em></h1><p>Compare changes. See the trade-offs. Challenge the result.</p></div>
      <div className="rl-project-context"><span><Waves size={18}/> FLOOD DESIGN EXPLORER</span><b>{project.name}</b><small>{siteName} · {model.roof_area_m2.toLocaleString()} m² footprint</small><div><i/> Confirmed blueprint geometry</div></div>
    </header>
    <div className="rl-layout">
      <aside className="rl-controls">
        <form onSubmit={e => {e.preventDefault(); void compare();}}>
          <div className="rl-panel-title"><SlidersHorizontal size={18}/><h2>Your constraints</h2><span>01</span></div>
          <fieldset disabled={busy}>
            <label className="rl-budget-label">Adaptation budget<span className="rl-money-input"><b>€</b><input aria-label="Adaptation budget" type="number" min={0} max={10000000} step={100} required value={form.budget_eur} onChange={e=>update("budget_eur", +e.target.value)}/></span></label>
            <div className="rl-two-fields"><NumberField label="Water level (m)" value={form.water_level_m} min={0} max={5} step={.1} onChange={v=>update("water_level_m",v)}/><NumberField label="Extra clearance (m)" value={form.freeboard_m} min={0} max={1} step={.1} onChange={v=>update("freeboard_m",v)}/></div>
            <p className="rl-help">A hypothetical water level above local ground. Extra clearance is your chosen margin.</p>
            <label>What must meet the target?<select aria-label="Protection target" value={form.protect_floor ? "both" : "equipment"} onChange={e=>update("protect_floor",e.target.value==="both")}><option value="both">Floor + critical equipment</option><option value="equipment">Critical equipment only</option></select></label>
            {!form.protect_floor && <p className="rl-inline-note">Equipment-only options can leave the building floor exposed.</p>}
            <div className="rl-two-fields"><NumberField label="Current floor (m)" value={form.baseline_floor_m} min={0} max={5} step={.1} onChange={v=>update("baseline_floor_m",v)}/><NumberField label="Equipment level (m)" value={form.baseline_equipment_m} min={form.baseline_floor_m} max={8} step={.1} onChange={v=>update("baseline_equipment_m",v)}/></div>
            <NumberField label="Maximum floor raise (m)" value={form.max_raise_m} min={0} max={3} step={.1} onChange={v=>update("max_raise_m",v)}/>
            <label className="rl-checkbox"><input type="checkbox" checked={form.allow_equipment_raise} onChange={e=>update("allow_equipment_raise",e.target.checked)}/>Allow additional equipment mounting</label>
            <details className="rl-assumption-editor"><summary>Cost & carbon assumptions <ChevronDown size={14}/></summary><p>Editable demo allowances, not supplier quotes. Additional works are excluded.</p>{([
              ["standard_cost_m3","Standard platform · €/m³"], ["lower_carbon_cost_m3","Reduced-carbon mix · €/m³"],
              ["standard_carbon_kg_m3","Standard · kgCO₂e/m³"], ["lower_carbon_kg_m3","Reduced-carbon · kgCO₂e/m³"],
              ["equipment_fixed_cost","Equipment setup · €"], ["equipment_cost_m","Equipment lift · €/m"],
              ["equipment_fixed_carbon_kg","Equipment setup · kgCO₂e"], ["equipment_carbon_kg_m","Equipment lift · kgCO₂e/m"],
            ] as [keyof ResilienceAssumptions,string][]).map(([key,label])=><NumberField key={key} label={label} value={form.assumptions[key]} min={key==="standard_cost_m3"||key==="lower_carbon_cost_m3" ? 1 : 0} max={key.includes("cost") && key.startsWith("equipment") ? 100000 : 10000} step={1} onChange={v=>update("assumptions",{...form.assumptions,[key]:v})}/>)}</details>
            <button className="rl-compare" type="submit">{busy?<Loader2 className="rl-spin" size={18}/>:<FlaskConical size={18}/>} {busy?"Comparing designs…":"Compare design options"}<ArrowRight size={17}/></button>
          </fieldset>
        </form>
        <p className="rl-save-note"><Check size={13}/> Comparisons and applied designs are saved.</p>
      </aside>
      <section className="rl-results" aria-busy={busy}>
        {error&&<div role="alert" className="rl-error">{error}</div>}
        {dirty&&<div role="status" className="rl-dirty">Your inputs changed. Compare again to update these saved results.</div>}
        {!result?<div className="rl-empty"><div className="rl-empty-icon"><FlaskConical size={34}/></div><span className="rl-eyebrow">YOUR NEXT DESIGN DECISION</span><h2>What should you change first?</h2><p>We compare floor elevation, platform materials and equipment placement against your budget and clearance target.</p><div className="rl-empty-steps"><span><b>01</b>Set a budget</span><span><b>02</b>Compare alternatives</span><span><b>03</b>Challenge your design</span></div><p className="rl-small">Calculations use confirmed geometry and visible cost and carbon assumptions.</p></div>:<>
          <div className="rl-results-heading"><div><span className="rl-eyebrow">02 · DESIGN ALTERNATIVES</span><h2>{result.status==="feasible" ? `${result.options.length} ${result.options.length===1?"option meets":"options meet"} your constraints` : "A useful answer, even when it’s no."}</h2></div><span className="rl-count">{result.evaluated_count.toLocaleString()} combinations checked</span></div>
          <div className="rl-baseline"><span className={result.baseline.meets_target?"rl-pass":"rl-fail"}>{result.baseline.meets_target?<CheckCircle2 size={16}/>:<Waves size={16}/>}Original design {result.baseline.meets_target?"meets":"misses"} your target</span><small>Target elevation {metres(result.target_elevation_m)} · Floor {metres(result.baseline.floor_m)} · Equipment {metres(result.baseline.equipment_m)}</small></div>
          {result.status!=="feasible"?<div className="rl-infeasible"><CircleHelp size={30}/><h3>{result.status==="budget_shortfall"?"The budget is the limiting constraint.":"The height limits block this target."}</h3><p>{result.status==="budget_shortfall"?`The least expensive supported option costs ${money(result.minimum_budget_eur!)}. You would need ${money(result.budget_gap_eur!)} more under these assumptions.`:baseline.protect_floor?`Meeting the selected floor target requires at least ${metres(result.required_floor_raise_m)} of floor raise. Your limit is ${metres(baseline.max_raise_m)}.`:"The permitted floor and equipment raises cannot reach the selected equipment target."}</p><div>{result.status==="budget_shortfall"&&<button disabled={busy||dirty} onClick={()=>compare({budget_eur:result.minimum_budget_eur!})}>Compare at {money(result.minimum_budget_eur!)}<ArrowRight size={15}/></button>}{result.status==="height_limit"&&baseline.protect_floor&&result.required_floor_raise_m<=3&&<button disabled={busy||dirty} onClick={()=>compare({max_raise_m:result.required_floor_raise_m})}>Allow {metres(result.required_floor_raise_m)} raise<ArrowRight size={15}/></button>}<small>No option has been applied. Change a constraint to explore again.</small></div></div>:<>
            <div className="rl-options">{result.options.map((option,index)=><button key={option.id} className={`rl-option ${selected?.id===option.id?"selected":""}`} onClick={()=>setSelectedId(option.id)} aria-pressed={selected?.id===option.id}><div className="rl-option-top"><span>OPTION {String(index+1).padStart(2,"0")}</span>{selected?.id===option.id?<CheckCircle2 size={18}/>:<span className="rl-radio"/>}</div><h3>{option.badges[0]}</h3><strong>{money(option.cost_eur)}</strong><p>{option.floor_raise_m ? `Raise floor ${metres(option.floor_raise_m)}` : "Keep current floor"}{option.equipment_raise_m>0&&` · equipment +${metres(option.equipment_raise_m)}`}</p><div className="rl-option-metrics"><span><Leaf size={14}/>{carbon(option.added_carbon_kg)} added</span><span><Waves size={14}/>{metres(option.clearance_m)} clearance</span></div><small>{option.name}{option.badges.length>1?` · Also ${option.badges.slice(1).join(" & ").toLowerCase()}`:""}</small></button>)}</div>
            {selected&&<>
              <section className="rl-preview"><div className="rl-preview-head"><div><span className="rl-eyebrow">03 · SEE THE CHANGE</span><h3>{showOriginal?"Original design":"Proposed design"}</h3></div><div className="rl-toggle"><button aria-pressed={showOriginal} onClick={()=>setShowOriginal(true)}>Before</button><button aria-pressed={!showOriginal} onClick={()=>setShowOriginal(false)}>After</button></div></div><div className="rl-canvas"><ProjectSimulation model={model} hazard="flood" intensity={challengeWater} floorElevation={showOriginal?baseline.baseline_floor_m:selected.floor_m} equipmentElevation={showOriginal?baseline.baseline_equipment_m:selected.equipment_m} showPlatform={!showOriginal&&selected.floor_raise_m>0} playing={false}/><div className="rl-canvas-label"><span>{showOriginal?"ORIGINAL":"PROPOSAL"}</span><b>Floor {metres(showOriginal?baseline.baseline_floor_m:selected.floor_m)}</b><small>Water {metres(challengeWater)} · drag to orbit</small></div></div><p className="rl-scene-note">Yellow marker: critical equipment. Placement is schematic; elevations use your inputs.</p></section>
              <section className="rl-challenge"><div><span className="rl-eyebrow">04 · CHALLENGE THE RESULT</span><h3>What if the water rises?</h3><p>Test this exact proposal without silently redesigning it.</p></div><strong className={passesChallenge?"rl-pass":"rl-fail"}>{passesChallenge?<ShieldCheck size={19}/>:<Waves size={19}/>} {passesChallenge?"Selected target met":"Selected target missed"}</strong><label className="rl-water-slider">Challenge water level <b>{metres(challengeWater)}</b><input aria-label="Challenge water level" type="range" min={0} max={5} step={.1} value={challengeWater} onChange={e=>setChallengeWater(+e.target.value)}/></label><div className="rl-challenge-details"><span>Target met up to <b>{metres(selected.max_water_level_m)}</b> water</span><span>Current clearance <b>{metres(protectedLevel-challengeWater)}</b></span><span>Required margin <b>{metres(baseline.freeboard_m)}</b></span></div>{!baseline.protect_floor&&<p className="rl-inline-note">This checks equipment only. Floor {selected.floor_m >= challengeWater+baseline.freeboard_m ? "meets" : "misses"} the same clearance target.</p>}<div className="rl-challenge-actions"><button disabled={busy||dirty} onClick={()=>compare({water_level_m:challengeWater})}>Redesign for this water level<ArrowRight size={14}/></button><button disabled={busy||dirty} onClick={()=>compare({budget_eur:Math.floor(baseline.budget_eur/2)})}>What if my budget halves?</button><button aria-label="Reset challenge water level" onClick={()=>setChallengeWater(baseline.water_level_m)}><RotateCcw size={14}/></button></div>{challengeWater!==baseline.water_level_m&&<small className="rl-challenge-note">Unsaved stress test. Apply uses the original {metres(baseline.water_level_m)} comparison; redesign to save this level.</small>}</section>
              <details className="rl-evidence"><summary><CircleHelp size={17}/>Show me the calculation<ChevronDown size={16}/></summary><div><EvidenceRow label="Confirmed footprint" value={`${model.footprint_m.width} × ${model.footprint_m.depth} = ${result.area_m2.toLocaleString()} m²`}/><EvidenceRow label="Platform volume" value={`${result.area_m2.toLocaleString()} m² × ${selected.floor_raise_m} m = ${selected.volume_m3.toLocaleString()} m³`}/><EvidenceRow label="Platform allowance" value={`${selected.volume_m3.toLocaleString()} m³ × ${selected.material==="none"?0:baseline.assumptions[selected.material==="standard"?"standard_cost_m3":"lower_carbon_cost_m3"]} €/m³ = ${money(selected.platform_cost_eur)}`}/><EvidenceRow label="Equipment allowance" value={selected.equipment_raise_m?`${money(baseline.assumptions.equipment_fixed_cost)} + ${selected.equipment_raise_m} m × ${money(baseline.assumptions.equipment_cost_m)}/m = ${money(selected.equipment_cost_eur)}`:"No additional mounting"}/><EvidenceRow label="Total adaptation allowance" value={`${money(selected.cost_eur)} / ${money(baseline.budget_eur)} budget`}/><EvidenceRow label="Added carbon estimate" value={`${selected.volume_m3.toLocaleString()} m³ × ${selected.material==="none"?0:baseline.assumptions[selected.material==="standard"?"standard_carbon_kg_m3":"lower_carbon_kg_m3"]} kgCO₂e/m³${selected.equipment_raise_m ? ` + ${baseline.assumptions.equipment_fixed_carbon_kg} + ${selected.equipment_raise_m} × ${baseline.assumptions.equipment_carbon_kg_m} kgCO₂e` : ""} = ${carbon(selected.added_carbon_kg)}`}/><EvidenceRow label="Saved clearance test" value={`${baseline.protect_floor?"min(floor, equipment)":"equipment"} − ${baseline.water_level_m} m ≥ ${baseline.freeboard_m} m`}/></div></details>
              <div className="rl-apply-bar"><div><b>{applied?"This design is applied to your project.":"Make this your working design."}</b><span>{applied?"Saved elevations are ready in the simulator and report.":"Your original blueprint dimensions stay intact."}</span></div><button className="rl-compare" disabled={busy||dirty||Boolean(applied)} onClick={apply}>{applied?<Check size={17}/>:<ArrowRight size={17}/>} {applied?"Applied & saved":"Apply this design"}</button>{applied&&<button className="rl-link-button" onClick={onSimulator}>Open simulator<ArrowRight size={15}/></button>}</div>
            </>}
          </>}
          <details className="rl-scope"><summary>What this comparison includes<ChevronDown size={14}/></summary><ul>{result.assumptions.map(item=><li key={item}>{item}</li>)}</ul></details>
          <div className="rl-footer"><span><Check size={14}/>Comparison saved · {new Date(study!.created_at).toLocaleString()}</span><button onClick={onReports}><Download size={15}/>Planning report<ArrowRight size={14}/></button></div>
        </>}
      </section>
    </div>
    <p className="rl-disclaimer">Conceptual design comparison. Demo cost and carbon assumptions. Vertical clearance does not establish flood safety or engineering suitability.</p>
  </div>;
}

function NumberField({label,value,min,max,step,onChange}:{label:string;value:number;min:number;max:number;step:number;onChange:(v:number)=>void}) {
  return <label>{label}<input type="number" aria-label={label} required min={min} max={max} step={step} value={value} onChange={e=>onChange(+e.target.value)}/></label>;
}
function EvidenceRow({label,value}:{label:string;value:string}) {return <div className="rl-evidence-row"><span>{label}</span><b>{value}</b></div>;}
