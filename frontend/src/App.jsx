import React, { useState, useEffect } from 'react';
import { 
  Building2, Calendar, Clock, Shield, CheckCircle2, AlertCircle, 
  User, DollarSign, LogOut, Key, Sparkles, BarChart3, Search, 
  Printer, ArrowRight, X, ChevronRight, Bed, Eye, Wind, Coffee, 
  Check, RefreshCw, FileText, Lock, Users, Layers
} from 'lucide-react';

const ROLES = {
  ADMIN: { label: 'Hotel Administrator', email: 'admin@grandview.com', role: 'ADMIN', badge: '👑 Admin' },
  STAFF: { label: 'Front Desk Reception', email: 'staff@grandview.com', role: 'STAFF', badge: '🛎️ Front Desk' },
  GUEST_DAVID: { label: 'David Miller (Guest)', email: 'guest@example.com', role: 'GUEST', badge: '👤 Guest (David)' },
  GUEST_SARAH: { label: 'Sarah Jenkins (Guest)', email: 'sarah@example.com', role: 'GUEST', badge: '👤 Guest (Sarah)' }
};

export default function App() {
  const [currentRoleKey, setCurrentRoleKey] = useState('ADMIN');
  const [activeTab, setActiveTab] = useState('booking'); // booking, my-stays, front-desk, housekeeping, analytics, rates, audit
  const [toast, setToast] = useState(null);

  // Availability Search State
  const todayStr = new Date().toISOString().split('T')[0];
  const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1);
  const dayAfter = new Date(); dayAfter.setDate(dayAfter.getDate() + 3);
  
  const [searchParams, setSearchParams] = useState({
    check_in: tomorrow.toISOString().split('T')[0],
    check_out: dayAfter.toISOString().split('T')[0],
    guests: '2'
  });
  const [availableRooms, setAvailableRooms] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState('');

  // Active Hold & Checkout State
  const [activeHold, setActiveHold] = useState(null);
  const [holdSecondsLeft, setHoldSecondsLeft] = useState(0);
  const [checkoutModalOpen, setCheckoutModalOpen] = useState(false);
  const [addons, setAddons] = useState({ breakfast: false, shuttle: false });
  const [isConfirming, setIsConfirming] = useState(false);

  // Confirmation Voucher State
  const [confirmedReservation, setConfirmedReservation] = useState(null);
  const [voucherModalOpen, setVoucherModalOpen] = useState(false);

  // Operations Data State
  const [reservations, setReservations] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [roomTypes, setRoomTypes] = useState([]);

  // Toast Helper
  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const currentUser = ROLES[currentRoleKey];

  // Load initial data
  useEffect(() => {
    fetchRoomTypes();
    fetchInventory();
    fetchReservations();
    fetchAnalytics();
    fetchAuditLogs();
    handleSearch();
  }, [currentRoleKey]);

  // Hold Countdown Timer Effect
  useEffect(() => {
    if (!activeHold || holdSecondsLeft <= 0) return;
    const interval = setInterval(() => {
      setHoldSecondsLeft((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          setActiveHold(null);
          setCheckoutModalOpen(false);
          showToast('Hold expired. The room has been restored to inventory.', 'error');
          handleSearch();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [activeHold, holdSecondsLeft]);

  // --- API Functions ---
  const fetchRoomTypes = async () => {
    try {
      const res = await fetch('/api/v1/rooms/');
      const data = await res.json();
      if (data.success) setRoomTypes(data.room_types);
    } catch (e) { console.error(e); }
  };

  const handleSearch = async () => {
    setIsSearching(true);
    setSearchError('');
    try {
      const res = await fetch(`/api/v1/availability/?check_in=${searchParams.check_in}&check_out=${searchParams.check_out}&guests=${searchParams.guests}`);
      const data = await res.json();
      if (!res.ok || !data.success) {
        setSearchError(data.error || 'Invalid date range');
        setAvailableRooms([]);
      } else {
        setAvailableRooms(data.rooms);
      }
    } catch (e) {
      setSearchError('Network error checking availability');
    } finally {
      setIsSearching(false);
    }
  };

  const handleCreateHold = async (room) => {
    try {
      const res = await fetch('/api/v1/holds/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room_id: room.room_id,
          check_in: searchParams.check_in,
          check_out: searchParams.check_out,
          guests: parseInt(searchParams.guests)
        })
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        showToast(data.error || 'Failed to place hold on room', 'error');
        handleSearch();
      } else {
        setActiveHold({ ...data, roomDetails: room });
        setHoldSecondsLeft(data.remaining_seconds || 900);
        setCheckoutModalOpen(true);
        showToast(`Room ${data.room_number} held for 15 minutes!`, 'success');
      }
    } catch (e) {
      showToast('Error placing hold', 'error');
    }
  };

  const handleConfirmBooking = async (e) => {
    e.preventDefault();
    if (!activeHold) return;
    setIsConfirming(true);

    try {
      const res = await fetch('/api/v1/bookings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          hold_id: activeHold.hold_id,
          guest_name: currentUser.label,
          guest_email: currentUser.email,
          guest_phone: '+1 (555) 019-8822',
          payment_method: 'CARD_SANDBOX',
          has_breakfast: addons.breakfast,
          has_shuttle: addons.shuttle
        })
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        showToast(data.error || 'Booking confirmation failed', 'error');
      } else {
        setConfirmedReservation(data);
        setActiveHold(null);
        setCheckoutModalOpen(false);
        setVoucherModalOpen(true);
        showToast(`Reservation guaranteed! Reference: ${data.booking_reference}`, 'success');
        fetchReservations();
        fetchAnalytics();
        fetchInventory();
        fetchAuditLogs();
        handleSearch();
      }
    } catch (e) {
      showToast('Error confirming payment', 'error');
    } finally {
      setIsConfirming(false);
    }
  };

  const fetchReservations = async () => {
    try {
      const res = await fetch('/api/v1/reservations/');
      const data = await res.json();
      if (data.success) setReservations(data.reservations);
    } catch (e) { console.error(e); }
  };

  const fetchInventory = async () => {
    try {
      const res = await fetch('/api/v1/inventory/');
      const data = await res.json();
      if (data.success) setInventory(data.rooms);
    } catch (e) { console.error(e); }
  };

  const fetchAnalytics = async () => {
    try {
      const res = await fetch('/api/v1/reports/operations/?start_date=' + todayStr);
      const data = await res.json();
      if (data.success) setAnalytics(data);
    } catch (e) { console.error(e); }
  };

  const fetchAuditLogs = async () => {
    try {
      const res = await fetch('/api/v1/audit/');
      const data = await res.json();
      if (data.success) setAuditLogs(data.logs);
    } catch (e) { console.error(e); }
  };

  const handleCheckIn = async (ref) => {
    try {
      const res = await fetch(`/api/v1/bookings/${ref}/check-in/`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        showToast(`Guest checked in! Room marked OCCUPIED.`, 'success');
        fetchReservations();
        fetchInventory();
        fetchAnalytics();
        fetchAuditLogs();
      } else {
        showToast(data.error || 'Check-in failed', 'error');
      }
    } catch (e) { showToast('Check-in error', 'error'); }
  };

  const handleCheckOut = async (ref) => {
    try {
      const res = await fetch(`/api/v1/bookings/${ref}/check-out/`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        showToast(`Guest checked out! Room marked DIRTY (housekeeping scheduled).`, 'success');
        fetchReservations();
        fetchInventory();
        fetchAnalytics();
        fetchAuditLogs();
      } else {
        showToast(data.error || 'Check-out failed', 'error');
      }
    } catch (e) { showToast('Check-out error', 'error'); }
  };

  const handleCancelBooking = async (ref) => {
    if (!window.confirm(`Are you sure you want to cancel reservation ${ref}? Full refund will be logged.`)) return;
    try {
      const res = await fetch(`/api/v1/bookings/${ref}/cancel/`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        showToast(`Reservation ${ref} cancelled and room restored to inventory.`, 'success');
        fetchReservations();
        fetchInventory();
        fetchAnalytics();
        fetchAuditLogs();
        handleSearch();
      } else {
        showToast(data.error || 'Cancellation failed', 'error');
      }
    } catch (e) { showToast('Cancellation error', 'error'); }
  };

  const handleUpdateRoomStatus = async (roomId, newStatus) => {
    try {
      const res = await fetch(`/api/v1/rooms/${roomId}/status/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus, notes: 'Updated via React Operations Board' })
      });
      const data = await res.json();
      if (data.success) {
        showToast(`Room status updated to ${newStatus}`, 'success');
        fetchInventory();
        fetchAnalytics();
        fetchAuditLogs();
      }
    } catch (e) { showToast('Update error', 'error'); }
  };

  // Format MM:SS for countdown timer
  const formatTimer = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      
      {/* 1. Reviewer 1-Click Role Switcher Bar */}
      <div className="bg-gradient-to-r from-amber-950 via-slate-900 to-amber-950 border-b border-amber-500/30 px-4 py-2 text-xs">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-2 text-amber-300 font-semibold font-mono">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping"></span>
            <span>REVIEWER DEMO SWITCHER:</span>
            <span className="text-slate-400 font-sans hidden sm:inline">1-Click instant role transition</span>
          </div>
          <div className="flex items-center flex-wrap gap-2">
            {Object.entries(ROLES).map(([key, info]) => (
              <button
                key={key}
                onClick={() => {
                  setCurrentRoleKey(key);
                  showToast(`Switched active persona to ${info.label}`, 'info');
                  if (info.role === 'ADMIN') setActiveTab('analytics');
                  else if (info.role === 'STAFF') setActiveTab('front-desk');
                  else setActiveTab('booking');
                }}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition border ${
                  currentRoleKey === key 
                    ? 'bg-amber-500 text-slate-950 border-amber-400 shadow-md shadow-amber-500/20' 
                    : 'bg-slate-900/80 text-slate-300 border-slate-700 hover:border-slate-500 hover:text-white'
                }`}
              >
                {info.badge}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 2. Main Luxury Header */}
      <header className="glass-card sticky top-0 z-40 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            
            {/* Logo */}
            <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('booking')}>
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center text-slate-950 font-serif font-bold text-xl shadow-lg shadow-amber-500/20">
                G
              </div>
              <div>
                <span className="text-lg font-serif font-bold tracking-wide text-white">GrandView</span>
                <span className="block text-[10px] uppercase tracking-widest text-amber-400 font-mono -mt-1">
                  Luxury Resort & React PMS
                </span>
              </div>
            </div>

            {/* Navigation Tabs */}
            <nav className="hidden md:flex items-center space-x-1 text-xs font-medium">
              <button
                onClick={() => setActiveTab('booking')}
                className={`px-3 py-2 rounded-lg transition ${activeTab === 'booking' ? 'bg-slate-800 text-white font-bold' : 'text-slate-400 hover:text-white'}`}
              >
                Suites & Booking
              </button>

              <button
                onClick={() => setActiveTab('my-stays')}
                className={`px-3 py-2 rounded-lg transition ${activeTab === 'my-stays' ? 'bg-slate-800 text-white font-bold' : 'text-slate-400 hover:text-white'}`}
              >
                My Stays
              </button>

              {(currentUser.role === 'STAFF' || currentUser.role === 'ADMIN') && (
                <>
                  <span className="h-4 w-px bg-slate-800 mx-1"></span>
                  <button
                    onClick={() => setActiveTab('front-desk')}
                    className={`px-3 py-2 rounded-lg transition flex items-center space-x-1 ${activeTab === 'front-desk' ? 'bg-blue-950/80 text-blue-300 font-bold border border-blue-500/40' : 'text-slate-400 hover:text-white'}`}
                  >
                    <span>🛎️ Front Desk</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('housekeeping')}
                    className={`px-3 py-2 rounded-lg transition flex items-center space-x-1 ${activeTab === 'housekeeping' ? 'bg-amber-950/80 text-amber-300 font-bold border border-amber-500/40' : 'text-slate-400 hover:text-white'}`}
                  >
                    <span>✨ Housekeeping</span>
                  </button>
                </>
              )}

              {currentUser.role === 'ADMIN' && (
                <>
                  <span className="h-4 w-px bg-slate-800 mx-1"></span>
                  <button
                    onClick={() => setActiveTab('analytics')}
                    className={`px-3 py-2 rounded-lg transition flex items-center space-x-1 ${activeTab === 'analytics' ? 'bg-emerald-950/80 text-emerald-300 font-bold border border-emerald-500/40' : 'text-slate-400 hover:text-white'}`}
                  >
                    <span>📊 Analytics</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('rates')}
                    className={`px-3 py-2 rounded-lg transition ${activeTab === 'rates' ? 'bg-slate-800 text-white font-bold' : 'text-slate-400 hover:text-white'}`}
                  >
                    Rates CRUD
                  </button>
                  <button
                    onClick={() => setActiveTab('audit')}
                    className={`px-3 py-2 rounded-lg transition ${activeTab === 'audit' ? 'bg-slate-800 text-white font-bold' : 'text-slate-400 hover:text-white'}`}
                  >
                    Audit Trail
                  </button>
                </>
              )}
            </nav>

            {/* Persona Indicator */}
            <div className="flex items-center space-x-3">
              <div className="text-right hidden sm:block">
                <span className="block text-xs text-white font-medium">{currentUser.label}</span>
                <span className="text-[10px] font-mono text-amber-400">{currentUser.email}</span>
              </div>
              <a 
                href="/api/docs/" 
                target="_blank" 
                rel="noreferrer" 
                className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-300 hover:text-white text-xs font-mono transition"
              >
                Swagger API
              </a>
            </div>

          </div>
        </div>
      </header>

      {/* Toast Alert */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 animate-bounce">
          <div className={`px-4 py-3 rounded-xl border shadow-2xl flex items-center space-x-3 text-xs font-medium ${
            toast.type === 'error' ? 'bg-rose-950 border-rose-700 text-rose-200' :
            toast.type === 'info' ? 'bg-blue-950 border-blue-700 text-blue-200' :
            'bg-emerald-950 border-emerald-700 text-emerald-200'
          }`}>
            {toast.type === 'error' ? <AlertCircle className="w-4 h-4 text-rose-400" /> : <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
            <span>{toast.message}</span>
            <button onClick={() => setToast(null)} className="ml-2 text-slate-400 hover:text-white">&times;</button>
          </div>
        </div>
      )}

      {/* Main Content Router */}
      <main className="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* ========================================================================= */}
        {/* VIEW 1: SUITES & AVAILABILITY SEARCH (GUEST WORKFLOW) */}
        {/* ========================================================================= */}
        {activeTab === 'booking' && (
          <div className="space-y-8">
            {/* Hero Banner with Search Engine */}
            <div className="relative rounded-3xl overflow-hidden border border-slate-800 bg-slate-900 p-8 sm:p-12 text-center shadow-2xl">
              <div className="absolute inset-0 opacity-20 bg-cover bg-center" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=1800&q=80')" }}></div>
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/70 to-transparent"></div>
              
              <div className="relative z-10 max-w-3xl mx-auto">
                <span className="inline-block px-3 py-1 rounded-full text-[10px] font-mono uppercase tracking-widest bg-amber-500/10 text-amber-400 border border-amber-500/30 mb-3">
                  ★ Handcrafted Oceanfront Sanctuaries &bull; Palm Haven
                </span>
                <h1 className="text-3xl sm:text-5xl font-serif font-bold text-white tracking-tight">
                  Instant Reservations with <span className="text-amber-400">15-Min Guaranteed Holds</span>
                </h1>
                <p className="mt-3 text-xs sm:text-sm text-slate-300 max-w-xl mx-auto leading-relaxed">
                  Real-time inventory locks prevent double-booking race conditions while you review transparent itemized pricing.
                </p>

                {/* Search Bar Widget */}
                <div className="mt-8 bg-slate-950/90 backdrop-blur-md p-4 rounded-2xl border border-slate-700 shadow-2xl text-left">
                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                    <div>
                      <label className="block text-[11px] font-mono uppercase text-slate-400 mb-1">Check-In</label>
                      <input 
                        type="date" 
                        min={todayStr}
                        value={searchParams.check_in}
                        onChange={(e) => setSearchParams({ ...searchParams, check_in: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-mono uppercase text-slate-400 mb-1">Check-Out</label>
                      <input 
                        type="date" 
                        min={todayStr}
                        value={searchParams.check_out}
                        onChange={(e) => setSearchParams({ ...searchParams, check_out: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-mono uppercase text-slate-400 mb-1">Guests</label>
                      <select 
                        value={searchParams.guests}
                        onChange={(e) => setSearchParams({ ...searchParams, guests: e.target.value })}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
                      >
                        <option value="1">1 Guest</option>
                        <option value="2">2 Guests</option>
                        <option value="3">3 Guests</option>
                        <option value="4">4 Guests</option>
                      </select>
                    </div>
                    <div className="flex items-end">
                      <button 
                        onClick={handleSearch}
                        disabled={isSearching}
                        className="w-full bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold py-2.5 px-4 rounded-lg text-xs uppercase tracking-wider transition flex items-center justify-center space-x-1.5 shadow"
                      >
                        {isSearching ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                        <span>Check Availability</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Error Message */}
            {searchError && (
              <div className="p-4 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-200 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 text-rose-400" />
                <span>{searchError}</span>
              </div>
            )}

            {/* Search Results Grid */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-serif font-bold text-white">Available Accommodations</h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Stay: <span className="text-amber-400 font-mono">{searchParams.check_in}</span> to <span className="text-amber-400 font-mono">{searchParams.check_out}</span> &bull; {searchParams.guests} Guests
                </p>
              </div>
              <span className="px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300">
                {availableRooms.length} Physical Rooms Ready
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {availableRooms.map((r) => (
                <div key={r.room_id} className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden hover:border-slate-700 transition flex flex-col justify-between group shadow-xl">
                  <div>
                    <div className="relative h-48 overflow-hidden">
                      <img src={r.room_type.image_url} alt={r.room_type.name} className="w-full h-full object-cover group-hover:scale-105 transition duration-500" />
                      <div className="absolute top-3 left-3 bg-slate-950/80 backdrop-blur-md px-2.5 py-1 rounded text-xs font-mono font-bold text-amber-400 border border-slate-700">
                        Room #{r.room_number} (Fl. {r.floor})
                      </div>
                      <div className="absolute bottom-3 right-3 bg-emerald-950/90 border border-emerald-700 text-emerald-300 px-2 py-0.5 rounded text-[10px] font-mono">
                        Available & Clean
                      </div>
                    </div>

                    <div className="p-5">
                      <h3 className="font-serif font-bold text-lg text-white group-hover:text-amber-400 transition">{r.room_type.name}</h3>
                      <p className="text-xs text-slate-400 font-mono mt-1">{r.room_type.bed_type} &bull; Max {r.room_type.max_guests} Guests</p>

                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {r.room_type.amenities?.map((amenity, i) => (
                          <span key={i} className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-[10px] text-slate-300 font-mono">
                            {amenity}
                          </span>
                        ))}
                      </div>

                      <div className="mt-4 p-3 rounded-xl bg-slate-950 border border-slate-800/80 text-xs font-mono space-y-1">
                        <div className="flex justify-between text-slate-400">
                          <span>{r.pricing.num_nights} nights x ${r.pricing.nightly_rate}:</span>
                          <span className="text-slate-200">${r.pricing.room_subtotal}</span>
                        </div>
                        <div className="flex justify-between text-slate-500 text-[11px]">
                          <span>Taxes & Fees:</span>
                          <span>${(parseFloat(r.pricing.tax_amount) + parseFloat(r.pricing.service_fee)).toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between text-white font-bold pt-1 border-t border-slate-800">
                          <span>Total Stay:</span>
                          <span className="text-amber-400 text-sm">${r.pricing.total_amount}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="p-5 pt-0">
                    <button
                      onClick={() => handleCreateHold(r)}
                      className="w-full py-2.5 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold text-xs uppercase tracking-wider rounded-xl transition shadow-lg shadow-amber-500/20 flex items-center justify-center space-x-1.5"
                    >
                      <Lock className="w-3.5 h-3.5" />
                      <span>Lock & Hold Room (15 Min)</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {availableRooms.length === 0 && !isSearching && (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center max-w-lg mx-auto">
                <Calendar className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <h3 className="text-base font-serif font-bold text-white">Full Occupancy / No Rooms Available</h3>
                <p className="text-xs text-slate-400 mt-1">
                  All rooms are reserved or currently under active temporary holds for the requested dates. Please choose alternative dates.
                </p>
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW 2: GUEST STAYS PORTAL */}
        {/* ========================================================================= */}
        {activeTab === 'my-stays' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-mono uppercase tracking-widest text-amber-400">Guest Stays</span>
                <h1 className="text-2xl font-serif font-bold text-white mt-1">My Reservations</h1>
                <p className="text-xs text-slate-400 mt-0.5">Showing reservations on record for <strong className="text-white">{currentUser.email}</strong></p>
              </div>
              <button onClick={() => setActiveTab('booking')} className="px-3.5 py-2 bg-amber-500 text-slate-950 font-bold text-xs rounded-lg shadow transition">
                + Book Another Sanctuary
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {reservations.filter(r => r.guest_email.toLowerCase() === currentUser.email.toLowerCase()).map(r => (
                <div key={r.id} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <span className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                        r.status === 'CONFIRMED' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                        r.status === 'CHECKED_IN' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                        r.status === 'CHECKED_OUT' ? 'bg-slate-800 text-slate-300' :
                        'bg-rose-950 text-rose-300 border border-rose-800'
                      }`}>
                        {r.status}
                      </span>
                      <span className="text-xs font-mono text-slate-400">{r.booking_reference}</span>
                    </div>

                    <h3 className="text-lg font-serif font-bold text-white">{r.room_type}</h3>
                    <p className="text-xs text-amber-400 font-mono mt-0.5">Room #{r.room_number} (Floor {r.floor})</p>

                    <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80 my-4 text-xs font-mono space-y-1">
                      <div className="flex justify-between text-slate-400">
                        <span>Check-In:</span>
                        <span className="text-white">{r.check_in} (14:00)</span>
                      </div>
                      <div className="flex justify-between text-slate-400">
                        <span>Check-Out:</span>
                        <span className="text-white">{r.check_out} (11:00)</span>
                      </div>
                      <div className="flex justify-between text-slate-400 pt-1 border-t border-slate-800">
                        <span>Total Stay:</span>
                        <span className="text-amber-400 font-bold">${r.total_amount}</span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                    <button
                      onClick={() => { setConfirmedReservation(r); setVoucherModalOpen(true); }}
                      className="text-xs text-amber-400 hover:underline font-semibold"
                    >
                      View Official Voucher &rarr;
                    </button>

                    {r.can_cancel && (
                      <button
                        onClick={() => handleCancelBooking(r.booking_reference)}
                        className="px-3 py-1 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-lg text-xs font-semibold transition"
                      >
                        Cancel Stay
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {reservations.filter(r => r.guest_email.toLowerCase() === currentUser.email.toLowerCase()).length === 0 && (
              <div className="bg-slate-900 border border-slate-800 p-8 rounded-xl text-center text-slate-400 text-xs">
                No active bookings recorded for {currentUser.email}. Select "Suites & Booking" above to reserve a stay!
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW 3: FRONT DESK RECEPTION TERMINAL (STAFF / ADMIN) */}
        {/* ========================================================================= */}
        {activeTab === 'front-desk' && (
          <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <span className="text-xs font-mono uppercase tracking-widest text-blue-400">Reception Desk</span>
                <h1 className="text-2xl font-serif font-bold text-white mt-1">Arrivals & Departures Console</h1>
                <p className="text-xs text-slate-400 mt-0.5">Manage live key handovers, execute check-in & check-out state transitions, and inspect guests.</p>
              </div>

              <div className="flex items-center space-x-2">
                <button onClick={() => setActiveTab('housekeeping')} className="px-3 py-2 bg-slate-900 border border-slate-700 text-slate-300 hover:text-white rounded-lg text-xs font-semibold transition">
                  ✨ Housekeeping Board
                </button>
              </div>
            </div>

            {/* Quick Metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                <div className="text-slate-400">Scheduled Check-Ins</div>
                <div className="text-2xl font-bold text-amber-400 mt-1">
                  {reservations.filter(r => r.status === 'CONFIRMED').length}
                </div>
              </div>
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                <div className="text-slate-400">Currently In-House</div>
                <div className="text-2xl font-bold text-emerald-400 mt-1">
                  {reservations.filter(r => r.status === 'CHECKED_IN').length}
                </div>
              </div>
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                <div className="text-slate-400">Completed Departures</div>
                <div className="text-2xl font-bold text-slate-300 mt-1">
                  {reservations.filter(r => r.status === 'CHECKED_OUT').length}
                </div>
              </div>
            </div>

            {/* Table */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 text-slate-400 uppercase font-mono border-b border-slate-800">
                  <tr>
                    <th className="p-4">Reference</th>
                    <th className="p-4">Guest</th>
                    <th className="p-4">Room</th>
                    <th className="p-4">Stay Dates</th>
                    <th className="p-4">Status</th>
                    <th className="p-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 font-mono">
                  {reservations.map(r => (
                    <tr key={r.id} className="hover:bg-slate-800/40 transition">
                      <td className="p-4 font-bold text-white">{r.booking_reference}</td>
                      <td className="p-4">
                        <div className="font-semibold text-white">{r.guest_name}</div>
                        <div className="text-[11px] text-slate-400">{r.guest_email}</div>
                      </td>
                      <td className="p-4 text-amber-400 font-bold">Room #{r.room_number}</td>
                      <td className="p-4 text-slate-300">{r.check_in} &rarr; {r.check_out} ({r.num_nights}n)</td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          r.status === 'CONFIRMED' ? 'bg-amber-500/20 text-amber-400' :
                          r.status === 'CHECKED_IN' ? 'bg-emerald-500/20 text-emerald-400' :
                          r.status === 'CHECKED_OUT' ? 'bg-slate-800 text-slate-300' : 'bg-rose-950 text-rose-300'
                        }`}>
                          {r.status}
                        </span>
                      </td>
                      <td className="p-4 text-right space-x-2">
                        {r.can_check_in && (
                          <button
                            onClick={() => handleCheckIn(r.booking_reference)}
                            className="px-3 py-1 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-lg text-xs shadow transition"
                          >
                            Check In &rarr;
                          </button>
                        )}
                        {r.can_check_out && (
                          <button
                            onClick={() => handleCheckOut(r.booking_reference)}
                            className="px-3 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-lg text-xs shadow transition"
                          >
                            Check Out &rarr;
                          </button>
                        )}
                        <button
                          onClick={() => { setConfirmedReservation(r); setVoucherModalOpen(true); }}
                          className="px-2.5 py-1 bg-slate-800 text-slate-300 hover:text-white rounded-lg text-xs"
                        >
                          Voucher
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW 4: HOUSEKEEPING BOARD */}
        {/* ========================================================================= */}
        {activeTab === 'housekeeping' && (
          <div className="space-y-6">
            <div>
              <span className="text-xs font-mono uppercase tracking-widest text-amber-400">Sanitation & Turnover</span>
              <h1 className="text-2xl font-serif font-bold text-white mt-1">Housekeeping Floor Status Board</h1>
              <p className="text-xs text-slate-400 mt-0.5">Real-time room sanitization states with 1-click turnover actions.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {inventory.map(room => (
                <div key={room.id} className={`p-4 rounded-2xl border transition ${
                  room.status === 'AVAILABLE' ? 'bg-slate-950 border-emerald-500/40' :
                  room.status === 'OCCUPIED' ? 'bg-slate-950 border-blue-500/40' :
                  room.status === 'DIRTY' ? 'bg-amber-950/20 border-amber-500/60' :
                  'bg-rose-950/20 border-rose-500/40'
                }`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-xl font-mono font-bold text-white">#{room.room_number}</span>
                      <span className="block text-[11px] text-slate-400">Floor {room.floor} &bull; {room.room_type.name}</span>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                      room.status === 'AVAILABLE' ? 'bg-emerald-500/20 text-emerald-400' :
                      room.status === 'OCCUPIED' ? 'bg-blue-500/20 text-blue-400' :
                      room.status === 'DIRTY' ? 'bg-amber-500/20 text-amber-400 animate-pulse' :
                      'bg-rose-500/20 text-rose-400'
                    }`}>
                      {room.status}
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-400 font-mono mt-2 min-h-[32px]">
                    {room.housekeeping_notes || 'Inspected and sealed.'}
                  </p>

                  <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between gap-1">
                    {room.status !== 'AVAILABLE' && (
                      <button
                        onClick={() => handleUpdateRoomStatus(room.id, 'AVAILABLE')}
                        className="w-full py-1.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-[11px] rounded-lg transition"
                      >
                        ✓ Mark Clean & Ready
                      </button>
                    )}
                    {room.status === 'AVAILABLE' && (
                      <>
                        <button
                          onClick={() => handleUpdateRoomStatus(room.id, 'DIRTY')}
                          className="w-1/2 py-1 bg-slate-800 text-amber-400 text-[10px] rounded transition"
                        >
                          Set Dirty
                        </button>
                        <button
                          onClick={() => handleUpdateRoomStatus(room.id, 'MAINTENANCE')}
                          className="w-1/2 py-1 bg-slate-800 text-rose-400 text-[10px] rounded transition"
                        >
                          Maintenance
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW 5: EXECUTIVE ANALYTICS DASHBOARD (ADMIN) */}
        {/* ========================================================================= */}
        {activeTab === 'analytics' && analytics && (
          <div className="space-y-6">
            <div>
              <span className="text-xs font-mono uppercase tracking-widest text-emerald-400">Executive Analytics</span>
              <h1 className="text-2xl font-serif font-bold text-white mt-1">Operational & Financial Intelligence</h1>
              <p className="text-xs text-slate-400 mt-0.5">Real-time occupancy rate, gross revenue, ADR, and RevPAR aggregated from reservation ledgers.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
                <span className="text-xs font-mono uppercase text-slate-400">Gross Room Revenue</span>
                <div className="text-3xl font-serif font-bold text-emerald-400 mt-1">${analytics.total_revenue}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Calculated over {analytics.num_days} days</div>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
                <span className="text-xs font-mono uppercase text-slate-400">Occupancy Rate</span>
                <div className="text-3xl font-serif font-bold text-blue-400 mt-1">{analytics.occupancy_rate_pct}%</div>
                <div className="text-[11px] text-slate-400 mt-0.5">{analytics.total_occupied_nights} / {analytics.total_available_nights} room nights sold</div>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
                <span className="text-xs font-mono uppercase text-slate-400">Average Daily Rate (ADR)</span>
                <div className="text-3xl font-serif font-bold text-amber-400 mt-1">${analytics.adr}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Revenue per occupied room night</div>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
                <span className="text-xs font-mono uppercase text-slate-400">RevPAR</span>
                <div className="text-3xl font-serif font-bold text-purple-400 mt-1">${analytics.revpar}</div>
                <div className="text-[11px] text-slate-400 mt-0.5">Revenue per available inventory night</div>
              </div>
            </div>

            {/* Daily Breakdown Table */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
              <div className="p-4 bg-slate-950 border-b border-slate-800 flex justify-between items-center">
                <h3 className="text-sm font-serif font-bold text-white">Daily Stay Performance Table</h3>
                <span className="text-xs text-slate-400 font-mono">Total Physical Rooms: {analytics.total_rooms}</span>
              </div>
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-950 text-slate-400 uppercase border-b border-slate-800">
                  <tr>
                    <th className="p-3.5">Date</th>
                    <th className="p-3.5">Occupied</th>
                    <th className="p-3.5">Available</th>
                    <th className="p-3.5">Occupancy %</th>
                    <th className="p-3.5 text-right">Daily Revenue</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {analytics.daily_breakdown?.map((d, i) => (
                    <tr key={i} className="hover:bg-slate-800/40">
                      <td className="p-3.5 text-white font-bold">{d.date_str} ({d.day_name})</td>
                      <td className="p-3.5 text-blue-400">{d.occupied_rooms} rooms</td>
                      <td className="p-3.5 text-emerald-400">{d.available_rooms} rooms</td>
                      <td className="p-3.5 text-amber-400">{d.occupancy_pct}%</td>
                      <td className="p-3.5 text-right text-white font-bold">${d.revenue}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW 6: ROOM & RATE ADMINISTRATION (ADMIN) */}
        {/* ========================================================================= */}
        {activeTab === 'rates' && (
          <div className="space-y-6">
            <div>
              <span className="text-xs font-mono uppercase tracking-widest text-amber-400">Inventory Administration</span>
              <h1 className="text-2xl font-serif font-bold text-white mt-1">Room Types & Rate Rules</h1>
              <p className="text-xs text-slate-400 mt-0.5">Configure nightly base weekday rates, weekend multipliers, and suite specifications.</p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-950 text-slate-400 uppercase border-b border-slate-800">
                  <tr>
                    <th className="p-4">Suite Category</th>
                    <th className="p-4">Capacity</th>
                    <th className="p-4">Base Weekday Rate</th>
                    <th className="p-4">Weekend Rate</th>
                    <th className="p-4">Active Rooms</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {roomTypes.map(rt => (
                    <tr key={rt.id} className="hover:bg-slate-800/40">
                      <td className="p-4 font-serif font-bold text-white text-sm">{rt.name}</td>
                      <td className="p-4 text-slate-300">{rt.bed_type} &bull; Max {rt.max_guests} Guests</td>
                      <td className="p-4 text-amber-400 font-bold">${rt.base_price}/night</td>
                      <td className="p-4 text-amber-300 font-bold">${rt.weekend_price}/night</td>
                      <td className="p-4 text-emerald-400 font-bold">{rt.total_rooms} Rooms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* VIEW 7: SYSTEM AUDIT TRAIL */}
        {/* ========================================================================= */}
        {activeTab === 'audit' && (
          <div className="space-y-6">
            <div>
              <span className="text-xs font-mono uppercase tracking-widest text-amber-400">Security & Integrity</span>
              <h1 className="text-2xl font-serif font-bold text-white mt-1">Material Actions Audit Trail</h1>
              <p className="text-xs text-slate-400 mt-0.5">Immutable chronological ledger of holds, confirmations, check-in handovers, and status changes.</p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl font-mono text-xs">
              <table className="w-full text-left">
                <thead className="bg-slate-950 text-slate-400 uppercase border-b border-slate-800">
                  <tr>
                    <th className="p-3.5">Timestamp (UTC)</th>
                    <th className="p-3.5">Action</th>
                    <th className="p-3.5">Actor</th>
                    <th className="p-3.5">Context & Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {auditLogs.map(log => (
                    <tr key={log.id} className="hover:bg-slate-800/40">
                      <td className="p-3.5 text-slate-400 whitespace-nowrap">{log.created_at}</td>
                      <td className="p-3.5">
                        <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-amber-400 font-bold border border-slate-700">
                          {log.action}
                        </span>
                      </td>
                      <td className="p-3.5 text-slate-300">{log.user}</td>
                      <td className="p-3.5 text-slate-200">
                        <div className="font-bold text-white">{log.title}</div>
                        <div className="text-[11px] text-slate-400 font-sans">{log.details}</div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </main>

      {/* ========================================================================= */}
      {/* MODAL 1: CHECKOUT & 15-MINUTE HOLD MODAL */}
      {/* ========================================================================= */}
      {checkoutModalOpen && activeHold && (
        <div className="fixed inset-0 z-50 bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-slate-900 border-2 border-amber-500/60 rounded-3xl max-w-xl w-full p-6 sm:p-8 shadow-2xl text-left relative">
            <button 
              onClick={() => setCheckoutModalOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Countdown Badge */}
            <div className="flex items-center justify-between p-3.5 rounded-xl bg-gradient-to-r from-amber-950/80 to-slate-950 border border-amber-500/40 mb-6">
              <div className="flex items-center space-x-2 text-amber-300 text-xs font-mono font-bold">
                <Lock className="w-4 h-4 text-amber-400" />
                <span>Room #{activeHold.room_number} Locked for You</span>
              </div>
              <div className="font-mono text-base font-bold text-amber-400 animate-pulse">
                {formatTimer(holdSecondsLeft)}
              </div>
            </div>

            <h3 className="text-2xl font-serif font-bold text-white">Complete Your Reservation</h3>
            <p className="text-xs text-slate-400 mt-1 font-mono">
              Stay: {activeHold.check_in} to {activeHold.check_out} &bull; {activeHold.room_type}
            </p>

            {/* Addons */}
            <div className="my-5 space-y-2">
              <label className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs cursor-pointer">
                <div className="flex items-center space-x-2">
                  <input 
                    type="checkbox" 
                    checked={addons.breakfast} 
                    onChange={(e) => setAddons({ ...addons, breakfast: e.target.checked })} 
                    className="rounded text-amber-500 bg-slate-900 border-slate-700" 
                  />
                  <span>Artisan Breakfast Buffet</span>
                </div>
                <span className="font-mono text-amber-400">+$25 / guest / night</span>
              </label>

              <label className="flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs cursor-pointer">
                <div className="flex items-center space-x-2">
                  <input 
                    type="checkbox" 
                    checked={addons.shuttle} 
                    onChange={(e) => setAddons({ ...addons, shuttle: e.target.checked })} 
                    className="rounded text-amber-500 bg-slate-900 border-slate-700" 
                  />
                  <span>Private Airport Mercedes Shuttle</span>
                </div>
                <span className="font-mono text-amber-400">+$45 flat</span>
              </label>
            </div>

            {/* Simulated Payment Card */}
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 mb-6 space-y-3">
              <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                <span>SIMULATED SANDBOX CARD</span>
                <span className="text-emerald-400">● 3D-Secure Test Mode</span>
              </div>
              <input 
                type="text" 
                value="4242 •••• •••• 4242" 
                readOnly 
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-amber-400" 
              />
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <input type="text" value="Exp: 12 / 28" readOnly className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-300" />
                <input type="text" value="CVC: 888" readOnly className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-slate-300" />
              </div>
            </div>

            <button
              onClick={handleConfirmBooking}
              disabled={isConfirming}
              className="w-full py-3.5 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold text-xs uppercase tracking-wider rounded-xl transition shadow-xl shadow-amber-500/20 flex items-center justify-center space-x-2"
            >
              {isConfirming ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
              <span>Authorize & Confirm Reservation</span>
            </button>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 2: CONFIRMATION VOUCHER MODAL */}
      {/* ========================================================================= */}
      {voucherModalOpen && confirmedReservation && (
        <div className="fixed inset-0 z-50 bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-slate-900 border-2 border-slate-700 rounded-3xl max-w-lg w-full overflow-hidden shadow-2xl text-left relative">
            <div className="bg-gradient-to-r from-amber-500 to-amber-600 p-6 text-slate-950 flex items-center justify-between">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-widest font-bold">Booking Reference</span>
                <div className="text-2xl font-mono font-bold tracking-wider">{confirmedReservation.booking_reference}</div>
              </div>
              <button onClick={() => setVoucherModalOpen(false)} className="text-slate-950 hover:opacity-75">
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs font-mono">
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                <div className="text-white font-bold text-sm">{confirmedReservation.room_type}</div>
                <div className="text-amber-400">Assigned Physical Room: #{confirmedReservation.room_number}</div>
                <div className="text-slate-400">{confirmedReservation.check_in} &rarr; {confirmedReservation.check_out} ({confirmedReservation.num_nights} Nights)</div>
              </div>

              <div className="flex justify-between text-slate-300">
                <span>Guest:</span>
                <span className="text-white font-bold">{confirmedReservation.guest_name}</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Total Settled:</span>
                <span className="text-amber-400 font-bold">${confirmedReservation.total_amount}</span>
              </div>
              <div className="flex justify-between text-slate-400 text-[11px]">
                <span>Transaction:</span>
                <span>{confirmedReservation.transaction_id || 'TXN-SB-VERIFIED'}</span>
              </div>

              <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
                <button onClick={() => window.print()} className="px-4 py-2 bg-slate-800 text-slate-200 rounded-lg text-xs font-semibold flex items-center space-x-1">
                  <Printer className="w-4 h-4" />
                  <span>Print Voucher</span>
                </button>
                <button onClick={() => setVoucherModalOpen(false)} className="px-4 py-2 bg-amber-500 text-slate-950 font-bold rounded-lg text-xs">
                  Done
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="bg-slate-950 border-t border-slate-800/80 py-8 text-xs text-slate-400 text-center">
        <p>&copy; 2026 GrandView Hotel & Resort. Built with React 18 + Django 5 + Tailwind CSS.</p>
        <p className="font-mono text-amber-500 mt-1">ACID Concurrency Protected &bull; 15-Minute Temporary Holds Enabled</p>
      </footer>

    </div>
  );
}
