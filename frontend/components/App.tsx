"use client";

import { ProjectPlanner } from "./planner/ProjectPlanner";

export function App({sessionReady}:{sessionReady:boolean}){
  return <div className="app-shell planner-shell"><header className="topbar planner-topbar"><div className="brand"><span className="logo-mark">S</span><span>SustainBuild</span></div><span className="product-mode">Before You Build, Understand the Impact.</span></header><main className="main"><ProjectPlanner sessionReady={sessionReady}/></main></div>;
}
