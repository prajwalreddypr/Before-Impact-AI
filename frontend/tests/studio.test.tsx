import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DecisionStudio } from "@/components/planner/DecisionStudio";
import { api } from "@/lib/api";
import { decisionPacket } from "@/lib/decisionPacket";
import { defaultResilienceInput } from "@/types/resilience";
import { ConstructionProject } from "@/types";
import { SavedDesign, StressResult } from "@/types/studio";

vi.mock("@/lib/api",()=>({api:vi.fn()}));
const input=defaultResilienceInput(7);
const option={id:"standard-9-0",material:"standard",name:"Standard platform",badges:["Lowest cost"],floor_raise_m:.9,equipment_raise_m:0,floor_m:1.1,equipment_m:1.2,volume_m3:1058.4,platform_cost_eur:190512,equipment_cost_eur:0,cost_eur:190512,added_carbon_kg:254016,clearance_m:.3,max_water_level_m:.8,meets_target:true,floor_meets_target:true,equipment_meets_target:true};
const design:SavedDesign={id:"design-1",name:"School first proposal",created_at:"2026-10-25T12:00:00Z",input,option,geometry:{width_m:42,depth_m:28,floors:2},geometry_fingerprint:"geometry-1",site_evidence:null,solver_version:"flood-options-1.0"};
const stress:StressResult={design_id:design.id,tested_at:"2026-10-25T12:10:00Z",water_levels:[.8,1.2],cost_increases_pct:[0,50],cells:[{water_m:.8,increase_pct:0,cost_eur:190512,water_pass:true,budget_pass:true,pass:true,reason:"Meets both"},{water_m:.8,increase_pct:50,cost_eur:285768,water_pass:true,budget_pass:true,pass:true,reason:"Meets both"},{water_m:1.2,increase_pct:0,cost_eur:190512,water_pass:false,budget_pass:true,pass:false,reason:"Water clearance"},{water_m:1.2,increase_pct:50,cost_eur:285768,water_pass:false,budget_pass:true,pass:false,reason:"Water clearance"}],passing_count:2,total_count:4,max_water_level_m:.8,max_cost_increase_pct:57.47,option,budget_eur:300000,freeboard_m:.3,protect_floor:true,notice:"This grid is not a probability or forecast."};
function project(library:SavedDesign[]=[]):ConstructionProject{return {id:9,name:"Climate-ready school",building_type:"School",region:"France",entry_mode:"find",active_section:"studio",selected_site_ids:[],created_at:"2026-10-25",updated_at:"2026-10-25",data:{blueprint:{id:7},model:{},design_library:library,resilience:{id:"study-1",input,result:{options:[option]}}}}}
function mount(p=project()){
  const props={project:p,onPrepare:vi.fn().mockResolvedValue(p),onProjectUpdated:vi.fn(),onOpenLab:vi.fn(),onBusyChange:vi.fn()};
  render(<DecisionStudio {...props}/>);return props;
}
beforeEach(()=>vi.mocked(api).mockReset());
afterEach(cleanup);

describe("Decision Studio flows",()=>{
  it("requires reviewing the brief before solving and preserves the selected blueprint",async()=>{
    const user=userEvent.setup(),props=mount();
    vi.mocked(api).mockResolvedValueOnce({mode:"local_parser",input:{...input,budget_eur:250000},extracted:["budget_eur"],notes:[],unparsed_notice:"Only supported constraints changed."});
    await user.click(screen.getByRole("button",{name:/Review extracted constraints/}));
    await screen.findByRole("button",{name:/Confirm & generate/});
    expect(vi.mocked(api).mock.calls).toHaveLength(1);
    await user.clear(screen.getByLabelText(/Adaptation budget/));
    await user.type(screen.getByLabelText(/Adaptation budget/),"240000");
    vi.mocked(api).mockResolvedValueOnce(project()).mockResolvedValueOnce(project());
    await user.click(screen.getByRole("button",{name:/Confirm & generate/}));
    await waitFor(()=>expect(props.onProjectUpdated).toHaveBeenCalled());
    const solve=vi.mocked(api).mock.calls.find(([url])=>url.endsWith("/resilience/solve"))!;
    expect(JSON.parse(solve[1]!.body as string)).toMatchObject({budget_eur:240000,blueprint_id:7});
    expect(props.onPrepare).toHaveBeenCalledOnce();
    expect(screen.getByRole("heading",{name:/A decision deserves a memory/})).toBeTruthy();
  });

  it("shows provider errors and does not invent address results",async()=>{
    const user=userEvent.setup();mount();
    await user.click(screen.getByRole("button",{name:/Site evidence/}));
    vi.mocked(api).mockRejectedValueOnce(new Error("Address search temporarily unavailable"));
    await user.click(screen.getByRole("button",{name:"Search"}));
    expect((await screen.findByRole("alert")).textContent).toContain("unavailable");
    expect(screen.getByText("No official evidence attached")).toBeTruthy();
  });

  it("attaches the selected server address using the exact searched query",async()=>{
    const user=userEvent.setup(),props=mount();
    await user.click(screen.getByRole("button",{name:/Site evidence/}));
    vi.mocked(api).mockResolvedValueOnce({addresses:[{id:"69123",label:"Lyon",citycode:"69123",latitude:45.758,longitude:4.835,precision:"municipality"}]});
    await user.click(screen.getByRole("button",{name:"Search"}));
    const address=await screen.findByRole("button",{name:/Lyon municipality/});
    vi.mocked(api).mockResolvedValueOnce(project());
    await user.click(address);
    await waitFor(()=>expect(props.onProjectUpdated).toHaveBeenCalled());
    const request=vi.mocked(api).mock.calls.at(-1)!;
    expect(request[0]).toBe("/api/construction-projects/9/studio/site");
    expect(JSON.parse(request[1]!.body as string)).toEqual({query:"Lyon",address_id:"69123"});
  });

  it("saves a named alternative using a study and option id, never submitted prices",async()=>{
    const user=userEvent.setup(),props=mount();
    await user.click(screen.getByRole("button",{name:/Design library/}));
    await user.type(screen.getByLabelText(/Name prefix/),"Round one");
    vi.mocked(api).mockResolvedValueOnce(project([design]));
    await user.click(screen.getByRole("button",{name:/Save alternative/}));
    await waitFor(()=>expect(props.onProjectUpdated).toHaveBeenCalled());
    expect(JSON.parse(vi.mocked(api).mock.calls[0][1]!.body as string)).toEqual({name:"Round one · Lowest cost",study_id:"study-1",option_id:option.id});
  });

  it("runs a fixed design stress grid and presents failure reasons",async()=>{
    const user=userEvent.setup(),props=mount(project([design]));
    await user.click(screen.getByRole("button",{name:/Stress tests/}));
    vi.mocked(api).mockResolvedValueOnce({...stress,project:project([{...design,last_stress:stress}])});
    await user.click(screen.getByRole("button",{name:/Run 24 scenarios/}));
    const table=await screen.findByRole("table",{name:/Water level ×/});
    expect(within(table).getAllByText(/Water clearance/)).toHaveLength(2);
    const body=JSON.parse(vi.mocked(api).mock.calls[0][1]!.body as string);
    expect(body.water_levels).toHaveLength(6);expect(body.cost_increases_pct).toHaveLength(4);
    expect(props.onProjectUpdated).toHaveBeenCalled();
  });

  it("reopens saved stress evidence and supports keyboard presentation and focus return",async()=>{
    const user=userEvent.setup();mount(project([{...design,last_stress:stress}]));
    await user.click(screen.getByRole("button",{name:/Decision story/}));
    const start=screen.getByRole("button",{name:/Present decision/});
    await user.click(start);
    expect(screen.getByRole("dialog")).toBeTruthy();
    await user.keyboard("{ArrowRight}{ArrowRight}{ArrowRight}{ArrowRight}");
    expect(screen.getByRole("heading",{name:/Challenge the proposal/})).toBeTruthy();
    expect(screen.getByText("2/4")).toBeTruthy();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();expect(document.activeElement).toBe(start);
  });
});

it("exports original design inputs, provenance and only the matching stress grid",()=>{
  const evidence={address:{id:"69123",label:"Lyon",citycode:"69123",latitude:45.758,longitude:4.835,precision:"municipality"},retrieved_at:"2026-10-25",address_source:"https://data.geopf.fr/geocodage/search",risk_source:"https://www.georisques.gouv.fr/api/v1/gaspar/risques?code_insee=69123",scope:"Municipality only",status:"available" as const,risks:["Inondation"]};
  const selected={...design,site_evidence:evidence};
  const document=decisionPacket("School",[selected],selected,stress);
  expect(document).toContain(evidence.risk_source);expect(document).toContain("standard_cost_m3: 180");expect(document).toContain("2/4 tested combinations");expect(document).toContain("geometry-1");
  expect(decisionPacket("School",[selected],selected,{...stress,design_id:"other"})).not.toContain("## Fixed-design stress test");
});
