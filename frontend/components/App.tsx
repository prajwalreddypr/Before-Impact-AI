"use client";

import { useEffect, useState } from "react";
import { BarChart3, Building2, ChevronDown, CloudSun, FileText, LogOut, Map, Menu, Radar, X } from "lucide-react";
import { api } from "@/lib/api";
import { Facility } from "@/types";
import { useSimulation } from "@/stores/simulation";
import { Overview } from "./Overview";
import { StormTwin } from "./stormtwin/StormTwin";
import { Explore } from "./Explore";
import { Sites } from "./Sites";
import { Reports } from "./Reports";

export type View = "overview"|"explore"|"stormtwin"|"sites"|"reports";
const NAV:{id:View;label:string;icon:typeof BarChart3}[]=[
  {id:"overview",label:"Overview",icon:BarChart3},{id:"explore",label:"Explore",icon:Map},{id:"stormtwin",label:"StormTwin",icon:Radar},{id:"sites",label:"My Sites",icon:Building2},{id:"reports",label:"Reports",icon:FileText}
];

export function App({onLogout}:{onLogout:()=>void}) {
  const [view,setView]=useState<View>("overview"); const [facilities,setFacilities]=useState<Facility[]>([]); const [mobile,setMobile]=useState(false); const [loading,setLoading]=useState(true);
  const {selectedFacilityId,setFacility}=useSimulation();
  const refresh=()=>api<Facility[]>("/api/facilities").then(rows=>{setFacilities(rows);if(!selectedFacilityId&&rows[0])setFacility(rows[0].id)}).finally(()=>setLoading(false));
  useEffect(()=>{refresh()},[]); const selected=facilities.find(f=>f.id===selectedFacilityId);
  return <div className="app-shell">
    <header className="topbar"><button className="mobile-menu" onClick={()=>setMobile(!mobile)} aria-label="Toggle navigation">{mobile?<X/>:<Menu/>}</button><div className="brand"><span className="logo-mark">B</span><span>BeforeImpact</span></div><nav className={mobile?"open":""}>{NAV.map(item=><button key={item.id} className={view===item.id?"active":""} onClick={()=>{setView(item.id);setMobile(false)}}><item.icon size={16}/>{item.label}</button>)}</nav><div className="top-actions"><label className="facility-select"><span className="status-dot"/><select value={selectedFacilityId||""} onChange={e=>setFacility(Number(e.target.value))}>{facilities.map(f=><option key={f.id} value={f.id}>{f.name}</option>)}</select><ChevronDown size={14}/></label><div className="weather-chip"><CloudSun size={17}/><span>14°</span><small>Synthetic</small></div><button className="avatar" title="Sign out" onClick={onLogout}>AM<span className="logout-tip"><LogOut size={13}/> Sign out</span></button></div></header>
    <main className={view==="stormtwin"?"main storm-main":"main"}>
      {loading?<div className="page-loading"><span/><span/><span/></div>:selected&&<>
        {view==="overview"&&<Overview facility={selected} onOpenStormTwin={()=>setView("stormtwin")} onOpenReports={()=>setView("reports")}/>} 
        {view==="explore"&&<Explore facilities={facilities} selected={selected} onSelect={id=>{setFacility(id);setView("overview")}} onCreated={()=>{refresh();setView("sites")}}/>}
        {view==="stormtwin"&&<StormTwin facility={selected}/>} 
        {view==="sites"&&<Sites facilities={facilities} selected={selected} onChanged={refresh} onSelect={setFacility}/>} 
        {view==="reports"&&<Reports facility={selected}/>} 
      </>}
    </main>
  </div>;
}
