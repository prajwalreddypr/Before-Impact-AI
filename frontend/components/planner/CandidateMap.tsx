"use client";

import { useEffect, useMemo, useRef } from "react";
import { ArrowLeft } from "lucide-react";
import maplibregl from "maplibre-gl";
import { SitePreset } from "@/types";

export type PlotSite=SitePreset&{plot_name?:string;parent_region_id?:string};
const offsets=[[-.035,.018],[.026,.025],[.012,-.031]];
export function regionalPlots(site:SitePreset):PlotSite[]{return offsets.map(([lng,lat],i)=>({...site,id:site.id,plot_name:`${site.name.replace(" Plot","")} · Plot ${String.fromCharCode(65+i)}`,parent_region_id:site.id,longitude:site.longitude+lng,latitude:site.latitude+lat,plot_area_m2:Math.round(site.plot_area_m2*(.78+i*.11))}))}

export function CandidateMap({sites,expandedRegionId,selectedPlotName,onExpand,onSelect}:{sites:SitePreset[];expandedRegionId:string;selectedPlotName:string;onExpand:(id:string)=>void;onSelect:(site:PlotSite)=>void}){
  const node=useRef<HTMLDivElement>(null),mapRef=useRef<maplibregl.Map|null>(null),expandRef=useRef(onExpand),selectRef=useRef(onSelect);
  expandRef.current=onExpand;selectRef.current=onSelect;
  const expanded=sites.find(x=>x.id===expandedRegionId);
  const markers=useMemo<PlotSite[]>(()=>expanded?regionalPlots(expanded):sites,[sites,expanded]);
  useEffect(()=>{if(!node.current)return;const map=new maplibregl.Map({container:node.current,center:[2.1,46.55],zoom:5.25,minZoom:4,maxZoom:16,style:{version:8,sources:{osm:{type:"raster",tiles:["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],tileSize:256,attribution:"© OpenStreetMap contributors"}},layers:[{id:"osm",type:"raster",source:"osm"}]}});map.addControl(new maplibregl.NavigationControl({showCompass:false}),"bottom-right");mapRef.current=map;return()=>{map.remove();mapRef.current=null}},[]);
  useEffect(()=>{const map=mapRef.current;if(!map)return;const instances=markers.map(site=>{const isPlot=Boolean(site.plot_name);const el=document.createElement("button");el.className=`real-map-marker ${isPlot?"plot-pin":"region-pin"} ${selectedPlotName===site.plot_name?"selected":""}`;el.type="button";el.setAttribute("aria-label",isPlot?`Select ${site.plot_name}`:`Explore ${site.name}`);el.innerHTML=`<span></span><b>${site.plot_name||site.name}</b>`;el.onclick=()=>isPlot?selectRef.current(site):expandRef.current(site.id);return new maplibregl.Marker({element:el,anchor:"bottom"}).setLngLat([site.longitude,site.latitude]).addTo(map)});if(expanded){map.flyTo({center:[expanded.longitude,expanded.latitude],zoom:11.4,duration:700})}else if(sites.length){const bounds=new maplibregl.LngLatBounds();sites.forEach(s=>bounds.extend([s.longitude,s.latitude]));map.fitBounds(bounds,{padding:70,maxZoom:6.2,duration:650})}return()=>instances.forEach(x=>x.remove())},[markers,expanded,selectedPlotName,sites]);
  return <div className="candidate-map-shell"><div className="real-candidate-map" ref={node}/><span className="map-live-badge">REAL MAP · FICTIONAL PLOTS</span>{expanded&&<button className="map-region-back" onClick={()=>onExpand("")}><ArrowLeft/>All France</button>}<div className="map-instruction"><b>{expanded?expanded.name:"Choose a region"}</b><span>{expanded?"Now select one of the three smaller plot pins.":"Select a large pin to reveal its available plots."}</span></div></div>
}
