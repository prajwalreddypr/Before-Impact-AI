"use client";

import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Grid, OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { Asset, Event, Reading } from "@/types";
import { useSimulation } from "@/stores/simulation";

function CameraRig({mode}:{mode:"perspective"|"top"}) {
  const {camera}=useThree(); const controls=useRef<any>(null);
  useEffect(()=>{ camera.position.set(mode==="top"?0:17,mode==="top"?28:13,mode==="top"?.1:20); camera.lookAt(0,0,0); controls.current?.target.set(0,0,0); controls.current?.update(); },[mode,camera]);
  return <OrbitControls ref={controls} makeDefault enableDamping maxPolarAngle={mode==="top"?.25:Math.PI/2.05} minDistance={8} maxDistance={42}/>;
}

function Greenhouse({asset,selected,onSelect}:{asset:Asset;selected:boolean;onSelect:()=>void}) {
  const w=asset.dimensions_json.width||3.5,h=asset.dimensions_json.height||2.3,d=asset.dimensions_json.depth||7;
  return <group position={[asset.relative_x,0,asset.relative_z]} onClick={e=>{e.stopPropagation();onSelect()}}>
    <mesh position={[0,h/2,0]} castShadow><boxGeometry args={[w,h,d]}/><meshPhysicalMaterial color={selected?"#ff8a67":"#f6c6ad"} transparent opacity={.62} roughness={.18} transmission={.16}/></mesh>
    <mesh position={[0,h+0.45,0]} rotation={[0,0,Math.PI/4]}><boxGeometry args={[w/1.45,w/1.45,d]}/><meshPhysicalMaterial color={selected?"#ff8a67":"#ffe0bf"} transparent opacity={.55}/></mesh>
    {[-1,0,1].map(i=><mesh key={i} position={[i*w/3,h/2,0]}><boxGeometry args={[.05,h+1,d+.08]}/><meshStandardMaterial color="#7b6256"/></mesh>)}
    {selected&&<pointLight position={[0,4,0]} intensity={3} color="#ff6548" distance={8}/>} 
  </group>;
}

function Rain({intensity}:{intensity:number}) {
  const group=useRef<THREE.Group>(null); const drops=useMemo(()=>Array.from({length:Math.round(40+intensity*3)},(_,i)=>({x:(i*7.13)%28-14,y:(i*3.7)%16,z:(i*11.3)%24-12})),[intensity]);
  useFrame((_,delta)=>{if(!group.current)return;group.current.children.forEach((o,i)=>{o.position.y-=delta*(8+intensity/2);if(o.position.y<0)o.position.y=15+(i%4)})});
  return <group ref={group}>{drops.map((p,i)=><mesh key={i} position={[p.x,p.y,p.z]} rotation={[0,0,-.15]}><boxGeometry args={[.018,.48,.018]}/><meshBasicMaterial color="#9dd7ea" transparent opacity={.62}/></mesh>)}</group>;
}

function Vegetation({wind}:{wind:number}) {
  const refs=useRef<THREE.Group[]>([]); useFrame(({clock})=>{refs.current.forEach((g,i)=>{if(g)g.rotation.z=Math.sin(clock.elapsedTime*3+i)*Math.min(.22,wind/260)})});
  return <>{Array.from({length:18},(_,i)=>{const x=-13+(i%9)*3.2,z=i<9?-9:10;return <group key={i} position={[x,0,z]} ref={el=>{if(el)refs.current[i]=el}}><mesh position={[0,.7,0]}><cylinderGeometry args={[.08,.14,1.4,6]}/><meshStandardMaterial color="#604b32"/></mesh><mesh position={[0,1.7,0]}><coneGeometry args={[.65,2.2,7]}/><meshStandardMaterial color={wind>65?"#d97a43":"#d9a24a"}/></mesh></group>})}</>;
}

function WindField({speed,direction}:{speed:number;direction:number}) {
  const group=useRef<THREE.Group>(null); useFrame(({clock})=>{if(group.current)group.current.position.x=((clock.elapsedTime*(speed/15))%24)-12});
  return <group ref={group} rotation={[0,-direction*Math.PI/180,0]}>{[2,5,8].map((z,i)=><group key={z} position={[0,3+i,z-5]}><mesh rotation={[0,0,Math.PI/2]}><cylinderGeometry args={[.035,.035,5,5]}/><meshBasicMaterial color="#ffd36d" transparent opacity={.6}/></mesh><mesh position={[2.7,0,0]} rotation={[0,0,-Math.PI/2]}><coneGeometry args={[.15,.6,6]}/><meshBasicMaterial color="#ffd36d" transparent opacity={.75}/></mesh></group>)}</group>;
}

function Scene({assets,event,reading}:{assets:Asset[];event:Event;reading:Reading}) {
  const {selectedAssetId,selectAsset,cameraMode}=useSimulation(); const hazard=event.hazard_type; const rain=hazard==="rain"||hazard==="flood"?reading.rainfall_mm:0; const flood=hazard==="flood"?event.scenario_depth_m*(Math.min(1,Math.max(0,(reading.rainfall_mm-1)/9))):0;
  return <>
    <CameraRig mode={cameraMode}/><color attach="background" args={[hazard==="rain"||hazard==="flood"?"#5a5150":hazard==="wildfire"?"#c86243":hazard==="heat"||hazard==="drought"?"#f2ba5d":"#e8b48f"]}/><fog attach="fog" args={[hazard==="rain"?"#5a5150":hazard==="wildfire"?"#b85b43":"#e8b48f",25,60]}/>
    <ambientLight intensity={hazard==="rain"?.6:1.15}/><directionalLight position={[10,18,8]} intensity={hazard==="heat"?3:1.7} color={hazard==="heat"?"#ffd28c":"#fff7df"} castShadow shadow-mapSize={[1024,1024]}/>
    <mesh rotation={[-Math.PI/2,0,0]} receiveShadow onClick={()=>selectAsset(null)}><planeGeometry args={[70,55]}/><meshStandardMaterial color={rain?"#6f625b":hazard==="wildfire"?"#7c4b37":hazard==="drought"?"#d8ad67":"#c88f62"} roughness={rain?.34:.9}/></mesh>
    <Grid args={[48,38]} position={[0,.012,0]} cellColor="#e2b389" sectionColor="#8e6551" fadeDistance={35}/>
    {assets.filter(a=>a.asset_type==="greenhouse").map(a=><Greenhouse key={a.id} asset={a} selected={a.id===selectedAssetId} onSelect={()=>selectAsset(a.id)}/>)}
    <mesh position={[7,1.4,4]} castShadow onClick={()=>{const a=assets.find(x=>x.asset_type==="building");if(a)selectAsset(a.id)}}><boxGeometry args={[4,2.8,4]}/><meshStandardMaterial color={selectedAssetId===assets.find(x=>x.asset_type==="building")?.id?"#e4ad61":"#6f786d"}/></mesh>
    <group position={[-8,0,4]} onClick={()=>{const a=assets.find(x=>x.asset_type==="water");if(a)selectAsset(a.id)}}><mesh position={[0,1.5,0]}><cylinderGeometry args={[1.25,1.25,3,24]}/><meshStandardMaterial color="#728c91" metalness={.6}/></mesh><mesh position={[0,3.05,0]}><sphereGeometry args={[1.25,16,8,0,Math.PI*2,0,Math.PI/2]}/><meshStandardMaterial color="#728c91" metalness={.6}/></mesh></group>
    <mesh position={[0,.07,8]} rotation={[-Math.PI/2,0,0]}><planeGeometry args={[9,28]}/><meshStandardMaterial color="#847d6e"/></mesh>
    <Vegetation wind={reading.wind_gust_kmh}/>{hazard==="wind"&&<WindField speed={reading.wind_gust_kmh} direction={reading.wind_direction_deg}/>} {rain>0&&<Rain intensity={rain}/>} 
    {flood>0&&<mesh position={[0,.12+flood,0]} rotation={[-Math.PI/2,0,0]}><planeGeometry args={[42,35,24,24]}/><meshPhysicalMaterial color="#3f9dcc" transparent opacity={.48} transmission={.25} roughness={.16}/></mesh>}
  </>;
}

export default function FacilityCanvas({assets,event,reading}:{assets:Asset[];event:Event;reading:Reading}) {
  return <Canvas shadows dpr={[1,1.5]} gl={{antialias:true,powerPreference:"high-performance"}} camera={{position:[17,13,20],fov:46}}><Scene assets={assets} event={event} reading={reading}/></Canvas>;
}
