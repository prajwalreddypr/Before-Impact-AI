"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Grid, OrbitControls } from "@react-three/drei";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import { ConceptModel } from "@/types";

function Rain({amount}:{amount:number}){
  const group=useRef<THREE.Group>(null);
  const drops=useMemo(()=>Array.from({length:Math.round(35+Math.min(100,amount)*1.8)},(_,i)=>({x:(i*7.1)%34-17,y:(i*3.9)%18,z:(i*9.3)%28-14})),[amount]);
  useFrame((_,delta)=>group.current?.children.forEach((drop,i)=>{drop.position.y-=delta*(7+amount/8);if(drop.position.y<0)drop.position.y=17+(i%3)}));
  return <group ref={group}>{drops.map((position,i)=><mesh key={i} position={[position.x,position.y,position.z]}><boxGeometry args={[.025,.5,.025]}/><meshBasicMaterial color="#b8e1f1" transparent opacity={.7}/></mesh>)}</group>
}

function Wind({amount}:{amount:number}){
  const group=useRef<THREE.Group>(null);
  useFrame(({clock})=>{if(group.current)group.current.position.x=(clock.elapsedTime*(1+amount/18)%34)-17});
  return <group ref={group}>{[-6,-2,2,6].map((z,i)=><mesh key={z} position={[0,3+i,z]} rotation={[0,0,Math.PI/2]}><cylinderGeometry args={[.035,.035,8,5]}/><meshBasicMaterial color="#ffd35f" transparent opacity={.8}/></mesh>)}</group>
}

function FireField({distance}:{distance:number}){
  const amount=Math.max(4,Math.round((600-distance)/55)),group=useRef<THREE.Group>(null);
  useFrame(({clock})=>group.current?.children.forEach((item,i)=>item.scale.setScalar(.8+Math.sin(clock.elapsedTime*5+i)*.18)));
  return <group ref={group}>{Array.from({length:amount},(_,i)=><mesh key={i} position={[-16+(i*3.8)%32,.35,12-(i%3)*2]}><coneGeometry args={[.3+.2*(i%2),.9+(i%3)*.3,8]}/><meshBasicMaterial color={i%2?"#ffb33c":"#e84f37"}/></mesh>)}</group>
}

type SceneProps={model:ConceptModel;hazard:string;intensity:number;floorElevation:number;orientation:number;offset:[number,number];playing:boolean;autoRotate:boolean;equipmentElevation?:number;showPlatform?:boolean};

function Building({model,hazard,intensity,floorElevation,orientation,offset,playing}:SceneProps){
  const ref=useRef<THREE.Group>(null);
  useFrame(({clock})=>{if(ref.current){const shake=hazard==="earthquake"&&playing?Math.sin(clock.elapsedTime*19)*intensity/230:0;ref.current.position.x=offset[0]+shake}});
  return <group ref={ref} position={[offset[0],floorElevation,offset[1]]} rotation={[0,orientation*Math.PI/180,0]}>{model.blocks.map((block,i)=><group key={block.id} position={[block.x,0,block.z]}><mesh position={[0,block.height/2,0]} castShadow><boxGeometry args={[block.width,block.height,block.depth]}/><meshStandardMaterial color={hazard==="heat"&&intensity>38?"#ef7c45":i%3===0?"#d95b43":i%3===1?"#ef9a55":"#f1c573"}/></mesh><mesh position={[0,block.height+.12,0]}><boxGeometry args={[block.width+.25,.25,block.depth+.25]}/><meshStandardMaterial color="#28221f"/></mesh></group>)}</group>
}

function Scene(props:SceneProps){
  const extent=Math.max(34,props.model.footprint_m.width,props.model.footprint_m.depth);
  const {hazard,intensity,playing,autoRotate}=props,wet=hazard==="rain"||hazard==="flood",water=hazard==="flood"?intensity:0;
  return <>
    <color attach="background" args={[hazard==="wildfire"?"#c7674c":hazard==="heat"?"#efbd68":wet?"#62676e":"#e7b18b"]}/>
    <fog attach="fog" args={[hazard==="wildfire"?"#b45b45":wet?"#62676e":"#e7b18b",extent*.7,extent*3]}/>
    <ambientLight intensity={wet ? .7 : 1.2}/>
    <directionalLight position={[10,18,8]} intensity={hazard==="heat"?2.8:1.8} color={hazard==="heat"?"#ffd07c":"#fff5df"}/>
    <OrbitControls makeDefault enableDamping autoRotate={autoRotate} autoRotateSpeed={1.15} minDistance={9} maxDistance={extent*3} target={[0,2,0]} maxPolarAngle={Math.PI/2.05}/>
    <mesh rotation={[-Math.PI/2,0,0]}><planeGeometry args={[extent*2.5,extent*2.5]}/><meshStandardMaterial color={wet?"#706861":"#c98f62"}/></mesh>
    <Grid args={[extent*2,extent*2]} position={[0,.02,0]} cellColor="#e9bf99" sectionColor="#8a6250"/>
    {props.showPlatform&&props.floorElevation>0&&<mesh position={[props.offset[0],props.floorElevation/2,props.offset[1]]} rotation={[0,props.orientation*Math.PI/180,0]}><boxGeometry args={[props.model.footprint_m.width+.8,props.floorElevation,props.model.footprint_m.depth+.8]}/><meshStandardMaterial color="#d7d1bf"/></mesh>}
    <Building {...props}/>
    {props.equipmentElevation!==undefined&&<group position={[props.model.footprint_m.width/2+2,0,0]}><mesh position={[0,props.equipmentElevation+.6,0]}><boxGeometry args={[1.4,1.2,1.2]}/><meshStandardMaterial color="#f1d17d"/></mesh>{props.equipmentElevation>0&&<mesh position={[0,props.equipmentElevation/2,0]}><boxGeometry args={[.6,props.equipmentElevation,.6]}/><meshStandardMaterial color="#524c42"/></mesh>}</group>}
    {hazard==="rain"&&playing&&<Rain amount={intensity}/>} {hazard==="wind"&&playing&&<Wind amount={intensity}/>} {hazard==="wildfire"&&<FireField distance={intensity}/>} {water>0&&<mesh position={[0,water,0]} rotation={[-Math.PI/2,0,0]}><planeGeometry args={[extent*2,extent*2]}/><meshPhysicalMaterial color="#3f9dcc" transparent opacity={.52} transmission={.3}/></mesh>} {hazard==="heat"&&<pointLight position={[0,12,0]} intensity={Math.max(1,intensity/12)} color="#ff9e43"/>}
  </>
}

export function ProjectSimulation({model,hazard,intensity,floorElevation=0,orientation=0,offset=[0,0],playing=true,autoRotate=false,equipmentElevation,showPlatform=false}:{model:ConceptModel;hazard:string;intensity:number;floorElevation?:number;orientation?:number;offset?:[number,number];playing?:boolean;autoRotate?:boolean;equipmentElevation?:number;showPlatform?:boolean}){
  const extent=Math.max(24,model.footprint_m.width,model.footprint_m.depth);
  return <Canvas shadows dpr={[1,1.5]} camera={{position:[extent*.95,extent*.7,extent*1.15],fov:45,far:extent*10}}><Scene model={model} hazard={hazard} intensity={intensity} floorElevation={floorElevation} orientation={orientation} offset={offset} playing={playing} autoRotate={autoRotate} equipmentElevation={equipmentElevation} showPlatform={showPlatform}/></Canvas>
}
