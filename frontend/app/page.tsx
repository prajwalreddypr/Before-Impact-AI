"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { App } from "@/components/App";
import { ArrowRight, CloudSun, Eye, EyeOff, ShieldCheck } from "lucide-react";

export default function Home() {
  const [ready,setReady]=useState(false); const [authed,setAuthed]=useState(false); const [error,setError]=useState(""); const [show,setShow]=useState(false);
  const [email,setEmail]=useState("demo@beforeimpact.ai"); const [password,setPassword]=useState("Demo123!");
  useEffect(()=>{ const token=localStorage.getItem("beforeimpact_token"); if(!token){setReady(true);return;} api("/api/auth/me").then(()=>setAuthed(true)).catch(()=>localStorage.removeItem("beforeimpact_token")).finally(()=>setReady(true)); },[]);
  async function login(e:React.FormEvent){ e.preventDefault(); setError(""); try { const data=await api<{access_token:string}>("/api/auth/login",{method:"POST",body:JSON.stringify({email,password})}); localStorage.setItem("beforeimpact_token",data.access_token); setAuthed(true); } catch(err){setError(err instanceof Error?err.message:"Login failed");} }
  if(!ready) return <div className="splash"><div className="logo-mark">B</div><span>Loading workspace…</span></div>;
  if(authed) return <App onLogout={()=>{localStorage.removeItem("beforeimpact_token");setAuthed(false)}}/>;
  return <main className="login-page">
    <section className="login-story"><div className="brand brand-light"><span className="logo-mark">B</span><span>BeforeImpact</span></div><div className="story-copy"><div className="eyebrow light"><CloudSun size={15}/> Climate resilience</div><h1>See the risk.<br/><em>Change the outcome.</em></h1><p>Storms, floods, heat, fire weather and drought—in one clear workspace.</p><div className="story-proof"><ShieldCheck/><span><strong>ImpactTwin</strong><small>Replay events. Test preparation.</small></span></div></div><div className="storm-lines" aria-hidden="true"/></section>
    <section className="login-panel"><form onSubmit={login}><div className="mobile-brand"><span className="logo-mark">B</span>BeforeImpact</div><span className="overline">SECURE WORKSPACE</span><h2>Welcome back</h2><p>Enter your details to continue.</p><label>Email address<input value={email} onChange={e=>setEmail(e.target.value)} type="email" required/></label><label>Password<div className="password"><input value={password} onChange={e=>setPassword(e.target.value)} type={show?"text":"password"} required/><button type="button" onClick={()=>setShow(!show)} aria-label="Show password">{show?<EyeOff/>:<Eye/>}</button></div></label>{error&&<div className="form-error">{error}</div>}<button className="primary login-button" type="submit">Enter workspace <ArrowRight size={17}/></button><button className="demo-fill" type="button" onClick={()=>{setEmail("demo@beforeimpact.ai");setPassword("Demo123!")}}>Use demo credentials</button><div className="demo-note"><span>DEMO</span><div><b>demo@beforeimpact.ai</b><small>Development access only</small></div></div></form></section>
  </main>;
}
