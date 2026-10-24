"use client";

import { LogOut } from "lucide-react";
import { ProjectPlanner } from "./planner/ProjectPlanner";

export function App({onLogout}:{onLogout:()=>void}) {
  return <div className="app-shell planner-shell"><header className="topbar planner-topbar"><div className="brand"><span className="logo-mark">B</span><span>BeforeImpact</span></div><span className="product-mode">New construction climate test</span><button className="avatar" title="Sign out" onClick={onLogout}>AM<span className="logout-tip"><LogOut/>Sign out</span></button></header><main className="main"><ProjectPlanner/></main></div>;
}
