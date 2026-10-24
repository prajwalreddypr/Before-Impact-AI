"use client";

import { useEffect, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowRight, CloudRain, Flame, Radar, SunMedium, ThermometerSun, Waves, Wind } from "lucide-react";
import { api } from "@/lib/api";
import { Asset, Event, Facility, Scenario, TimelineData, Warning } from "@/types";

const hazardIcons:Record<string,typeof Wind>={wind:Wind,flood:Waves,rain:CloudRain,heat:ThermometerSun,wildfire:Flame,drought:SunMedium};
const hazardLabels:Record<string,string>={wind:"Storm",flood:"Flood",rain:"Heavy rain",heat:"Extreme heat",wildfire:"Fire weather",drought:"Drought"};

export function Overview({facility,onOpenTwin,onOpenWarning}:{facility:Facility;onOpenTwin:()=>void;onOpenWarning:(facilityId:number,eventId:number)=>void}) {
  const [assets,setAssets]=useState<Asset[]>([]); const [events,setEvents]=useState<Event[]>([]); const [timeline,setTimeline]=useState<TimelineData|null>(null); const [scenarios,setScenarios]=useState<Scenario[]>([]); const [warnings,setWarnings]=useState<Warning[]>([]);
  useEffect(()=>{Promise.all([api<Asset[]>(`/api/facilities/${facility.id}/assets`),api<Event[]>(`/api/facilities/${facility.id}/events`),api<Scenario[]>(`/api/facilities/${facility.id}/scenarios`),api<{warnings:Warning[]}>("/api/warnings")]).then(([a,e,s,w])=>{setAssets(a);setEvents(e);setScenarios(s);setWarnings(w.warnings);if(e[0])api<TimelineData>(`/api/events/${e[0].id}/timeline`).then(setTimeline)})},[facility.id]);
  const peak=useMemo(()=>timeline?.readings.reduce((a,b)=>b.wind_gust_kmh>a.wind_gust_kmh?b:a,timeline.readings[0]),[timeline]);
  const value=assets.reduce((sum,a)=>sum+a.value_amount,0);
  return <div className="overview page-wrap compact-overview">
    <div className="page-heading"><div><h1>Climate watch</h1><p>{warnings.length} signals across your portfolio</p></div><button className="primary hero-cta" onClick={onOpenTwin}><Radar/>Open ImpactTwin<ArrowRight/></button></div>

    <section className="climate-summary"><div><span>NOW</span><b>{warnings.filter(w=>w.severity==="severe").length}</b><small>severe</small></div><h2>Major events</h2><p>Synthetic demo signals</p><div className="summary-icons">{warnings.map(w=>{const Icon=hazardIcons[w.hazard_type]||Radar;return <span key={w.id} title={hazardLabels[w.hazard_type]}><Icon/></span>})}</div></section>

    <section className="warning-grid">{warnings.map(w=>{const Icon=hazardIcons[w.hazard_type]||Radar;return <button className={`warning-card ${w.hazard_type}`} key={w.id} onClick={()=>onOpenWarning(w.facility_id,w.weather_event_id)}><span className="warning-icon"><Icon/></span><span className="warning-main"><small>{hazardLabels[w.hazard_type]||w.hazard_type}</small><b>{w.title}</b><em>{w.facility_name}</em></span><span className={`warning-level ${w.severity}`}>{w.severity}</span><ArrowRight/></button>})}</section>

    <div className="dashboard-grid simple-grid"><section className="panel trend-panel"><div className="panel-head"><h3>{events[0]?.name||"Event trend"}</h3><b>{Math.round(peak?.wind_gust_kmh||0)} km/h</b></div><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={timeline?.readings||[]}><defs><linearGradient id="windfill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#e7674d" stopOpacity={.34}/><stop offset="100%" stopColor="#f5b34c" stopOpacity={0}/></linearGradient></defs><CartesianGrid vertical={false} stroke="#f0dfd3"/><XAxis dataKey="timestamp" tickFormatter={x=>new Date(x).toLocaleDateString(undefined,{weekday:"short"})} minTickGap={60} axisLine={false} tickLine={false}/><YAxis axisLine={false} tickLine={false}/><Tooltip labelFormatter={x=>new Date(x).toLocaleString()}/><Area type="monotone" dataKey="wind_gust_kmh" stroke="#d94f3d" fill="url(#windfill)" strokeWidth={2}/></AreaChart></ResponsiveContainer></div></section>
      <section className="panel asset-panel"><div className="panel-head"><h3>{facility.name}</h3><b>{new Intl.NumberFormat(undefined,{style:"currency",currency:facility.currency,notation:"compact"}).format(value)}</b></div><div className="asset-list clean-list">{assets.slice(0,5).map((asset,i)=><div key={asset.id}><span className={`asset-icon a${i%3}`}>{asset.name.charAt(0)}</span><b>{asset.name}</b><strong>{new Intl.NumberFormat(undefined,{style:"currency",currency:asset.currency,notation:"compact"}).format(asset.value_amount)}</strong></div>)}</div></section>
      <section className="panel scenario-panel"><div className="panel-head"><h3>Saved scenarios</h3><b>{scenarios.length}</b></div>{scenarios.slice(0,2).map(s=><div className="scenario-row" key={s.id}><span className={s.scenario_type}/><b>{s.name}</b><strong>{s.result?.exposure_score||0}</strong></div>)}{!scenarios.length&&<div className="empty-small">No saved scenarios</div>}</section>
    </div>
    <footer className="disclaimer">Synthetic demonstrations · Illustrative outcomes</footer>
  </div>;
}
