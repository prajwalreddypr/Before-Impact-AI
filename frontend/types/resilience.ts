export type ResilienceAssumptions = {
  standard_cost_m3: number; lower_carbon_cost_m3: number;
  standard_carbon_kg_m3: number; lower_carbon_kg_m3: number;
  equipment_fixed_cost: number; equipment_cost_m: number;
  equipment_fixed_carbon_kg: number; equipment_carbon_kg_m: number;
};
export type ResilienceInput = {
  blueprint_id: number; budget_eur: number; water_level_m: number; freeboard_m: number;
  baseline_floor_m: number; baseline_equipment_m: number; max_raise_m: number;
  allow_equipment_raise: boolean; protect_floor: boolean; assumptions: ResilienceAssumptions;
};
export type ResilienceOption = {
  id: string; material: string; name: string; badges: string[];
  floor_raise_m: number; equipment_raise_m: number; floor_m: number; equipment_m: number;
  volume_m3: number; platform_cost_eur: number; equipment_cost_eur: number;
  cost_eur: number; added_carbon_kg: number; clearance_m: number; max_water_level_m: number;
  meets_target: boolean; floor_meets_target: boolean; equipment_meets_target: boolean;
};
export type ResilienceStudy = {
  id: string; created_at: string; input: ResilienceInput; applied_option_id: string | null;
  result: {
    version: string; geometry_fingerprint: string; status: "feasible" | "budget_shortfall" | "height_limit";
    area_m2: number; target_elevation_m: number; evaluated_count: number; feasible_count: number;
    baseline: {floor_m: number; equipment_m: number; clearance_m: number; meets_target: boolean};
    required_floor_raise_m: number; minimum_budget_eur: number | null; budget_gap_eur: number | null;
    options: ResilienceOption[]; assumptions: string[];
  };
};
export function defaultResilienceInput(blueprintId: number): ResilienceInput {
  return {
    blueprint_id: blueprintId, budget_eur: 300000, water_level_m: .8, freeboard_m: .3,
    baseline_floor_m: .2, baseline_equipment_m: .3, max_raise_m: 1.5,
    allow_equipment_raise: true, protect_floor: true,
    assumptions: {standard_cost_m3: 180, lower_carbon_cost_m3: 215,
      standard_carbon_kg_m3: 240, lower_carbon_kg_m3: 130,
      equipment_fixed_cost: 1500, equipment_cost_m: 2400,
      equipment_fixed_carbon_kg: 80, equipment_carbon_kg_m: 60},
  };
}
