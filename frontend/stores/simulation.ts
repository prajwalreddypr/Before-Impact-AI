import { create } from "zustand";

type SimulationState = {
  selectedFacilityId:number|null; selectedEventId:number|null; selectedTimestamp:number;
  playbackStatus:"playing"|"paused"; playbackSpeed:1|2|4; selectedAssetId:number|null;
  selectedActions:number[]; cameraMode:"perspective"|"top";
  setFacility:(id:number)=>void; setEvent:(id:number)=>void; setTimestamp:(index:number)=>void;
  setPlayback:(status:"playing"|"paused")=>void; setSpeed:(speed:1|2|4)=>void;
  selectAsset:(id:number|null)=>void; toggleAction:(id:number, active:boolean)=>void;
  setCameraMode:(mode:"perspective"|"top")=>void;
};

export const useSimulation = create<SimulationState>((set) => ({
  selectedFacilityId:null, selectedEventId:null, selectedTimestamp:0, playbackStatus:"paused", playbackSpeed:1,
  selectedAssetId:null, selectedActions:[], cameraMode:"perspective",
  setFacility:(id)=>set({selectedFacilityId:id, selectedEventId:null, selectedTimestamp:0, selectedActions:[]}),
  setEvent:(id)=>set({selectedEventId:id, selectedTimestamp:0, playbackStatus:"paused", selectedActions:[]}),
  setTimestamp:(index)=>set({selectedTimestamp:index}), setPlayback:(status)=>set({playbackStatus:status}),
  setSpeed:(speed)=>set({playbackSpeed:speed}), selectAsset:(id)=>set({selectedAssetId:id}),
  toggleAction:(id,active)=>set(s=>({selectedActions:active?[...new Set([...s.selectedActions,id])]:s.selectedActions.filter(x=>x!==id)})),
  setCameraMode:(mode)=>set({cameraMode:mode}),
}));
