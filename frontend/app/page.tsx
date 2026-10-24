"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { App } from "@/components/App";

export default function Home(){
  const [sessionReady,setSessionReady]=useState(false);
  useEffect(()=>{async function prepare(){const existing=localStorage.getItem("beforeimpact_token");if(existing){try{await api("/api/auth/me");setSessionReady(true);return}catch{localStorage.removeItem("beforeimpact_token")}}try{const data=await api<{access_token:string}>("/api/auth/login",{method:"POST",body:JSON.stringify({email:"demo@beforeimpact.ai",password:"Demo123!"})});localStorage.setItem("beforeimpact_token",data.access_token);setSessionReady(true)}catch{setSessionReady(false)}}prepare()},[]);
  return <App sessionReady={sessionReady}/>;
}
