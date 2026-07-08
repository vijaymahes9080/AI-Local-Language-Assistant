"use client";

import React, { useState, useEffect } from "react";
import { 
  ShieldAlert, Activity, Users, Zap, Terminal, Database, ToggleLeft, ToggleRight, 
  RefreshCw, LogOut, CheckCircle, AlertTriangle, Key, Search
} from "lucide-react";

interface Metrics {
  active_users: number;
  total_messages: number;
  prompt_firewall_triggers: number;
  average_latency_ms: number;
  total_tokens_consumed: number;
}

interface AuditLog {
  id: string;
  user_id: string;
  action: string;
  status: string;
  payload: string;
  timestamp: string;
}

interface FeatureFlag {
  flag_key: string;
  is_enabled: boolean;
  description: string;
}

export default function AdminConsole() {
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState("admin@lingosphere.ai");
  const [password, setPassword] = useState("adminpass");
  const [errorMsg, setErrorMsg] = useState("");
  const [infoMsg, setInfoMsg] = useState("");

  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [dbStatus, setDbStatus] = useState<string>("Checking...");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const API_BASE = "http://localhost:8000/api/v1";

  useEffect(() => {
    const saved = localStorage.getItem("admin_token");
    if (saved) {
      setToken(saved);
      loadAllAdminData(saved);
    }
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      if (!res.ok) throw new Error("Invalid admin credentials");
      const data = await res.json();
      
      // We will check the user's role by calling /me (or catch the 403 on metrics load)
      const testMe = await fetch(`${API_BASE}/auth/me`, {
        headers: { "Authorization": `Bearer ${data.access_token}` }
      });
      const meData = await testMe.json();
      
      if (meData.role !== "admin") {
        throw new Error("Access Denied: You do not hold administrator privilege privileges.");
      }

      setToken(data.access_token);
      localStorage.setItem("admin_token", data.access_token);
      loadAllAdminData(data.access_token);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed login");
    }
  };

  const handleLogout = () => {
    setToken(null);
    localStorage.removeItem("admin_token");
  };

  const loadAllAdminData = async (authToken: string) => {
    setIsRefreshing(true);
    try {
      const headers = { "Authorization": `Bearer ${authToken}` };

      // 1. Fetch metrics
      const mRes = await fetch(`${API_BASE}/admin/metrics`, { headers });
      if (mRes.ok) {
        const mData = await mRes.json();
        setMetrics(mData);
      }

      // 2. Fetch flags
      const fRes = await fetch(`${API_BASE}/admin/flags`, { headers });
      if (fRes.ok) {
        const fData = await fRes.json();
        setFlags(fData);
      }

      // 3. Fetch audit logs
      const aRes = await fetch(`${API_BASE}/admin/audit-logs`, { headers });
      if (aRes.ok) {
        const aData = await aRes.json();
        setAuditLogs(aData);
      }

      // 4. Fetch DB health status
      const dRes = await fetch(`${API_BASE}/admin/db-health`, { headers });
      if (dRes.ok) {
        const dData = await dRes.json();
        setDbStatus(dData.status === "healthy" ? "CONNECTED" : "DISCONNECTED");
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Toggle Feature Flag
  const toggleFlag = async (flagKey: string, currentVal: boolean) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/admin/flags`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ flag_key: flagKey, is_enabled: !currentVal })
      });
      if (res.ok) {
        setInfoMsg(`Feature flag '${flagKey}' updated successfully.`);
        loadAllAdminData(token);
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-[#f8fafc] flex flex-col">
      
      {/* TOP HEADER */}
      <header className="glass-panel px-6 py-4 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <div className="bg-red-500/10 border border-red-500/30 p-2.5 rounded-xl">
            <ShieldAlert className="h-6 w-6 text-red-400" />
          </div>
          <div>
            <h1 className="text-lg font-bold">LingoSphere AI Control Console</h1>
            <p className="text-xs text-slate-400">Security Firewall & Systems Orchestration</p>
          </div>
        </div>

        {token && (
          <div className="flex items-center gap-3">
            <button 
              onClick={() => loadAllAdminData(token)}
              disabled={isRefreshing}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-50 transition-all flex items-center gap-1.5 text-xs font-semibold"
            >
              <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} /> Reload
            </button>
            <button 
              onClick={handleLogout}
              className="p-2 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 transition-all flex items-center gap-1 text-xs font-semibold"
            >
              <LogOut className="h-4 w-4" /> Exit Console
            </button>
          </div>
        )}
      </header>

      {/* BODY VIEWPORT */}
      {!token ? (
        /* LOGIN */
        <main className="flex-1 flex items-center justify-center p-6 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-background to-background">
          <div className="glass-panel w-full max-w-md p-8 rounded-2xl border border-card-border shadow-2xl">
            <h2 className="text-xl font-bold text-center mb-1 flex items-center justify-center gap-2">
              <Key className="h-5 w-5 text-brand-purple" /> Admin Authorization
            </h2>
            <p className="text-xs text-slate-400 text-center mb-6">Access restricted to platform operators only.</p>

            {errorMsg && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-3 rounded-lg text-xs mb-4 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">OPERATOR EMAIL</label>
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full bg-slate-900 border border-slate-700 px-4 py-2.5 rounded-lg text-sm focus:outline-none focus:border-brand-purple text-slate-200"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">SECURITY KEY</label>
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full bg-slate-900 border border-slate-700 px-4 py-2.5 rounded-lg text-sm focus:outline-none focus:border-brand-purple text-slate-200"
                />
              </div>

              <button 
                type="submit"
                className="w-full bg-gradient-to-r from-red-600 to-red-800 text-white py-3 rounded-lg font-bold text-sm hover:opacity-90 transition-opacity mt-4 shadow-lg shadow-red-900/30 border border-red-500/20"
              >
                Authenticate Operator
              </button>
            </form>
          </div>
        </main>
      ) : (
        /* CONSOLE WORKSPACE */
        <main className="flex-1 p-6 space-y-6 overflow-y-auto">
          
          {infoMsg && (
            <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 p-3 rounded-lg text-xs flex items-center gap-2">
              <CheckCircle className="h-4 w-4" />
              <span>{infoMsg}</span>
              <button onClick={() => setInfoMsg("")} className="ml-auto font-bold">×</button>
            </div>
          )}

          {/* TELEMETRY METRICS GRID */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            
            <div className="glass-panel p-4 rounded-xl border border-card-border flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase">Active Users</span>
                <h3 className="text-xl font-bold mt-1 text-slate-100">{metrics?.active_users ?? 0}</h3>
              </div>
              <div className="bg-brand-purple/10 p-2.5 rounded-lg text-brand-purple">
                <Users className="h-5 w-5" />
              </div>
            </div>

            <div className="glass-panel p-4 rounded-xl border border-card-border flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase">Total Messages</span>
                <h3 className="text-xl font-bold mt-1 text-slate-100">{metrics?.total_messages ?? 0}</h3>
              </div>
              <div className="bg-brand-royal/10 p-2.5 rounded-lg text-brand-royal">
                <Terminal className="h-5 w-5" />
              </div>
            </div>

            <div className="glass-panel p-4 rounded-xl border border-card-border flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase">Avg Response Speed</span>
                <h3 className="text-xl font-bold mt-1 text-slate-100">{metrics?.average_latency_ms ?? 0.0} <span className="text-xs font-normal">ms</span></h3>
              </div>
              <div className="bg-brand-cyan/10 p-2.5 rounded-lg text-brand-cyan">
                <Activity className="h-5 w-5" />
              </div>
            </div>

            <div className="glass-panel p-4 rounded-xl border border-card-border flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase">Tokens Billing Count</span>
                <h3 className="text-xl font-bold mt-1 text-slate-100">{metrics?.total_tokens_consumed ?? 0}</h3>
              </div>
              <div className="bg-brand-emerald/10 p-2.5 rounded-lg text-brand-emerald">
                <Zap className="h-5 w-5" />
              </div>
            </div>

            <div className="glass-panel p-4 rounded-xl border border-card-border flex items-center justify-between">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase">Firewall Alarms</span>
                <h3 className="text-xl font-bold mt-1 text-red-400">{metrics?.prompt_firewall_triggers ?? 0}</h3>
              </div>
              <div className="bg-red-500/10 p-2.5 rounded-lg text-red-400 animate-pulse">
                <ShieldAlert className="h-5 w-5" />
              </div>
            </div>

          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* FEATURE FLAGS SECTION */}
            <div className="glass-panel p-6 rounded-2xl border border-card-border lg:col-span-1">
              <h3 className="text-sm font-bold mb-4 text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Database className="h-4 w-4 text-brand-purple" /> System Feature Flags
              </h3>
              
              {flags.length === 0 ? (
                <p className="text-xs text-slate-500">No active flags. System defaults are operational.</p>
              ) : (
                <div className="space-y-4">
                  {flags.map((flag, idx) => (
                    <div key={idx} className="flex items-start justify-between p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                      <div className="flex-1 mr-3">
                        <span className="text-xs font-bold text-slate-200 block truncate max-w-[170px]">{flag.flag_key}</span>
                        <p className="text-[10px] text-slate-400 leading-normal mt-0.5">{flag.description}</p>
                      </div>
                      <button 
                        onClick={() => toggleFlag(flag.flag_key, flag.is_enabled)}
                        className="text-slate-400 hover:text-white transition-colors"
                      >
                        {flag.is_enabled ? (
                          <ToggleRight className="h-6 w-6 text-brand-emerald" />
                        ) : (
                          <ToggleLeft className="h-6 w-6 text-slate-500" />
                        )}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* SECURITY AUDIT FIREWALL LOGS */}
            <div className="glass-panel p-6 rounded-2xl border border-card-border lg:col-span-2 flex flex-col h-[400px] overflow-hidden">
              <h3 className="text-sm font-bold mb-4 text-slate-300 uppercase tracking-wider flex items-center gap-1.5 flex-shrink-0">
                <Terminal className="h-4 w-4 text-red-400" /> Prompt Injection Firewall Alerts
              </h3>
              
              <div className="flex-1 overflow-y-auto space-y-3 pr-2">
                {auditLogs.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-xs text-slate-500 font-medium">
                    No prompt injection incidents logged. System secure.
                  </div>
                ) : (
                  auditLogs.map((log, idx) => (
                    <div key={idx} className="p-3 rounded-lg bg-red-500/[0.02] border border-red-500/10 text-xs space-y-1">
                      <div className="flex items-center justify-between font-bold text-red-400">
                        <span className="flex items-center gap-1">
                          <AlertTriangle className="h-3.5 w-3.5" /> BLOCKED INJECTION
                        </span>
                        <span className="text-[10px] font-mono text-slate-500">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-slate-300 bg-slate-950 p-2 rounded font-mono text-[11px] break-words whitespace-pre-wrap">
                        {log.payload}
                      </p>
                      <div className="text-[9px] text-slate-500 font-semibold truncate">
                        User ID: {log.user_id}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>

          {/* DIAGNOSTICS CONTROL PANEL */}
          <div className="glass-panel p-4 rounded-xl border border-card-border flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Database className="h-4.5 w-4.5 text-slate-400" />
              <span className="text-xs font-bold text-slate-400 uppercase">Database connection Status:</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                dbStatus === "CONNECTED" ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" : "bg-red-500/20 text-red-300 border border-red-500/30"
              }`}>
                {dbStatus}
              </span>
            </div>
            
            <div className="text-slate-500 text-[10px] font-semibold">
              LingoSphere AI Management Console v1.0.0 (Windows local engine active)
            </div>
          </div>

        </main>
      )}
    </div>
  );
}
