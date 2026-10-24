"use client";

import { useEffect, useMemo, useRef } from "react";
import { Canvas, ThreeEvent, useFrame, useThree } from "@react-three/fiber";
import { Grid, OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { Asset, Event, Facility, Reading } from "@/types";
import { useSimulation } from "@/stores/simulation";

function CameraRig({mode}:{mode:"perspective"|"top"}) {const {camera}=useThree();const controls=useRef<any>(null);useEffect(()=>{camera.position.set(mode==="top"?0:18,mode==="top"?30:14,mode==="top"?.1:21);camera.lookAt(0,0,0);controls.current?.target.set(0,0,0);controls.current?.update()},[mode,camera]);return <OrbitControls ref={controls} makeDefault enableDamping maxPolarAngle={mode==="top"?.25:Math.PI/2.05} minDistance={8} maxDistance={44}/>}
function choose(id:number|undefined,select:(id:number|null)=>void){return(e:ThreeEvent<MouseEvent>)=>{e.stopPropagation();if(id)select(id)}}

function GreenhouseSite({assets,selected,select}:{assets:Asset[];selected:number|null;select:(id:number|null)=>void}) {return <>
  {assets.filter(a=>a.asset_type==="greenhouse").map(a=>{const w=a.dimensions_json.width||3.5,h=a.dimensions_json.height||2.3,d=a.dimensions_json.depth||7;return <group key={a.id} position={[a.relative_x,0,a.relative_z]} onClick={choose(a.id,select)}><mesh position={[0,h/2,0]}><boxGeometry args={[w,h,d]}/><meshPhysicalMaterial color={selected===a.id?"#ff7857":"#f4c2a8"} transparent opacity={.68} transmission={.13}/></mesh><mesh position={[0,h+.45,0]} rotation={[0,0,Math.PI/4]}><boxGeometry args={[w/1.45,w/1.45,d]}/><meshPhysicalMaterial color="#ffe0bf" transparent opacity={.58}/></mesh></group>})}
  <mesh position={[7,1.4,4]} onClick={choose(assets.find(a=>a.asset_type==="building")?.id,select)}><boxGeometry args={[4,2.8,4]}/><meshStandardMaterial color="#b65d43"/></mesh><mesh position={[0,.06,8]} rotation={[-Math.PI/2,0,0]}><planeGeometry args={[9,28]}/><meshStandardMaterial color="#8b7667"/></mesh><Tank position={[-8,0,4]}/>
  </>}

function WarehouseSite({assets,select}:{assets:Asset[];select:(id:number|null)=>void}) {return <>
  <group onClick={choose(assets[0]?.id,select)}><mesh position={[0,2.3,0]}><boxGeometry args={[15,4.6,10]}/><meshStandardMaterial color="#c95d43"/></mesh><mesh position={[0,4.75,0]} rotation={[0,0,.08]}><boxGeometry args={[15.5,.25,10.5]}/><meshStandardMaterial color="#2b2521"/></mesh>{[-4,0,4].map(x=><mesh key={x} position={[x,1,-5.06]}><boxGeometry args={[2.6,2.2,.15]}/><meshStandardMaterial color="#ffd16c"/></mesh>)}</group>
  {[-5,-2,1,4].map((x,i)=><mesh key={x} position={[x,.7,7]} onClick={choose(assets[(i%Math.max(1,assets.length))]?.id,select)}><boxGeometry args={[2.1,1.4,2]}/><meshStandardMaterial color={i%2?"#ed8a4a":"#f2bd62"}/></mesh>)}
  <mesh position={[0,.04,-8]} rotation={[-Math.PI/2,0,0]}><planeGeometry args={[20,7]}/><meshStandardMaterial color="#6d635c"/></mesh>
  </>}

function FarmSite({assets,select}:{assets:Asset[];select:(id:number|null)=>void}) {return <>
  {Array.from({length:12},(_,i)=><mesh key={i} position={[-10+i*1.8,.18,-2]} onClick={choose(assets[1]?.id,select)}><boxGeometry args={[1.1,.35,14]}/><meshStandardMaterial color={i%2?"#d99245":"#efb65b"}/></mesh>)}
  <mesh position={[8,1.8,5]} onClick={choose(assets[0]?.id,select)}><boxGeometry args={[5,3.6,5]}/><meshStandardMaterial color="#f0dfc4"/></mesh><mesh position={[8,3.75,5]} rotation={[0,0,Math.PI/4]}><boxGeometry args={[3.7,3.7,5.2]}/><meshStandardMaterial color="#b84c38"/></mesh><Tank position={[-9,0,7]}/>
  </>}

function WorkshopSite({assets,select}:{assets:Asset[];select:(id:number|null)=>void}) {return <>
  <mesh position={[1,1.6,0]} onClick={choose(assets[0]?.id,select)}><boxGeometry args={[12,3.2,8]}/><meshStandardMaterial color="#e6a267"/></mesh><mesh position={[1,3.35,0]}><boxGeometry args={[12.5,.3,8.5]}/><meshStandardMaterial color="#2c2724"/></mesh>
  {[-7,-4,7].map((x,i)=><group key={x} position={[x,0,i*3-3]} onClick={choose(assets[1]?.id,select)}><mesh position={[0,.5,0]}><boxGeometry args={[2,1,1.3]}/><meshStandardMaterial color="#d6523e"/></mesh><mesh position={[0,.95,0]}><cylinderGeometry args={[.45,.45,.3,12]}/><meshStandardMaterial color="#26211f"/></mesh></group>)}
  <mesh position={[0,.1,-10]} rotation={[-Math.PI/2,0,0]}><planeGeometry args={[35,7]}/><meshStandardMaterial color="#638397"/></mesh>
  </>}

function FactorySite({assets,select}:{assets:Asset[];select:(id:number|null)=>void}) {return <>
  <mesh position={[-2,2,0]} onClick={choose(assets[0]?.id,select)}><boxGeometry args={[15,4,11]}/><meshStandardMaterial color="#9a4a3d"/></mesh><mesh position={[-2,4.1,0]}><boxGeometry args={[15.5,.3,11.5]}/><meshStandardMaterial color="#24201e"/></mesh>
  {[-7,-3,1].map((x,i)=><group key={x} position={[x,4.2,-2]}><mesh position={[0,2+i*.5,0]}><cylinderGeometry args={[.55,.75,4+i,16]}/><meshStandardMaterial color="#e5a158"/></mesh><mesh position={[0,4+i,0]}><cylinderGeometry args={[.65,.65,.3,16]}/><meshStandardMaterial color="#292320"/></mesh></group>)}
  {[7,10].map((x,i)=><group key={x} position={[x,0,i*4-2]} onClick={choose(assets[1]?.id,select)}><Tank position={[0,0,0]}/></group>)}
  </>}

function ProposedSite({assets,select}:{assets:Asset[];select:(id:number|null)=>void}) {return <>
  <mesh position={[0,2,0]} onClick={choose(assets[0]?.id,select)}><boxGeometry args={[16,4,11]}/><meshStandardMaterial color="#ffb46a" wireframe/></mesh><mesh position={[-7,.7,7]} onClick={choose(assets[1]?.id,select)}><boxGeometry args={[4,1.4,3]}/><meshStandardMaterial color="#d94f3d" wireframe/></mesh>
  {Array.from({length:8},(_,i)=><mesh key={i} position={[-7+i*2,.05,-7]}><boxGeometry args={[1.2,.1,1.2]}/><meshStandardMaterial color="#2c2724"/></mesh>)}
  </>}

function Tank({position}:{position:[number,number,number]}) {return <group position={position}><mesh position={[0,1.5,0]}><cylinderGeometry args={[1.25,1.25,3,24]}/><meshStandardMaterial color="#6d7780" metalness={.55}/></mesh><mesh position={[0,3.05,0]}><sphereGeometry args={[1.25,16,8,0,Math.PI*2,0,Math.PI/2]}/><meshStandardMaterial color="#6d7780" metalness={.55}/></mesh></group>}

function SiteGeometry({facility,assets,selected,select}:{facility:Facility;assets:Asset[];selected:number|null;select:(id:number|null)=>void}) {if(facility.status==="proposed")return <ProposedSite assets={assets} select={select}/>;switch(facility.facility_type){case"greenhouse":return <GreenhouseSite assets={assets} selected={selected} select={select}/>;case"warehouse":return <WarehouseSite assets={assets} select={select}/>;case"farm":return <FarmSite assets={assets} select={select}/>;case"workshop":return <WorkshopSite assets={assets} select={select}/>;default:return <FactorySite assets={assets} select={select}/>}}

function Rain({intensity}:{intensity:number}) {const group=useRef<THREE.Group>(null);const drops=useMemo(()=>Array.from({length:Math.round(40+intensity*3)},(_,i)=>({x:(i*7.13)%28-14,y:(i*3.7)%16,z:(i*11.3)%24-12})),[intensity]);useFrame((_,d)=>{group.current?.children.forEach((o,i)=>{o.position.y-=d*(8+intensity/2);if(o.position.y<0)o.position.y=15+(i%4)})});return <group ref={group}>{drops.map((p,i)=><mesh key={i} position={[p.x,p.y,p.z]}><boxGeometry args={[.018,.48,.018]}/><meshBasicMaterial color="#9dd7ea" transparent opacity={.62}/></mesh>)}</group>}
function Vegetation({wind}:{wind:number}) {const refs=useRef<THREE.Group[]>([]);useFrame(({clock})=>refs.current.forEach((g,i)=>{if(g)g.rotation.z=Math.sin(clock.elapsedTime*3+i)*Math.min(.22,wind/260)}));return <>{Array.from({length:16},(_,i)=><group key={i} position={[-13+(i%8)*3.7,0,i<8?-10:11]} ref={el=>{if(el)refs.current[i]=el}}><mesh position={[0,.7,0]}><cylinderGeometry args={[.08,.14,1.4,6]}/><meshStandardMaterial color="#604b32"/></mesh><mesh position={[0,1.7,0]}><coneGeometry args={[.65,2.2,7]}/><meshStandardMaterial color={wind>65?"#d97a43":"#d9a24a"}/></mesh></group>)}</>}
function WindField({speed,direction}:{speed:number;direction:number}) {const group=useRef<THREE.Group>(null);useFrame(({clock})=>{if(group.current)group.current.position.x=((clock.elapsedTime*(speed/15))%24)-12});return <group ref={group} rotation={[0,-direction*Math.PI/180,0]}>{[2,5,8].map((z,i)=><mesh key={z} position={[0,3+i,z-5]} rotation={[0,0,Math.PI/2]}><cylinderGeometry args={[.035,.035,5,5]}/><meshBasicMaterial color="#ffd36d" transparent opacity={.7}/></mesh>)}</group>}

function Scene({facility,assets,event,reading}:{facility:Facility;assets:Asset[];event:Event;reading:Reading}) {const {selectedAssetId,selectAsset,cameraMode}=useSimulation();const h=event.hazard_type;const rain=h==="rain"||h==="flood"?reading.rainfall_mm:0;const flood=h==="flood"?event.scenario_depth_m*Math.min(1,Math.max(0,(reading.rainfall_mm-1)/9)):0;return <><CameraRig mode={cameraMode}/><color attach="background" args={[h==="rain"||h==="flood"?"#5a5150":h==="wildfire"?"#c86243":h==="heat"||h==="drought"?"#f2ba5d":"#e8b48f"]}/><fog attach="fog" args={[h==="rain"?"#5a5150":h==="wildfire"?"#b85b43":"#e8b48f",25,60]}/><ambientLight intensity={h==="rain"?.6:1.15}/><directionalLight position={[10,18,8]} intensity={h==="heat"?3:1.7} color={h==="heat"?"#ffd28c":"#fff7df"} castShadow/><mesh rotation={[-Math.PI/2,0,0]} receiveShadow onClick={()=>selectAsset(null)}><planeGeometry args={[70,55]}/><meshStandardMaterial color={rain?"#6f625b":h==="wildfire"?"#7c4b37":h==="drought"?"#d8ad67":"#c88f62"}/></mesh><Grid args={[48,38]} position={[0,.012,0]} cellColor="#e2b389" sectionColor="#8e6551" fadeDistance={35}/><SiteGeometry facility={facility} assets={assets} selected={selectedAssetId} select={selectAsset}/><Vegetation wind={reading.wind_gust_kmh}/>{h==="wind"&&<WindField speed={reading.wind_gust_kmh} direction={reading.wind_direction_deg}/>} {rain>0&&<Rain intensity={rain}/>} {flood>0&&<mesh position={[0,.12+flood,0]} rotation={[-Math.PI/2,0,0]}><planeGeometry args={[42,35]}/><meshPhysicalMaterial color="#3f9dcc" transparent opacity={.48} transmission={.25}/></mesh>}</>}

export default function FacilityCanvas({facility,assets,event,reading}:{facility:Facility;assets:Asset[];event:Event;reading:Reading}) {return <Canvas shadows dpr={[1,1.5]} gl={{antialias:true,powerPreference:"high-performance"}} camera={{position:[18,14,21],fov:46}}><Scene facility={facility} assets={assets} event={event} reading={reading}/></Canvas>}
