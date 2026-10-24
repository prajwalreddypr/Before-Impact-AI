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

type SceneProps={model:ConceptModel;hazard:string;intensity:number;floorElevation:number;orientation:number;offset:[number,number];playing:boolean;autoRotate:boolean};

function Building({model,hazard,intensity,floorElevation,orientation,offset,playing}:SceneProps){
  const ref=useRef<THREE.Group>(null);
  useFrame(({clock})=>{if(ref.current){const shake=hazard==="earthquake"&&playing?Math.sin(clock.elapsedTime*19)*intensity/230:0;ref.current.position.x=offset[0]+shake}});
  return <group ref={ref} position={[offset[0],floorElevation,offset[1]]} rotation={[0,orientation*Math.PI/180,0]}>{model.blocks.map((block,i)=><group key={block.id} position={[block.x,0,block.z]}><mesh position={[0,block.height/2,0]} castShadow><boxGeometry args={[block.width,block.height,block.depth]}/><meshStandardMaterial color={hazard==="heat"&&intensity>38?"#ef7c45":i%3===0?"#d95b43":i%3===1?"#ef9a55":"#f1c573"}/></mesh><mesh position={[0,block.height+.12,0]}><boxGeometry args={[block.width+.25,.25,block.depth+.25]}/><meshStandardMaterial color="#28221f"/></mesh></group>)}</group>
}

function Scene(props:SceneProps){
  const {hazard,intensity,playing,autoRotate}=props,wet=hazard==="rain"||hazard==="flood",water=hazard==="flood"?intensity:0;
  return <>
    <color attach="background" args={[hazard==="wildfire"?"#c7674c":hazard==="heat"?"#efbd68":wet?"#62676e":"#e7b18b"]}/>
    <fog attach="fog" args={[hazard==="wildfire"?"#b45b45":wet?"#62676e":"#e7b18b",30,62]}/>
    <ambientLight intensity={wet ? .7 : 1.2}/>
    <directionalLight position={[10,18,8]} intensity={hazard==="heat"?2.8:1.8} color={hazard==="heat"?"#ffd07c":"#fff5df"}/>
    <OrbitControls makeDefault enableDamping autoRotate={autoRotate} autoRotateSpeed={1.15} minDistance={9} maxDistance={58} maxPolarAngle={Math.PI/2.05}/>
    <mesh rotation={[-Math.PI/2,0,0]}><planeGeometry args={[72,52]}/><meshStandardMaterial color={wet?"#706861":"#c98f62"}/></mesh>
    <Grid args={[50,38]} position={[0,.02,0]} cellColor="#e9bf99" sectionColor="#8a6250"/>
    <Building {...props}/>
    {hazard==="rain"&&playing&&<Rain amount={intensity}/>} {hazard==="wind"&&playing&&<Wind amount={intensity}/>} {hazard==="wildfire"&&<FireField distance={intensity}/>} {water>0&&<mesh position={[0,water,0]} rotation={[-Math.PI/2,0,0]}><planeGeometry args={[50,38]}/><meshPhysicalMaterial color="#3f9dcc" transparent opacity={.52} transmission={.3}/></mesh>} {hazard==="heat"&&<pointLight position={[0,12,0]} intensity={Math.max(1,intensity/12)} color="#ff9e43"/>}
  </>
}

export function ProjectSimulation({model,hazard,intensity,floorElevation=0,orientation=0,offset=[0,0],playing=true,autoRotate=false}:{model:ConceptModel;hazard:string;intensity:number;floorElevation?:number;orientation?:number;offset?:[number,number];playing?:boolean;autoRotate?:boolean}){
  return <Canvas shadows dpr={[1,1.5]} camera={{position:[24,18,26],fov:45}}><Scene model={model} hazard={hazard} intensity={intensity} floorElevation={floorElevation} orientation={orientation} offset={offset} playing={playing} autoRotate={autoRotate}/></Canvas>
}
