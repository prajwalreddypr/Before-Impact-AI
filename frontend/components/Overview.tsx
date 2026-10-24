"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Check, ClipboardCheck, CloudRain, Flame, Play, Radar, Share2, SunMedium, ThermometerSun, UserRound, Waves, Wind, X } from "lucide-react";
import { api } from "@/lib/api";
import { Asset, Facility, Plan, Scenario, Warning } from "@/types";

const hazardIcons:Record<string,typeof Wind>={wind:Wind,flood:Waves,rain:CloudRain,heat:ThermometerSun,wildfire:Flame,drought:SunMedium};
const hazardLabels:Record<string,string>={wind:"Storm",flood:"Flood",rain:"Heavy rain",heat:"Extreme heat",wildfire:"Fire weather",drought:"Drought"};
const owners=["Unassigned","Site lead","Operations","Maintenance"];

export function Overview({facility,onOpenTwin,onOpenWarning}:{facility:Facility;onOpenTwin:()=>void;onOpenWarning:(facilityId:number,eventId:number)=>void}) {
  const [assets,setAssets]=useState<Asset[]>([]); const [scenarios,setScenarios]=useState<Scenario[]>([]); const [warnings,setWarnings]=useState<Warning[]>([]); const [active,setActive]=useState<Warning|null>(null); const [plan,setPlan]=useState<Plan|null>(null); const [busy,setBusy]=useState(false); const [toast,setToast]=useState("");
  useEffect(()=>{Promise.all([api<Asset[]>(`/api/facilities/${facility.id}/assets`),api<Scenario[]>(`/api/facilities/${facility.id}/scenarios`),api<{warnings:Warning[]}>("/api/warnings")]).then(([a,s,w])=>{setAssets(a);setScenarios(s);setWarnings(w.warnings)})},[facility.id]);
  useEffect(()=>{if(active)api<Asset[]>(`/api/facilities/${active.facility_id}/assets`).then(setAssets)},[active?.id]);
  async function startResponse(){if(!active)return;setBusy(true);setPlan(await api(`/api/events/${active.weather_event_id}/generate-plan`,{method:"POST"}));setBusy(false);show("Response started")}
  async function updateItem(id:number,patch:Record<string,string>){if(!plan)return;const item=plan.items.find(x=>x.id===id);if(!item)return;const updated=await api<any>(`/api/plans/${plan.id}/items/${id}`,{method:"PATCH",body:JSON.stringify({status:patch.status??item.status,assignee_name:patch.assignee_name??item.assignee_name,user_notes:""})});setPlan({...plan,items:plan.items.map(x=>x.id===id?{...x,...updated}:x)})}
  async function share(){if(!active||!plan)return;const complete=plan.items.filter(x=>x.status==="completed").length;const text=`SustainBuild response: ${active.title} — ${active.facility_name}. ${complete}/${plan.items.length} actions complete. Open the workspace for assignments.`;const canShare=typeof navigator.share==="function";if(canShare)await navigator.share({title:"SustainBuild response",text});else await navigator.clipboard.writeText(text);show(canShare?"Share sheet opened":"Briefing copied")}
  function show(message:string){setToast(message);setTimeout(()=>setToast(""),2200)}
  const value=assets.reduce((sum,a)=>sum+a.value_amount,0); const completed=plan?.items.filter(x=>x.status==="completed").length||0; const ActiveIcon=active?hazardIcons[active.hazard_type]||Radar:Radar;
  return <div className="overview page-wrap response-overview">
    {toast&&<div className="toast"><Check/>{toast}</div>}
    <div className="page-heading"><div><h1>SustainBuild</h1><p>Choose a signal. Start a response.</p></div><button className="secondary" onClick={onOpenTwin}><Radar/>Site visual</button></div>
    <div className="purpose-strip"><span><b>1</b>Detect</span><ArrowRight/><span><b>2</b>Assign</span><ArrowRight/><span><b>3</b>Track</span></div>

    <div className="response-layout"><section><div className="section-title"><h2>Climate signals</h2><span>{warnings.length} active demos</span></div><div className="warning-grid response-signals">{warnings.map(w=>{const Icon=hazardIcons[w.hazard_type]||Radar;return <button className={`warning-card ${w.hazard_type} ${active?.id===w.id?"selected":""}`} key={w.id} onClick={()=>{setActive(w);setPlan(null)}}><span className="warning-icon"><Icon/></span><span className="warning-main"><small>{hazardLabels[w.hazard_type]}</small><b>{w.facility_name}</b></span><span className={`warning-level ${w.severity}`}>{w.severity}</span><ArrowRight/></button>})}</div>
      <div className="portfolio-row"><div><small>SELECTED SITE VALUE</small><b>{new Intl.NumberFormat(undefined,{style:"currency",currency:facility.currency,notation:"compact"}).format(value)}</b></div><div><small>SAVED RESPONSES</small><b>{scenarios.length}</b></div><div><small>REGISTERED ASSETS</small><b>{assets.length}</b></div></div></section>

      <aside className={`response-console ${active?"open":""}`}>{!active?<div className="response-empty"><ClipboardCheck/><h2>Select a signal</h2><p>Then assign and track the response.</p></div>:<><div className="response-head"><span className={`warning-icon ${active.hazard_type}`}><ActiveIcon/></span><div><small>{hazardLabels[active.hazard_type]}</small><h2>{active.title}</h2><p>{active.facility_name} · {active.country}</p></div><button onClick={()=>{setActive(null);setPlan(null)}}><X/></button></div><div className="response-steps"><span className="done"><Check/>Signal</span><span className={plan?"done":"active"}>{plan?<Check/>:<b>2</b>}Response</span><span className={completed>0?"active":""}><b>3</b>Complete</span></div>
        {!plan?<div className="start-response"><div className="impact-assets"><small>EXPOSED ASSETS</small>{assets.slice(0,3).map(a=><span key={a.id}>{a.name}</span>)}</div><button className="primary full" disabled={busy} onClick={startResponse}><Play/>{busy?"Starting…":"Start response"}</button><button className="secondary full" onClick={()=>onOpenWarning(active.facility_id,active.weather_event_id)}>View site impact</button></div>:<div className="active-response"><div className="response-progress"><b>{completed}/{plan.items.length}</b><span><i style={{width:`${completed/plan.items.length*100}%`}}/></span><small>complete</small></div><div className="response-actions">{plan.items.map(item=><div key={item.id} className={item.status==="completed"?"complete":""}><button className="action-check" onClick={()=>updateItem(item.id,{status:item.status==="completed"?"planned":"completed"})}>{item.status==="completed"&&<Check/>}</button><span><b>{item.action.title}</b><small>{item.action.estimated_minutes} min</small></span><label><UserRound/><select value={item.assignee_name||"Unassigned"} onChange={e=>updateItem(item.id,{assignee_name:e.target.value,status:item.status==="suggested"?"planned":item.status})}>{owners.map(x=><option key={x}>{x}</option>)}</select></label></div>)}</div><div className="response-buttons"><button className="primary" onClick={share}><Share2/>Share briefing</button><button className="secondary" onClick={()=>onOpenWarning(active.facility_id,active.weather_event_id)}>Site visual</button></div></div>}
      </>}</aside>
    </div>
    <footer className="disclaimer">Demo signals · Actions persist · No public warning is sent</footer>
  </div>;
}
