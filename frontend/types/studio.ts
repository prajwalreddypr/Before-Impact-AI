import { ResilienceInput, ResilienceOption } from "./resilience";

export type AddressResult = {id:string;label:string;citycode:string;latitude:number;longitude:number;precision:string};
export type SiteEvidence = {
  address:AddressResult;retrieved_at:string;address_source:string;risk_source:string;
  scope:string;status:"available"|"unavailable"|"no_record";risks:string[];
};
export type SavedDesign = {
  id:string;name:string;created_at:string;input:ResilienceInput;option:ResilienceOption;
  geometry:{width_m:number;depth_m:number;floors:number};geometry_fingerprint:string;
  site_evidence:SiteEvidence|null;solver_version:string;
  last_stress?:StressResult;
};
export type BriefPreview = {mode:string;input:ResilienceInput;extracted:string[];notes:string[];unparsed_notice:string};
export type StressResult = {
  design_id:string;tested_at:string;water_levels:number[];cost_increases_pct:number[];
  cells:{water_m:number;increase_pct:number;cost_eur:number;water_pass:boolean;budget_pass:boolean;pass:boolean;reason:string}[];
  passing_count:number;total_count:number;max_water_level_m:number;max_cost_increase_pct:number|null;
  option:ResilienceOption;budget_eur:number;freeboard_m:number;protect_floor:boolean;notice:string;
};
