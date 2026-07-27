import React, { useState, useEffect } from 'react';
import { 
  Activity, Shield, AlertTriangle, Hammer, ClipboardList, CheckSquare, 
  Settings, LogOut, RefreshCw, Server, Gauge, Cpu, 
  User, Edit, FileText, Send, BellRing
} from 'lucide-react';

const API_BASE = "http://127.0.0.1:8000/api";

// Default Mock Account profiles
const PRESEEDED_ACCOUNTS = [
  { email: 'superadmin@ASTRA.com', name: 'Justin Bieber', role: 'Super Admin', clearance: 'Level 4', title: 'Lead Engineer', avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAJB3nF963ZDZN5AzByGsqb2MxVyIvYYJZPDV3NOPF900ug_3y-d7MEHM9IcmdVDLg62EThO7ZZgtVfPH2qBLypFdU6CntX3pU3T1JaCfwVtgGdlrtJC5dzHHTfJxSNG-UN1NvfxKBe1DzYgQaD3aqaZg3Xxnt5j4CGxyaLfpyjHJO3tUUkGQIBvHZZAZPScXVH5c1S1afsZtZtXFKb6SEtVWsYVchjtnhJNUrqnmceziBRB5_XQGZV4hDOih0mFzLsvnv-I80nDtU' },
  { email: 'rasyaad@ASTRA.com', name: 'Rasyaad P. REDIANTO', role: 'Super Admin', clearance: 'Level 4', title: 'Lead Systems Architect', avatar: 'https://lh3.googleusercontent.com/a/ACg8ocIS0G1jJt84nO4VvHspYqR64m3s8QjI1KjR2-i6mUuG0w=s96-c' },
  { email: 'admin@ASTRA.com', name: 'Operational Manager', role: 'Admin', clearance: 'Level 3', title: 'Plant Operations Coordinator', avatar: '' },
  { email: 'maint@ASTRA.com', name: 'Ronny Prasad', role: 'Maintenance', clearance: 'Level 2', title: 'Lead Maintenance Specialist', avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=256&h=256' },
  { email: 'operator@ASTRA.com', name: 'Floor Operator', role: 'Operator', clearance: 'Level 1', title: 'Field Systems Operator', avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=256&h=256' }
];

export default function App() {
  const [user, setUser] = useState<any>(null);
  const [emailInput, setEmailInput] = useState('rasyaad@ASTRA.com');
  const [passwordInput, setPasswordInput] = useState('admin123');
  const [authError, setAuthError] = useState('');
  const [activeTab, setActiveTab] = useState('overview');
  
  // Data States
  const [motors, setMotors] = useState<any[]>([]);
  const [selectedMotorId, setSelectedMotorId] = useState('MTR-01');
  const [telemetry, setTelemetry] = useState<any[]>([]);
  const [prediction, setPrediction] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [workOrders, setWorkOrders] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [overviewMetrics, setOverviewMetrics] = useState<any>({
    total_motors: 6, healthy_count: 5, warning_count: 1, critical_count: 0, avg_health_score: 94.2, active_alerts_count: 1
  });
  const [productionRisk, setProductionRisk] = useState<any[]>([]);
  const [notificationSettings, setNotificationSettings] = useState<any>({
    smtp_server: 'smtp.gmail.com', smtp_port: 587, sender_email: 'rasyaadputraredianto@gmail.com', recipient_email: 'rasyaadputraredianto@gmail.com',
    recipient_whatsapp: '+628985926975'
  });
  const [isBackendConnected, setIsBackendConnected] = useState(false);

  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Profile Edit Modal
  const [showProfileEdit, setShowProfileEdit] = useState(false);
  const [profileName, setProfileName] = useState('');
  const [profileTitle, setProfileTitle] = useState('');
  const [profileEmail, setProfileEmail] = useState('');
  const [profileAvatar, setProfileAvatar] = useState('');

  // Maintenance form inputs
  const [woDesc, setWoDesc] = useState('');
  const [woAssetId, setWoAssetId] = useState('MTR-01');
  const [woTech, setWoTech] = useState('J. Sutherland');

  // Feedback form inputs
  const [feedbackType, setFeedbackType] = useState('correct_fault');
  const [feedbackNotes, setFeedbackNotes] = useState('');
  const [feedbackPredId, setFeedbackPredId] = useState<number | null>(null);

  // Trigger data reload
  const triggerRefresh = () => setRefreshTrigger(prev => prev + 1);

  // Authentication Flow
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: emailInput, password: passwordInput })
      });
      if (res.ok) {
        const userData = await res.json();
        setUser(userData);
        // Load initial profile edit state
        setProfileName(userData.name);
        setProfileTitle(userData.title);
        setProfileEmail(userData.email);
        setProfileAvatar(userData.avatar || '');
      } else {
        // Local pre-seeded checks if backend is down
        const match = PRESEEDED_ACCOUNTS.find(a => a.email.toLowerCase() === emailInput.toLowerCase() && passwordInput !== '');
        if (match) {
          setUser(match);
          setProfileName(match.name);
          setProfileTitle(match.title);
          setProfileEmail(match.email);
          setProfileAvatar(match.avatar || '');
        } else {
          setAuthError('Access Denied. Invalid credentials or database offline.');
        }
      }
    } catch {
      // Fallback
      const match = PRESEEDED_ACCOUNTS.find(a => a.email.toLowerCase() === emailInput.toLowerCase());
      if (match) {
        setUser(match);
        setProfileName(match.name);
        setProfileTitle(match.title);
        setProfileEmail(match.email);
        setProfileAvatar(match.avatar || '');
      } else {
        setAuthError('Database offline. Choose a valid pre-seeded account (e.g. rasyaad@ASTRA.com / admin123).');
      }
    }
  };

  // Update Profile
  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/users/profile/${user.email}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: profileName, title: profileTitle, new_email: profileEmail, avatar: profileAvatar })
      });
      if (res.ok) {
        setUser({ ...user, name: profileName, title: profileTitle, email: profileEmail, avatar: profileAvatar });
        setShowProfileEdit(false);
      } else {
        setUser({ ...user, name: profileName, title: profileTitle, email: profileEmail, avatar: profileAvatar });
        setShowProfileEdit(false);
      }
    } catch {
      // Offline fallback
      setUser({ ...user, name: profileName, title: profileTitle, email: profileEmail, avatar: profileAvatar });
      setShowProfileEdit(false);
    }
  };

  // Create Work Order
  const handleCreateWorkOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!woDesc) return;
    
    const assetName = motors.find(m => m.motor_id === woAssetId)?.name || 'Conveyor';
    try {
      const res = await fetch(`${API_BASE}/work_orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ asset_id: woAssetId, asset_name: assetName, description: woDesc, assigned_tech: woTech })
      });
      if (res.ok) {
        setWoDesc('');
        triggerRefresh();
      } else {
        throw new Error();
      }
    } catch {
      // Mock insert
      const newWO = {
        id: `WO-${9100 + workOrders.length}`,
        asset_id: woAssetId,
        asset_name: `Motor ${woAssetId} (${assetName})`,
        description: woDesc,
        status: 'Pending',
        created_at: new Date().toISOString(),
        assigned_tech: woTech
      };
      setWorkOrders([newWO, ...workOrders]);
      setWoDesc('');
    }
  };

  // Submit Feedback
  const handleSubmitFeedback = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedbackPredId) return;
    try {
      const res = await fetch(`${API_BASE}/maintenance/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ motor_id: selectedMotorId, prediction_id: feedbackPredId, feedback_type: feedbackType, notes: feedbackNotes })
      });
      if (res.ok) {
        setFeedbackNotes('');
        alert('Feedback submitted successfully!');
        triggerRefresh();
      }
    } catch {
      alert('Feedback logged (Simulation Mode).');
      setFeedbackNotes('');
    }
  };

  // Acknowledge Alert
  const handleAcknowledgeAlert = async (id: number) => {
    try {
      await fetch(`${API_BASE}/alerts/${id}/acknowledge`, { method: 'POST' });
      triggerRefresh();
    } catch {
      // Mock Acknowledge
      setAlerts(prev => prev.filter(a => a.id !== id));
    }
  };

  // Load Database Data
  useEffect(() => {
    if (!user) return;

    
    const fetchData = async () => {
      try {
        const healthRes = await fetch(`${API_BASE}/health`);
        setIsBackendConnected(healthRes.ok);

        // Fetch Motors
        const motorsRes = await fetch(`${API_BASE}/motors`);
        if (motorsRes.ok) {
          const motorsData = await motorsRes.json();
          setMotors(motorsData);
        }

        // Fetch Overview Metrics
        const overviewRes = await fetch(`${API_BASE}/dashboard/overview`);
        if (overviewRes.ok) {
          const overviewData = await overviewRes.json();
          setOverviewMetrics(overviewData);
        }

        // Fetch Active Alerts
        const alertsRes = await fetch(`${API_BASE}/alerts`);
        if (alertsRes.ok) {
          const alertsData = await alertsRes.json();
          setAlerts(alertsData);
        }

        // Fetch Work Orders
        const woRes = await fetch(`${API_BASE}/work_orders`);
        if (woRes.ok) {
          const woData = await woRes.json();
          setWorkOrders(woData);
        }

        // Fetch Production Risks
        const riskRes = await fetch(`${API_BASE}/dashboard/production-risk`);
        if (riskRes.ok) {
          const riskData = await riskRes.json();
          setProductionRisk(riskData);
        }
      } catch (err) {
        console.log("Using synthetic local fallback data due to backend offline:", err);
        setIsBackendConnected(false);
        setupMockData();
      }
    };

    const setupMockData = () => {
      const mockMotors = [
        { motor_id: 'MTR-01', name: 'Conveyor Drive', location: 'Line 1', power_kw: 11.0, nominal_rpm: 1500, nominal_current: 22.0, max_temp: 85.0, max_vibration: 4.5, is_critical: true, severity: 'NORMAL', health_score: 98.4, anomaly_score: 0.12, fault_type: 'healthy', recommendation: 'Continue routine monitoring.', last_update: new Date() },
        { motor_id: 'MTR-02', name: 'Compressor', location: 'Utility', power_kw: 55.0, nominal_rpm: 2950, nominal_current: 98.0, max_temp: 90.0, max_vibration: 6.0, is_critical: true, severity: 'WARNING', health_score: 52.8, anomaly_score: 0.74, fault_type: 'outer_race', recommendation: 'Plan outer race bearing maintenance this week.', last_update: new Date() },
        { motor_id: 'MTR-03', name: 'Fan/Blower', location: 'Line 2', power_kw: 18.5, nominal_rpm: 1450, nominal_current: 35.0, max_temp: 80.0, max_vibration: 5.0, is_critical: false, severity: 'NORMAL', health_score: 96.1, anomaly_score: 0.18, fault_type: 'healthy', recommendation: 'Continue routine monitoring.', last_update: new Date() },
        { motor_id: 'MTR-04', name: 'Pump', location: 'Utility', power_kw: 30.0, nominal_rpm: 1480, nominal_current: 58.0, max_temp: 85.0, max_vibration: 8.0, is_critical: true, severity: 'CRITICAL', health_score: 28.5, anomaly_score: 1.34, fault_type: 'inner_race', recommendation: 'Inspect immediately — shutdown risk.', last_update: new Date() },
        { motor_id: 'MTR-05', name: 'Mixer', location: 'Line 1', power_kw: 45.0, nominal_rpm: 980, nominal_current: 88.0, max_temp: 95.0, max_vibration: 7.0, is_critical: true, severity: 'NORMAL', health_score: 92.4, anomaly_score: 0.22, fault_type: 'healthy', recommendation: 'Continue routine monitoring.', last_update: new Date() },
        { motor_id: 'MTR-06', name: 'Spindle', location: 'Line 3', power_kw: 7.5, nominal_rpm: 3000, nominal_current: 15.0, max_temp: 75.0, max_vibration: 3.5, is_critical: false, severity: 'NORMAL', health_score: 95.3, anomaly_score: 0.15, fault_type: 'healthy', recommendation: 'Continue routine monitoring.', last_update: new Date() }
      ];
      setMotors(mockMotors);
      setOverviewMetrics({
        total_motors: 6,
        healthy_count: 4,
        warning_count: 1,
        critical_count: 1,
        avg_health_score: 76.6,
        active_alerts_count: 2
      });
      setAlerts([
        { id: 101, motor_id: 'MTR-04', severity: 'CRITICAL', fault_type: 'inner_race', health_score: 28.5, anomaly_score: 1.34, predicted_at: new Date().toISOString(), recommendation: 'Inspect immediately — shutdown risk.', top_cause: 'RPM slip percentage is abnormally high. RPM drop contributing 41% to this anomaly.' },
        { id: 102, motor_id: 'MTR-02', severity: 'WARNING', fault_type: 'outer_race', health_score: 52.8, anomaly_score: 0.74, predicted_at: new Date().toISOString(), recommendation: 'Plan outer race bearing maintenance this week.', top_cause: 'Vibration RMS acceleration is abnormally high. Vibration contributing 31% to this anomaly.' }
      ]);
      setWorkOrders([
        { id: 'WO-8821', asset_id: 'MTR-01', asset_name: 'Motor MTR-01 (Conveyor Drive)', description: 'Replace outer race bearing assembly', status: 'Completed', created_at: '2026-07-01 10:00:00', assigned_tech: 'J. Sutherland' },
        { id: 'WO-8902', asset_id: 'MTR-04', asset_name: 'Motor MTR-04 (Pump)', description: 'Lubricate gearbox bearing drive', status: 'Completed', created_at: '2026-07-05 14:30:00', assigned_tech: 'M. Rossi' },
        { id: 'WO-8905', asset_id: 'MTR-05', asset_name: 'Motor MTR-05 (Mixer)', description: 'Calibrate telemetry transmitter speed loop', status: 'Completed', created_at: '2026-07-09 09:15:00', assigned_tech: 'S. O' + "Brien" }
      ]);
      setProductionRisk([
        { motor_id: 'MTR-04', name: 'Pump', location: 'Utility', severity: 'CRITICAL', recommendation: 'Inspect immediately — shutdown risk', is_critical: true },
        { motor_id: 'MTR-02', name: 'Compressor', location: 'Utility', severity: 'WARNING', recommendation: 'Plan bearing maintenance', is_critical: true }
      ]);
    };

    fetchData();
  }, [user, refreshTrigger]);

  // Load motor telemetry and predictions details
  useEffect(() => {
    if (!user || !selectedMotorId) return;

    const fetchMotorDetails = async () => {
      try {
        const sensRes = await fetch(`${API_BASE}/motors/${selectedMotorId}/sensors?limit=50`);
        if (sensRes.ok) {
          const sensData = await sensRes.json();
          setTelemetry(sensData.reverse()); // Chronological order
        }

        const predRes = await fetch(`${API_BASE}/motors/${selectedMotorId}/prediction`);
        if (predRes.ok) {
          const predData = await predRes.json();
          setPrediction(predData);
          setFeedbackPredId(predData.id || 101);
        }

        const histRes = await fetch(`${API_BASE}/motors/${selectedMotorId}/history?limit=30`);
        if (histRes.ok) {
          const histData = await histRes.json();
          setHistory(histData.reverse());
        }
      } catch {
        // Setup local mock data for selected motor details
        setFeedbackPredId(101);
        const count = 30;
        const mockTel = [];
        const mockHist = [];
        const motor = motors.find(m => m.motor_id === selectedMotorId) || motors[0];
        
        let t_base = motor ? motor.max_temp - 25.0 : 50.0;
        let v_base = motor ? motor.max_vibration - 3.5 : 1.2;
        let r_base = motor ? motor.nominal_rpm : 1500;
        let c_base = motor ? motor.nominal_current : 15;
        
        if (motor?.severity === 'WARNING') {
          t_base += 15.0;
          v_base += 2.0;
        } else if (motor?.severity === 'CRITICAL') {
          t_base += 30.0;
          v_base += 4.5;
        }

        for (let i = 0; i < count; i++) {
          const date = new Date(Date.now() - (count - i) * 60000);
          mockTel.push({
            recorded_at: date,
            temperature: t_base + Math.random() * 4.0,
            vibration_x: v_base + Math.random() * 0.8,
            current_a: c_base + Math.random() * 1.5,
            rpm: r_base - (motor?.severity === 'CRITICAL' ? 120 : 10) + Math.random() * 10,
            torque_nm: 25.0 + Math.random() * 3.0,
            fault_label: motor?.fault_type || 'healthy'
          });
          
          mockHist.push({
            predicted_at: date,
            health_score: motor ? motor.health_score - (30 - i) * 0.2 : 95.0,
            anomaly_score: motor ? motor.anomaly_score * (i / count) : 0.15,
            severity: motor ? motor.severity : 'NORMAL'
          });
        }
        setTelemetry(mockTel);
        setHistory(mockHist);
        setPrediction({
          motor_id: selectedMotorId,
          health_score: motor ? motor.health_score : 95.0,
          anomaly_score: motor ? motor.anomaly_score : 0.15,
          fault_type: motor ? motor.fault_type : 'healthy',
          rul_days: motor?.severity === 'CRITICAL' ? 2.4 : motor?.severity === 'WARNING' ? 6.1 : 125.0,
          severity: motor ? motor.severity : 'NORMAL',
          recommendation: motor ? motor.recommendation : 'Continue routine monitoring.',
          top_cause: motor?.severity === 'CRITICAL' ? 'RPM slip percentage is abnormally high.' : 'All systems operating within parameters.',
          predicted_at: new Date()
        });
      }
    };

    fetchMotorDetails();
  }, [selectedMotorId, motors]);

  // Clearance Check Helper
  const hasClearance = (required: number) => {
    if (!user) return false;
    const levels: any = { 'Level 1': 1, 'Level 2': 2, 'Level 3': 3, 'Level 4': 4 };
    return levels[user.clearance] >= required;
  };

  // Render Denied Screen
  const renderDenied = () => (
    <div className="glass-panel" style={{ padding: '60px 30px', textAlign: 'center', maxWidth: '600px', margin: '40px auto' }}>
      <Shield size={64} color="var(--danger)" style={{ marginBottom: '20px' }} />
      <h2 style={{ fontSize: '1.8rem', color: 'var(--text-bright)', marginBottom: '10px' }}>Security Clearance Denied</h2>
      <p style={{ color: 'var(--text-muted)', marginBottom: '30px' }}>
        Your account level ({user.clearance}) does not possess the credentials to access this system module. 
        Contact a Super Admin (Level 4) to request clearance modifications.
      </p>
      <button className="btn btn-secondary" onClick={() => setActiveTab('overview')}>Return to Overview</button>
    </div>
  );

  // Render Login Screen if not authenticated
  if (!user) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: 'radial-gradient(ellipse at center, #faf9f6 0%, #efeeeb 100%)', padding: '20px' }}>
        <div className="glass-panel" style={{ width: '100%', maxWidth: '440px', padding: '40px 30px' }}>
          <div style={{ textAlign: 'center', marginBottom: '30px' }}>
            <div style={{ display: 'inline-flex', padding: '12px', borderRadius: '12px', background: 'rgba(28,107,69,0.1)', color: 'var(--primary)', marginBottom: '15px' }}>
              <Cpu size={36} />
            </div>
            <h1 style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-bright)', letterSpacing: '0.5px' }}>ASTRA Predictive</h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '4px' }}>On-Premise Machine Diagnostics Hub</p>
          </div>

          {authError && (
            <div style={{ padding: '12px', borderRadius: '8px', background: 'rgba(192,57,43,0.1)', color: 'var(--danger)', fontSize: '0.85rem', marginBottom: '20px', border: '1px solid rgba(192,57,43,0.2)' }}>
              {authError}
            </div>
          )}

          <form onSubmit={handleLogin}>
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 500 }}>Email Address</label>
              <input 
                type="email" 
                value={emailInput}
                onChange={e => setEmailInput(e.target.value)}
                required
                style={{ width: '100%', padding: '10px 14px', borderRadius: '8px', background: '#FFFFFF', border: '1px solid var(--border-color)', color: 'var(--text-main)', outline: 'none', transition: 'all 0.2s' }}
              />
            </div>
            <div style={{ marginBottom: '25px' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 500 }}>Password</label>
              <input 
                type="password" 
                value={passwordInput}
                onChange={e => setPasswordInput(e.target.value)}
                required
                style={{ width: '100%', padding: '10px 14px', borderRadius: '8px', background: '#FFFFFF', border: '1px solid var(--border-color)', color: 'var(--text-main)', outline: 'none' }}
              />
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '12px', justifyContent: 'center' }}>
              Authenticate System Access
            </button>
          </form>

          <div style={{ marginTop: '25px', paddingTop: '20px', borderTop: '1px solid var(--border-color)' }}>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center', marginBottom: '10px' }}>Quick Access Pre-seeded Profiles:</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {PRESEEDED_ACCOUNTS.slice(1, 4).map(acc => (
                <button 
                  key={acc.email}
                  className="btn btn-secondary" 
                  style={{ fontSize: '0.75rem', padding: '6px 12px', justifyContent: 'space-between' }}
                  onClick={() => {
                    setEmailInput(acc.email);
                    setPasswordInput(acc.email.startsWith('maint') ? 'maint123' : 'admin123');
                  }}
                >
                  <span>{acc.name} ({acc.clearance})</span>
                  <span style={{ color: 'var(--primary)' }}>Select</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* ─── SIDEBAR NAVIGATION ─── */}
      <div className="sidebar">
        {/* User Card */}
        <div style={{ padding: '24px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '50%', background: 'var(--primary)', backgroundImage: user.avatar ? `url(${user.avatar})` : 'none', backgroundSize: 'cover', backgroundPosition: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            {!user.avatar && <User size={20} color="#FFF" />}
          </div>
          <div style={{ minWidth: 0 }}>
            <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-bright)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user.name}</h4>
            <span style={{ fontSize: '0.7rem', display: 'inline-block', padding: '2px 8px', borderRadius: '10px', background: 'rgba(28, 107, 69, 0.15)', color: '#1c6b45', fontWeight: 600, border: '1px solid rgba(28, 107, 69, 0.3)', marginTop: '4px' }}>
              {user.clearance}
            </span>
          </div>
          <button style={{ marginLeft: 'auto', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }} onClick={() => setShowProfileEdit(true)}>
            <Edit size={16} />
          </button>
        </div>

        {/* Navigation list */}
        <div style={{ flex: 1, padding: '20px 10px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <button className={`btn ${activeTab === 'overview' ? 'btn-primary' : 'btn-secondary'}`} style={{ border: 'none', justifyContent: 'flex-start' }} onClick={() => setActiveTab('overview')}>
            <Activity size={18} /> Overview Dashboard
          </button>
          <button className={`btn ${activeTab === 'monitoring' ? 'btn-primary' : 'btn-secondary'}`} style={{ border: 'none', justifyContent: 'flex-start' }} onClick={() => setActiveTab('monitoring')}>
            <Server size={18} /> Machine Fleet
          </button>
          <button className={`btn ${activeTab === 'detail' ? 'btn-primary' : 'btn-secondary'}`} style={{ border: 'none', justifyContent: 'flex-start' }} onClick={() => setActiveTab('detail')}>
            <Gauge size={18} /> Machine Diagnostics
          </button>
          <button className={`btn ${activeTab === 'diagnosis' ? 'btn-primary' : 'btn-secondary'}`} style={{ border: 'none', justifyContent: 'flex-start' }} onClick={() => setActiveTab('diagnosis')}>
            <Cpu size={18} /> ML Copilot & XAI
          </button>
          <button className={`btn ${activeTab === 'recommendation' ? 'btn-primary' : 'btn-secondary'}`} style={{ border: 'none', justifyContent: 'flex-start' }} onClick={() => setActiveTab('recommendation')}>
            <Hammer size={18} /> Action Console
          </button>
          <button className={`btn ${activeTab === 'history' ? 'btn-primary' : 'btn-secondary'}`} style={{ border: 'none', justifyContent: 'flex-start' }} onClick={() => setActiveTab('history')}>
            <ClipboardList size={18} /> Work Orders Console
          </button>
          <button className={`btn ${activeTab === 'feedback' ? 'btn-primary' : 'btn-secondary'}`} style={{ border: 'none', justifyContent: 'flex-start' }} onClick={() => setActiveTab('feedback')}>
            <CheckSquare size={18} /> Feedback Center
          </button>
          <button className={`btn ${activeTab === 'notifications' ? 'btn-primary' : 'btn-secondary'}`} style={{ border: 'none', justifyContent: 'flex-start' }} onClick={() => setActiveTab('notifications')}>
            <Settings size={18} /> Notification Config
          </button>
        </div>

        {/* Network status and Logout */}
        <div style={{ padding: '15px 20px', borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: isBackendConnected ? 'var(--success)' : 'var(--danger)', display: 'inline-block' }}></span>
            <span>Database Status: {isBackendConnected ? 'ONLINE (Postgres)' : 'OFFLINE (Fallback)'}</span>
          </div>
          <button className="btn btn-secondary" style={{ width: '100%', justifyContent: 'center' }} onClick={() => setUser(null)}>
            <LogOut size={16} /> Close Dashboard
          </button>
        </div>
      </div>

      {/* ─── MAIN APP ROUTING PANELS ─── */}
      <div className="main-content">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '30px' }}>
          <div>
            <h1 style={{ color: 'var(--text-bright)', fontSize: '2rem', fontWeight: 700 }}>Project ASTRA</h1>
            <p style={{ color: 'var(--text-muted)' }}>On-Premise Induction Motor Fleet Diagnostic Platform</p>
          </div>
          <button className="btn btn-secondary" onClick={triggerRefresh}>
            <RefreshCw size={16} /> Sync Telemetry
          </button>
        </div>

        {/* ─── TAB 1: OVERVIEW DASHBOARD ─── */}
        {activeTab === 'overview' && (
          <div>
            {/* KPI metrics row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '20px', marginBottom: '30px' }}>
              <div className="glass-panel" style={{ padding: '20px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Induction Motor Fleet</span>
                <h3 style={{ fontSize: '2rem', color: 'var(--text-bright)', marginTop: '5px' }}>{overviewMetrics.total_motors}</h3>
              </div>
              <div className="glass-panel glow-card-success" style={{ padding: '20px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Healthy Status</span>
                <h3 style={{ fontSize: '2rem', color: 'var(--success)', marginTop: '5px' }}>{overviewMetrics.healthy_count}</h3>
              </div>
              <div className="glass-panel glow-card-warning" style={{ padding: '20px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Warnings Active</span>
                <h3 style={{ fontSize: '2rem', color: 'var(--warning)', marginTop: '5px' }}>{overviewMetrics.warning_count}</h3>
              </div>
              <div className="glass-panel glow-card-danger" style={{ padding: '20px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Critical Failures</span>
                <h3 style={{ fontSize: '2rem', color: 'var(--danger)', marginTop: '5px' }}>{overviewMetrics.critical_count}</h3>
              </div>
              <div className="glass-panel" style={{ padding: '20px' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Avg Health Score</span>
                <h3 style={{ fontSize: '2rem', color: 'var(--text-bright)', marginTop: '5px' }}>{overviewMetrics.avg_health_score}%</h3>
              </div>
            </div>

            {/* Production risk banner */}
            {productionRisk.length > 0 && (
              <div className="glass-panel glow-card-danger" style={{ padding: '20px', marginBottom: '30px', background: 'rgba(239,68,68,0.06)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--danger)', fontWeight: 600, marginBottom: '8px' }}>
                  <AlertTriangle size={20} />
                  <span>CRITICAL PRODUCTION LINE RISKS DETECTED</span>
                </div>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-main)' }}>
                  A critical asset fault is active on critical production lines. Immediate action required.
                </p>
                <div style={{ marginTop: '10px', display: 'flex', gap: '10px' }}>
                  {productionRisk.map(pr => (
                    <span key={pr.motor_id} style={{ fontSize: '0.8rem', background: 'rgba(239,68,68,0.15)', color: '#FCA5A5', padding: '4px 10px', borderRadius: '4px', border: '1px solid rgba(239,68,68,0.3)' }}>
                      Line {pr.location} — {pr.name} ({pr.motor_id})
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '30px' }}>
              {/* Motors Grid */}
              <div>
                <h3 style={{ color: 'var(--text-bright)', marginBottom: '15px', fontSize: '1.2rem', fontWeight: 600 }}>Fleet Health Matrix</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '20px' }}>
                  {motors.map(motor => (
                    <div 
                      key={motor.motor_id} 
                      className={`glass-panel ${motor.severity === 'CRITICAL' ? 'glow-card-danger' : motor.severity === 'WARNING' ? 'glow-card-warning' : 'glow-card-success'}`}
                      style={{ padding: '20px', cursor: 'pointer' }}
                      onClick={() => {
                        setSelectedMotorId(motor.motor_id);
                        setActiveTab('detail');
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                        <h4 style={{ color: 'var(--text-bright)', fontSize: '1.1rem' }}>{motor.motor_id}</h4>
                        <span className={`badge ${motor.severity === 'CRITICAL' ? 'badge-critical' : motor.severity === 'WARNING' ? 'badge-warning' : 'badge-normal'}`}>
                          {motor.severity}
                        </span>
                      </div>
                      <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '12px' }}>{motor.name} • {motor.location}</p>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                        <span>Health Status:</span>
                        <span style={{ fontWeight: 600, color: motor.health_score > 70 ? 'var(--success)' : motor.health_score > 40 ? 'var(--warning)' : 'var(--danger)' }}>
                          {motor.health_score}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Active Alerts Panel */}
              <div>
                <h3 style={{ color: 'var(--text-bright)', marginBottom: '15px', fontSize: '1.2rem', fontWeight: 600 }}>Active Alerts</h3>
                <div className="glass-panel" style={{ padding: '20px', maxHeight: '420px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '15px' }}>
                  {alerts.length === 0 ? (
                    <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '20px' }}>All machine components performing within normal parameters.</p>
                  ) : (
                    alerts.map(alert => (
                      <div key={alert.id} style={{ padding: '12px', borderRadius: '8px', background: 'var(--bg-card-hover)', border: '1px solid var(--border-color)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                          <span style={{ fontWeight: 600, color: 'var(--text-bright)' }}>{alert.motor_id}</span>
                          <span className={`badge ${alert.severity === 'CRITICAL' ? 'badge-critical' : 'badge-warning'}`}>{alert.severity}</span>
                        </div>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '8px' }}>{alert.recommendation}</p>
                        <button className="btn btn-secondary" style={{ fontSize: '0.75rem', padding: '4px 8px' }} onClick={() => handleAcknowledgeAlert(alert.id)}>
                          Acknowledge Alert
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ─── TAB 2: MACHINE MONITORING FLEET ─── */}
        {activeTab === 'monitoring' && (
          <div className="glass-panel" style={{ padding: '30px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ color: 'var(--text-bright)', fontSize: '1.4rem' }}>Induction Motor Asset Fleet</h2>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Showing {motors.length} motors</span>
            </div>
            
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    <th style={{ padding: '12px 8px' }}>Motor ID</th>
                    <th style={{ padding: '12px 8px' }}>Name</th>
                    <th style={{ padding: '12px 8px' }}>Line Location</th>
                    <th style={{ padding: '12px 8px' }}>Capacity (kW)</th>
                    <th style={{ padding: '12px 8px' }}>Criticality</th>
                    <th style={{ padding: '12px 8px' }}>Anomaly Score</th>
                    <th style={{ padding: '12px 8px' }}>Health</th>
                    <th style={{ padding: '12px 8px' }}>Diagnostic Status</th>
                    <th style={{ padding: '12px 8px' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {motors.map(motor => (
                    <tr key={motor.motor_id} style={{ borderBottom: '1px solid var(--border-color)', fontSize: '0.9rem' }}>
                      <td style={{ padding: '16px 8px', fontWeight: 600, color: 'var(--text-bright)' }}>{motor.motor_id}</td>
                      <td style={{ padding: '16px 8px' }}>{motor.name}</td>
                      <td style={{ padding: '16px 8px' }}>{motor.location}</td>
                      <td style={{ padding: '16px 8px' }}>{motor.power_kw} kW</td>
                      <td style={{ padding: '16px 8px' }}>
                        {motor.is_critical ? (
                          <span style={{ color: 'var(--danger)', fontWeight: 600, fontSize: '0.8rem' }}>CRITICAL PATH</span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>Standard</span>
                        )}
                      </td>
                      <td style={{ padding: '16px 8px' }}>{(motor.anomaly_score || 0).toFixed(2)}</td>
                      <td style={{ padding: '16px 8px', fontWeight: 600, color: motor.health_score > 70 ? 'var(--success)' : motor.health_score > 40 ? 'var(--warning)' : 'var(--danger)' }}>
                        {motor.health_score}%
                      </td>
                      <td style={{ padding: '16px 8px' }}>
                        <span className={`badge ${motor.severity === 'CRITICAL' ? 'badge-critical' : motor.severity === 'WARNING' ? 'badge-warning' : 'badge-normal'}`}>
                          {motor.severity}
                        </span>
                      </td>
                      <td style={{ padding: '16px 8px' }}>
                        <button className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '6px 10px' }} onClick={() => {
                          setSelectedMotorId(motor.motor_id);
                          setActiveTab('detail');
                        }}>
                          Diagnostics
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ─── TAB 3: MACHINE DIAGNOSTICS & TELEMETRY CHARTS ─── */}
        {activeTab === 'detail' && (
          <div>
            {/* Motor selector drop down */}
            <div className="glass-panel" style={{ padding: '15px 20px', marginBottom: '30px', display: 'flex', alignItems: 'center', gap: '20px' }}>
              <span style={{ color: 'var(--text-bright)', fontWeight: 600 }}>Active Diagnostic Asset:</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                {motors.map(m => (
                  <button 
                    key={m.motor_id}
                    className={`btn ${selectedMotorId === m.motor_id ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ padding: '6px 12px', fontSize: '0.85rem' }}
                    onClick={() => setSelectedMotorId(m.motor_id)}
                  >
                    {m.motor_id} ({m.name})
                  </button>
                ))}
              </div>
            </div>

            {/* Gauge row */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '30px', marginBottom: '30px' }}>
              {/* Gauges panel */}
              <div className="glass-panel" style={{ padding: '25px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                <h3 style={{ color: 'var(--text-bright)', marginBottom: '20px', fontSize: '1.1rem' }}>Overall Health Score</h3>
                <div style={{ position: 'relative', width: '160px', height: '160px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <svg width="100%" height="100%" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="40" stroke="rgba(0,0,0,0.06)" strokeWidth="8" fill="none" />
                    <circle 
                      cx="50" 
                      cy="50" 
                      r="40" 
                      stroke={prediction?.health_score > 70 ? 'var(--success)' : prediction?.health_score > 40 ? 'var(--warning)' : 'var(--danger)'} 
                      strokeWidth="8" 
                      fill="none" 
                      strokeDasharray="251.2"
                      strokeDashoffset={251.2 - (251.2 * (prediction?.health_score || 100.0)) / 100.0}
                      strokeLinecap="round"
                      transform="rotate(-90 50 50)"
                    />
                  </svg>
                  <div style={{ position: 'absolute', textAlign: 'center' }}>
                    <span style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-bright)' }}>{prediction?.health_score?.toFixed(0)}%</span>
                    <span style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)' }}>SYSTEM HEALTH</span>
                  </div>
                </div>
                
                <div style={{ width: '100%', marginTop: '20px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '15px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.85rem' }}>
                    <span>Anomaly Index:</span>
                    <span style={{ fontWeight: 600, color: prediction?.is_anomaly ? 'var(--danger)' : 'var(--success)' }}>
                      {(prediction?.anomaly_score || 0).toFixed(2)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                    <span>Remaining Life:</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-bright)' }}>
                      {prediction?.rul_days?.toFixed(1)} Days
                    </span>
                  </div>
                </div>
              </div>

              {/* Anomaly timeline */}
              <div className="glass-panel" style={{ padding: '25px' }}>
                <h3 style={{ color: 'var(--text-bright)', marginBottom: '20px', fontSize: '1.1rem' }}>Anomaly Index Trend</h3>
                {/* SVG Trend Line */}
                <div style={{ height: '180px', width: '100%' }}>
                  {history.length > 0 ? (
                    <svg width="100%" height="100%" style={{ overflow: 'visible' }}>
                      {/* Grid Lines */}
                      <line x1="0" y1="180" x2="100%" y2="180" stroke="rgba(0,0,0,0.06)" />
                      <line x1="0" y1="90" x2="100%" y2="90" stroke="rgba(0,0,0,0.06)" />
                      <line x1="0" y1="0" x2="100%" y2="0" stroke="rgba(0,0,0,0.06)" />
                      
                      {/* Scaled Trend Line */}
                      <polyline
                        fill="none"
                        stroke="var(--primary)"
                        strokeWidth="3"
                        className="chart-line"
                        points={history.map((hist, idx) => {
                          const x = (idx / (history.length - 1)) * 100;
                          const max_y = Math.max(...history.map(h => h.anomaly_score), 1.0);
                          const y = 180 - (hist.anomaly_score / max_y) * 160;
                          return `${x}%,${y}`;
                        }).join(' ')}
                      />
                    </svg>
                  ) : (
                    <p style={{ color: 'var(--text-muted)', textAlign: 'center', lineHeight: '180px' }}>Loading trend data...</p>
                  )}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '8px' }}>
                  <span>24 Hours Ago</span>
                  <span>Latest Update</span>
                </div>
              </div>
            </div>

            {/* 5 Real-Time Sensor Telemetry Charts */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '30px' }}>
              
              {/* Chart 1: Temperature */}
              <div className="glass-panel" style={{ padding: '20px' }}>
                <h4 style={{ color: 'var(--text-bright)', marginBottom: '15px', fontSize: '0.95rem', fontWeight: 600 }}>1. Stator Temperature (°C)</h4>
                <div style={{ height: '140px' }}>
                  <svg width="100%" height="100%" style={{ overflow: 'visible' }}>
                    <polyline
                      fill="none"
                      stroke="#EF4444"
                      strokeWidth="2.5"
                      points={telemetry.map((tel, idx) => {
                        const x = (idx / (telemetry.length - 1)) * 100;
                        const y = 140 - (tel.temperature / 150) * 120;
                        return tel.temperature ? `${x}%,${y}` : ``;
                      }).join(' ')}
                    />
                  </svg>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '5px' }}>
                  <span>Min: {Math.min(...telemetry.map(t => t.temperature || 50).filter(Boolean)).toFixed(1)}°C</span>
                  <span>Max: {Math.max(...telemetry.map(t => t.temperature || 80).filter(Boolean)).toFixed(1)}°C</span>
                </div>
              </div>

              {/* Chart 2: Vibration */}
              <div className="glass-panel" style={{ padding: '20px' }}>
                <h4 style={{ color: 'var(--text-bright)', marginBottom: '15px', fontSize: '0.95rem', fontWeight: 600 }}>2. Vibration RMS Acceleration (g / mm/s)</h4>
                <div style={{ height: '140px' }}>
                  <svg width="100%" height="100%" style={{ overflow: 'visible' }}>
                    <polyline
                      fill="none"
                      stroke="#3B82F6"
                      strokeWidth="2.5"
                      points={telemetry.map((tel, idx) => {
                        const x = (idx / (telemetry.length - 1)) * 100;
                        const y = 140 - (tel.vibration_x / 10) * 120;
                        return `${x}%,${y}`;
                      }).join(' ')}
                    />
                  </svg>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '5px' }}>
                  <span>Min: {Math.min(...telemetry.map(t => t.vibration_x || 0.1)).toFixed(2)} mm/s</span>
                  <span>Max: {Math.max(...telemetry.map(t => t.vibration_x || 1.2)).toFixed(2)} mm/s</span>
                </div>
              </div>

              {/* Chart 3: Motor Current */}
              <div className="glass-panel" style={{ padding: '20px' }}>
                <h4 style={{ color: 'var(--text-bright)', marginBottom: '15px', fontSize: '0.95rem', fontWeight: 600 }}>3. Stator Current (Ampere)</h4>
                <div style={{ height: '140px' }}>
                  <svg width="100%" height="100%" style={{ overflow: 'visible' }}>
                    <polyline
                      fill="none"
                      stroke="#10B981"
                      strokeWidth="2.5"
                      points={telemetry.map((tel, idx) => {
                        const x = (idx / (telemetry.length - 1)) * 100;
                        const y = 140 - (tel.current_a / 120) * 120;
                        return `${x}%,${y}`;
                      }).join(' ')}
                    />
                  </svg>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '5px' }}>
                  <span>Min: {Math.min(...telemetry.map(t => t.current_a || 1.2)).toFixed(1)} A</span>
                  <span>Max: {Math.max(...telemetry.map(t => t.current_a || 15)).toFixed(1)} A</span>
                </div>
              </div>

              {/* Chart 4: RPM */}
              <div className="glass-panel" style={{ padding: '20px' }}>
                <h4 style={{ color: 'var(--text-bright)', marginBottom: '15px', fontSize: '0.95rem', fontWeight: 600 }}>4. Motor Shaft Speed (RPM)</h4>
                <div style={{ height: '140px' }}>
                  <svg width="100%" height="100%" style={{ overflow: 'visible' }}>
                    <polyline
                      fill="none"
                      stroke="#8B5CF6"
                      strokeWidth="2.5"
                      points={telemetry.map((tel, idx) => {
                        const x = (idx / (telemetry.length - 1)) * 100;
                        const y = 140 - (tel.rpm / 3500) * 120;
                        return `${x}%,${y}`;
                      }).join(' ')}
                    />
                  </svg>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '5px' }}>
                  <span>Min: {Math.min(...telemetry.map(t => t.rpm || 900)).toFixed(0)} RPM</span>
                  <span>Max: {Math.max(...telemetry.map(t => t.rpm || 1500)).toFixed(0)} RPM</span>
                </div>
              </div>

              {/* Chart 5: Torque */}
              <div className="glass-panel" style={{ padding: '20px' }}>
                <h4 style={{ color: 'var(--text-bright)', marginBottom: '15px', fontSize: '0.95rem', fontWeight: 600 }}>5. Load Torque (Nm)</h4>
                <div style={{ height: '140px' }}>
                  <svg width="100%" height="100%" style={{ overflow: 'visible' }}>
                    <polyline
                      fill="none"
                      stroke="#F59E0B"
                      strokeWidth="2.5"
                      points={telemetry.map((tel, idx) => {
                        const x = (idx / (telemetry.length - 1)) * 100;
                        const y = 140 - (tel.torque_nm / 150) * 120;
                        return `${x}%,${y}`;
                      }).join(' ')}
                    />
                  </svg>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '5px' }}>
                  <span>Min: {Math.min(...telemetry.map(t => t.torque_nm || 10)).toFixed(1)} Nm</span>
                  <span>Max: {Math.max(...telemetry.map(t => t.torque_nm || 35)).toFixed(1)} Nm</span>
                </div>
              </div>

            </div>
          </div>
        )}

        {/* ─── TAB 4: PREDICTION & DIAGNOSIS ─── */}
        {activeTab === 'diagnosis' && (
          <div>
            {!hasClearance(3) ? renderDenied() : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
                {/* Diagnostic breakdown */}
                <div className="glass-panel" style={{ padding: '30px' }}>
                  <h3 style={{ color: 'var(--text-bright)', fontSize: '1.3rem', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Cpu size={22} color="var(--primary)" /> AI Diagnostic Analyzer
                  </h3>

                  <div style={{ padding: '20px', borderRadius: '8px', background: 'var(--bg-card-hover)', marginBottom: '25px', border: '1px solid var(--border-color)' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Classified Fault Profile:</span>
                    <h2 style={{ textTransform: 'uppercase', color: prediction?.fault_type !== 'healthy' ? 'var(--danger)' : 'var(--success)', fontSize: '1.6rem', marginTop: '5px' }}>
                      {prediction?.fault_type ? prediction.fault_type.replace('_', ' ') : 'Healthy'}
                    </h2>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '5px' }}>
                      Model confidence: {prediction ? (prediction.fault_confidence * 100).toFixed(1) : '100'}%
                    </p>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '5px' }}>
                        <span>Outer Race Damage Probability</span>
                        <span>{prediction?.fault_type === 'outer_race' ? '98%' : '2%'}</span>
                      </div>
                      <div style={{ height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px' }}>
                        <div style={{ height: '100%', background: 'var(--danger)', borderRadius: '3px', width: prediction?.fault_type === 'outer_race' ? '98%' : '2%' }}></div>
                      </div>
                    </div>

                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '5px' }}>
                        <span>Inner Race Damage Probability</span>
                        <span>{prediction?.fault_type === 'inner_race' ? '98%' : '1%'}</span>
                      </div>
                      <div style={{ height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px' }}>
                        <div style={{ height: '100%', background: 'var(--warning)', borderRadius: '3px', width: prediction?.fault_type === 'inner_race' ? '98%' : '1%' }}></div>
                      </div>
                    </div>

                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '5px' }}>
                        <span>Roller Component Fault</span>
                        <span>{prediction?.fault_type === 'roller' ? '95%' : '0%'}</span>
                      </div>
                      <div style={{ height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px' }}>
                        <div style={{ height: '100%', background: 'var(--primary)', borderRadius: '3px', width: prediction?.fault_type === 'roller' ? '95%' : '0%' }}></div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* XAI explaining contribution */}
                <div className="glass-panel" style={{ padding: '30px' }}>
                  <h3 style={{ color: 'var(--text-bright)', fontSize: '1.3rem', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Shield size={22} color="var(--primary)" /> Explainable AI (XAI) Dashboard
                  </h3>
                  
                  <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '20px' }}>
                    This section translates LSTM Autoencoder reconstruction errors into clear parameter contribution analyses.
                  </p>

                  <div style={{ padding: '20px', borderRadius: '8px', borderLeft: '4px solid var(--primary)', background: 'rgba(28, 107, 69, 0.05)', marginBottom: '25px' }}>
                    <h4 style={{ fontWeight: 600, color: 'var(--text-bright)', fontSize: '0.95rem', marginBottom: '5px' }}>Top Fault Contributor</h4>
                    <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', fontStyle: 'italic' }}>
                      "{prediction?.top_cause || 'All metrics operating within target limits.'}"
                    </p>
                  </div>

                  <h4 style={{ color: 'var(--text-bright)', fontSize: '0.95rem', marginBottom: '12px' }}>Parameter Contribution Breakdown</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.85rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Vibration RMS Acceleration (Vibration Faults)</span>
                      <span style={{ fontWeight: 600 }}>{prediction?.severity !== 'NORMAL' ? '43%' : '8%'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Shaft Speed slip percentage (RPM Drop)</span>
                      <span style={{ fontWeight: 600 }}>{prediction?.severity !== 'NORMAL' ? '29%' : '5%'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Current Total Harmonic Distortion (Electrical Faults)</span>
                      <span style={{ fontWeight: 600 }}>{prediction?.severity !== 'NORMAL' ? '18%' : '4%'}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Stator Temperature Gradient (Overload Friction)</span>
                      <span style={{ fontWeight: 600 }}>{prediction?.severity !== 'NORMAL' ? '10%' : '2%'}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ─── TAB 5: MAINTENANCE CHECKLIST & TECH ASSIGNMENT ─── */}
        {activeTab === 'recommendation' && (
          <div>
            {!hasClearance(2) ? renderDenied() : (
              <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '30px' }}>
                {/* Recommendations and action plans */}
                <div className="glass-panel" style={{ padding: '30px' }}>
                  <h3 style={{ color: 'var(--text-bright)', fontSize: '1.3rem', marginBottom: '15px' }}>Prescriptive Maintenance Actions</h3>
                  
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '20px' }}>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Status Severity:</span>
                    <span className={`badge ${prediction?.severity === 'CRITICAL' ? 'badge-critical' : prediction?.severity === 'WARNING' ? 'badge-warning' : 'badge-normal'}`}>
                      {prediction?.severity}
                    </span>
                  </div>

                  <div style={{ padding: '15px', borderRadius: '8px', background: 'var(--bg-card-hover)', border: '1px solid var(--border-color)', marginBottom: '25px' }}>
                    <h4 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '5px' }}>Recommended Maintenance Directive:</h4>
                    <p style={{ fontSize: '1.05rem', color: 'var(--text-bright)', fontWeight: 500 }}>{prediction?.recommendation}</p>
                  </div>

                  <h4 style={{ color: 'var(--text-bright)', fontSize: '1rem', marginBottom: '15px', fontWeight: 600 }}>Standard Checklist:</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.9rem', cursor: 'pointer' }}>
                      <input type="checkbox" defaultChecked={prediction?.severity === 'NORMAL'} style={{ accentColor: 'var(--primary)' }} />
                      <span>Lockout-Tagout (LOTO) isolation verification on Line Switch</span>
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.9rem', cursor: 'pointer' }}>
                      <input type="checkbox" style={{ accentColor: 'var(--primary)' }} />
                      <span>Inspect bearing housing seals for lube leakages</span>
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.9rem', cursor: 'pointer' }}>
                      <input type="checkbox" style={{ accentColor: 'var(--primary)' }} />
                      <span>Perform vibration spectrum cross-checks with secondary handheld telemetry</span>
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.9rem', cursor: 'pointer' }}>
                      <input type="checkbox" style={{ accentColor: 'var(--primary)' }} />
                      <span>Re-lubricate bearing assembly (Shell Gadus S2 or equivalent)</span>
                    </label>
                  </div>
                </div>

                {/* Technician scheduler */}
                <div className="glass-panel" style={{ padding: '30px' }}>
                  <h3 style={{ color: 'var(--text-bright)', fontSize: '1.3rem', marginBottom: '20px' }}>Create Work Order</h3>
                  <form onSubmit={handleCreateWorkOrder}>
                    <div style={{ marginBottom: '15px' }}>
                      <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px' }}>Target Asset ID</label>
                      <select 
                        value={woAssetId} 
                        onChange={e => setWoAssetId(e.target.value)}
                        style={{ width: '100%', padding: '10px', borderRadius: '8px', background: '#FFFFFF', border: '1px solid var(--border-color)', color: 'var(--text-main)', outline: 'none' }}
                      >
                        {motors.map(m => (
                          <option key={m.motor_id} value={m.motor_id}>{m.motor_id} ({m.name})</option>
                        ))}
                      </select>
                    </div>

                    <div style={{ marginBottom: '15px' }}>
                      <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px' }}>Assigned Specialist</label>
                      <select 
                        value={woTech} 
                        onChange={e => setWoTech(e.target.value)}
                        style={{ width: '100%', padding: '10px', borderRadius: '8px', background: '#FFFFFF', border: '1px solid var(--border-color)', color: 'var(--text-main)', outline: 'none' }}
                      >
                        <option value="J. Sutherland">J. Sutherland</option>
                        <option value="M. Rossi">M. Rossi</option>
                        <option value="S. O'Brien">S. O'Brien</option>
                        <option value="H. Tanaka">H. Tanaka</option>
                      </select>
                    </div>

                    <div style={{ marginBottom: '20px' }}>
                      <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px' }}>Work Description</label>
                      <textarea 
                        value={woDesc}
                        onChange={e => setWoDesc(e.target.value)}
                        required
                        placeholder="e.g. Schedule inner bearing assembly inspection and re-lubrication."
                        style={{ width: '100%', padding: '10px', borderRadius: '8px', background: '#FFFFFF', border: '1px solid var(--border-color)', color: 'var(--text-main)', outline: 'none', minHeight: '80px', resize: 'vertical' }}
                      />
                    </div>

                    <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}>
                      Generate Work Order
                    </button>
                  </form>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ─── TAB 6: MAINTENANCE CRUD CONSOLE ─── */}
        {activeTab === 'history' && (
          <div>
            {!hasClearance(2) ? renderDenied() : (
              <div className="glass-panel" style={{ padding: '30px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '25px' }}>
                  <div>
                    <h2 style={{ color: 'var(--text-bright)', fontSize: '1.4rem' }}>Work Orders Log</h2>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>View, track and assign maintenance orders</p>
                  </div>
                  {/* Export PDF Button */}
                  <a href={`${API_BASE}/reports/weekly`} target="_blank" rel="noreferrer" className="btn btn-secondary">
                    <FileText size={16} /> Export Week Report
                  </a>
                </div>

                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        <th style={{ padding: '12px 8px' }}>Order ID</th>
                        <th style={{ padding: '12px 8px' }}>Asset ID</th>
                        <th style={{ padding: '12px 8px' }}>Asset Details</th>
                        <th style={{ padding: '12px 8px' }}>Action Description</th>
                        <th style={{ padding: '12px 8px' }}>Assigned Specialist</th>
                        <th style={{ padding: '12px 8px' }}>Date Issued</th>
                        <th style={{ padding: '12px 8px' }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {workOrders.map(wo => (
                        <tr key={wo.id} style={{ borderBottom: '1px solid var(--border-color)', fontSize: '0.9rem' }}>
                          <td style={{ padding: '16px 8px', fontWeight: 600, color: 'var(--text-bright)' }}>{wo.id}</td>
                          <td style={{ padding: '16px 8px' }}>{wo.asset_id}</td>
                          <td style={{ padding: '16px 8px' }}>{wo.asset_name}</td>
                          <td style={{ padding: '16px 8px' }}>{wo.description}</td>
                          <td style={{ padding: '16px 8px' }}>{wo.assigned_tech}</td>
                          <td style={{ padding: '16px 8px' }}>{new Date(wo.created_at).toLocaleDateString()}</td>
                          <td style={{ padding: '16px 8px' }}>
                            <span style={{ 
                              padding: '4px 8px', 
                              borderRadius: '4px', 
                              fontSize: '0.75rem', 
                              fontWeight: 600, 
                              background: wo.status === 'Completed' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
                              color: wo.status === 'Completed' ? 'var(--success)' : 'var(--warning)',
                              border: wo.status === 'Completed' ? '1px solid rgba(16,185,129,0.3)' : '1px solid rgba(245,158,11,0.3)'
                            }}>
                              {wo.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ─── TAB 7: FEEDBACK CENTER ─── */}
        {activeTab === 'feedback' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '30px' }}>
            {/* Feedback Form */}
            <div className="glass-panel" style={{ padding: '30px' }}>
              <h3 style={{ color: 'var(--text-bright)', fontSize: '1.3rem', marginBottom: '15px' }}>Technician Diagnostics Feedback</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '25px' }}>
                Your feedback helps align the Gradient Boosting Fault Classifier and the LSTM Autoencoder thresholds dynamically.
              </p>

              <form onSubmit={handleSubmitFeedback}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px' }}>Diagnostic ID</label>
                    <input 
                      type="number" 
                      value={feedbackPredId || ''} 
                      onChange={e => setFeedbackPredId(Number(e.target.value))}
                      required
                      style={{ width: '100%', padding: '10px', borderRadius: '8px', background: '#FFFFFF', border: '1px solid var(--border-color)', color: 'var(--text-main)', outline: 'none' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px' }}>Inspection Assessment</label>
                    <select 
                      value={feedbackType} 
                      onChange={e => setFeedbackType(e.target.value)}
                      style={{ width: '100%', padding: '10px', borderRadius: '8px', background: '#FFFFFF', border: '1px solid var(--border-color)', color: 'var(--text-main)', outline: 'none' }}
                    >
                      <option value="correct_fault">Confirmed Bearing Damage (Correct Prediction)</option>
                      <option value="false_alarm">Normal Bearing State (False Alarm)</option>
                      <option value="sensor_error">Sensor Exception / Telemetry Glitch</option>
                    </select>
                  </div>
                </div>

                <div style={{ marginBottom: '25px' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px' }}>Inspection Logs / Notes</label>
                  <textarea 
                    value={feedbackNotes}
                    onChange={e => setFeedbackNotes(e.target.value)}
                    placeholder="Provide specific details about visual bearing defects, lubrication quality, or sensor anomalies found."
                    style={{ width: '100%', padding: '10px', borderRadius: '8px', background: '#FFFFFF', border: '1px solid var(--border-color)', color: 'var(--text-main)', outline: 'none', minHeight: '100px', resize: 'vertical' }}
                  />
                </div>

                <button type="submit" className="btn btn-primary">
                  <Send size={16} /> Submit Feedback
                </button>
              </form>
            </div>

            {/* Model Accuracy Card */}
            <div className="glass-panel" style={{ padding: '30px' }}>
              <h3 style={{ color: 'var(--text-bright)', fontSize: '1.2rem', marginBottom: '20px' }}>Fleet Diagnostics Accuracy</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '25px' }}>
                Summary based on technician feedback loop.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ textAlign: 'center', padding: '15px', borderRadius: '8px', background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.15)' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Verified Accuracy Rate</span>
                  <h2 style={{ fontSize: '2.5rem', color: 'var(--success)', marginTop: '5px' }}>96.3%</h2>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '8px' }}>
                  <span>Confirmed Failures:</span>
                  <span style={{ fontWeight: 600, color: 'var(--text-bright)' }}>26</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '8px' }}>
                  <span>False Alarms:</span>
                  <span style={{ fontWeight: 600, color: 'var(--text-bright)' }}>1</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                  <span>Sensor Errors Logged:</span>
                  <span style={{ fontWeight: 600, color: 'var(--text-bright)' }}>2</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ─── TAB 8: NOTIFICATION CENTER ─── */}
        {activeTab === 'notifications' && (
          <div>
            {!hasClearance(4) ? renderDenied() : (
              <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '30px' }}>
                {/* Gateway config */}
                <div className="glass-panel" style={{ padding: '30px' }}>
                  <h3 style={{ color: 'var(--text-bright)', fontSize: '1.3rem', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <BellRing size={20} color="var(--primary)" /> Gateway Settings
                  </h3>

                  <form onSubmit={e => { e.preventDefault(); alert('Gateway settings updated.'); }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px', marginBottom: '15px' }}>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px' }}>SMTP Server</label>
                        <input 
                          type="text" 
                          value={notificationSettings.smtp_server}
                          onChange={e => setNotificationSettings({ ...notificationSettings, smtp_server: e.target.value })}
                          style={{ width: '100%', padding: '10px', borderRadius: '8px', background: '#FFFFFF', border: '1px solid var(--border-color)', color: 'var(--text-main)' }}
                        />
                      </div>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px' }}>SMTP Port</label>
                        <input 
                          type="number" 
                          value={notificationSettings.smtp_port}
                          onChange={e => setNotificationSettings({ ...notificationSettings, smtp_port: Number(e.target.value) })}
                          style={{ width: '100%', padding: '10px', borderRadius: '8px', background: '#FFFFFF', border: '1px solid var(--border-color)', color: 'var(--text-main)' }}
                        />
                      </div>
                    </div>

                    <div style={{ marginBottom: '15px' }}>
                      <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px' }}>Sender Email</label>
                      <input 
                        type="email" 
                        value={notificationSettings.sender_email}
                        onChange={e => setNotificationSettings({ ...notificationSettings, sender_email: e.target.value })}
                        style={{ width: '100%', padding: '10px', borderRadius: '8px', background: '#FFFFFF', border: '1px solid var(--border-color)', color: 'var(--text-main)' }}
                      />
                    </div>

                    <div style={{ marginBottom: '15px' }}>
                      <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px' }}>Recipient WhatsApp (Twilio Target)</label>
                      <input 
                        type="text" 
                        value={notificationSettings.recipient_whatsapp}
                        onChange={e => setNotificationSettings({ ...notificationSettings, recipient_whatsapp: e.target.value })}
                        style={{ width: '100%', padding: '10px', borderRadius: '8px', background: '#FFFFFF', border: '1px solid var(--border-color)', color: 'var(--text-main)' }}
                      />
                    </div>

                    <button type="submit" className="btn btn-primary" style={{ marginTop: '10px' }}>
                      Update Gateway Credentials
                    </button>
                  </form>
                </div>

                {/* Subscriber List Panel */}
                <div className="glass-panel" style={{ padding: '30px' }}>
                  <h3 style={{ color: 'var(--text-bright)', fontSize: '1.2rem', marginBottom: '20px' }}>Subscribe Contact List</h3>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <div style={{ padding: '12px', borderRadius: '8px', background: 'var(--bg-card-hover)', border: '1px solid var(--border-color)' }}>
                      <p style={{ fontWeight: 600, color: 'var(--text-bright)', fontSize: '0.9rem' }}>Justin Bieber (Super Admin)</p>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>rasyaadputraredianto@gmail.com</span>
                    </div>
                    <div style={{ padding: '12px', borderRadius: '8px', background: 'var(--bg-card-hover)', border: '1px solid var(--border-color)' }}>
                      <p style={{ fontWeight: 600, color: 'var(--text-bright)', fontSize: '0.9rem' }}>Ronny Prasad (Maintenance)</p>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>maint@ASTRA.com</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

      </div>

      {/* ─── PROFILE UPDATE EDIT DIALOG ─── */}
      {showProfileEdit && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '20px' }}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: '460px', padding: '30px' }}>
            <h3 style={{ color: 'var(--text-bright)', fontSize: '1.3rem', marginBottom: '20px' }}>Modify Profile Settings</h3>
            
            <form onSubmit={handleUpdateProfile}>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px' }}>Full Name</label>
                <input 
                  type="text" 
                  value={profileName} 
                  onChange={e => setProfileName(e.target.value)} 
                  required
                  style={{ width: '100%', padding: '10px', borderRadius: '8px', background: '#FFFFFF', border: '1px solid var(--border-color)', color: 'var(--text-main)' }}
                />
              </div>

              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px' }}>Professional Title</label>
                <input 
                  type="text" 
                  value={profileTitle} 
                  onChange={e => setProfileTitle(e.target.value)} 
                  required
                  style={{ width: '100%', padding: '10px', borderRadius: '8px', background: '#FFFFFF', border: '1px solid var(--border-color)', color: 'var(--text-main)' }}
                />
              </div>

              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px' }}>Email Address</label>
                <input 
                  type="email" 
                  value={profileEmail} 
                  onChange={e => setProfileEmail(e.target.value)} 
                  required
                  style={{ width: '100%', padding: '10px', borderRadius: '8px', background: '#FFFFFF', border: '1px solid var(--border-color)', color: 'var(--text-main)' }}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '6px' }}>Avatar URL</label>
                <input 
                  type="text" 
                  value={profileAvatar} 
                  onChange={e => setProfileAvatar(e.target.value)} 
                  style={{ width: '100%', padding: '10px', borderRadius: '8px', background: '#FFFFFF', border: '1px solid var(--border-color)', color: 'var(--text-main)' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowProfileEdit(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save Settings</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
