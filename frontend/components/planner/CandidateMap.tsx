"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import { SitePreset } from "@/types";

export function CandidateMap({sites,selectedIds,activeId,onSelect}:{sites:SitePreset[];selectedIds:string[];activeId:string;onSelect:(site:SitePreset)=>void}){
  const node=useRef<HTMLDivElement>(null),mapRef=useRef<maplibregl.Map|null>(null),selectRef=useRef(onSelect);
  selectRef.current=onSelect;
  useEffect(()=>{if(!node.current)return;const map=new maplibregl.Map({container:node.current,center:[2.1,46.55],zoom:5.25,minZoom:4,maxZoom:15,style:{version:8,sources:{osm:{type:"raster",tiles:["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],tileSize:256,attribution:"© OpenStreetMap contributors"}},layers:[{id:"osm",type:"raster",source:"osm"}]}});map.addControl(new maplibregl.NavigationControl({showCompass:false}),"bottom-right");mapRef.current=map;return()=>{map.remove();mapRef.current=null}},[]);
  useEffect(()=>{const map=mapRef.current;if(!map)return;const markers=sites.map(site=>{const el=document.createElement("button");el.className=`real-map-marker ${selectedIds.includes(site.id)?"selected":""} ${activeId===site.id?"active":""}`;el.type="button";el.setAttribute("aria-label",`Select ${site.name}`);el.innerHTML=`<span></span><b>${site.name}</b>`;el.onclick=()=>selectRef.current(site);return new maplibregl.Marker({element:el,anchor:"bottom"}).setLngLat([site.longitude,site.latitude]).addTo(map)});if(sites.length){const bounds=new maplibregl.LngLatBounds();sites.forEach(s=>bounds.extend([s.longitude,s.latitude]));map.fitBounds(bounds,{padding:70,maxZoom:6.2,duration:650})}return()=>markers.forEach(x=>x.remove())},[sites,selectedIds,activeId]);
  return <div className="real-candidate-map" ref={node}><span className="map-live-badge">REAL MAP · FICTIONAL PLOTS</span></div>
}
