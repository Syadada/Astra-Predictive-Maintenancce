/**
 * PredictaGuard – Shared Sidebar Component
 *
 * Usage: include this file, then call renderSidebar('page-id') at end of <body>.
 *
 * Valid page IDs: 'overview' | 'predictions' | 'equipment' | 'alerts'
 *                 | 'maintenance' | 'reports' | 'support' | 'settings'
 *
 * Optional second argument overrides the sidebar's position/size/z-index classes
 * (used only by overview.html which has a full-width top bar above the sidebar):
 *   renderSidebar('overview', 'top-16 h-[calc(100vh-64px)] z-50')
 */
(function () {
  'use strict';

  // ─── SESSION SECURITY GUARD ───────────────────────────────────────────────
  var currentPath = window.location.pathname.split('/').pop().toLowerCase();
  var currentUser = JSON.parse(localStorage.getItem('currentUser'));

  // Define public pages
  var isPublicPage = (currentPath === 'login.html' || currentPath === 'presentationsite.html');

  if (!currentUser && !isPublicPage) {
    console.warn('[ASTRA-Security] No active session found. Redirecting to login.');
    window.location.href = 'login.html';
    return;
  }

  // ─── IDLE SESSION TIMEOUT ─────────────────────────────────────────────────
  // Auto logout after 15 minutes of no user activity.
  // Shows a 60-second countdown warning modal before logging out.
  var IDLE_TIMEOUT_MS   = 15 * 60 * 1000;  // 15 minutes
  var WARNING_BEFORE_MS = 60 * 1000;        // Show warning 60 seconds before logout
  var _idleTimer        = null;
  var _warningTimer     = null;
  var _countdownInterval= null;
  var _warningVisible   = false;

  function _clearSession() {
    localStorage.removeItem('currentUser');
  }

  function _forceLogout(reason) {
    _clearSession();
    clearTimeout(_idleTimer);
    clearTimeout(_warningTimer);
    clearInterval(_countdownInterval);
    var msg = encodeURIComponent(reason || 'session_expired');
    window.location.href = 'login.html?reason=' + msg;
  }

  function _hideWarningModal() {
    var modal = document.getElementById('pg-idle-warning-modal');
    if (modal) modal.remove();
    _warningVisible = false;
    clearInterval(_countdownInterval);
  }

  function _showWarningModal(secondsLeft) {
    if (_warningVisible) return;
    _warningVisible = true;

    var modal = document.createElement('div');
    modal.id = 'pg-idle-warning-modal';
    modal.style.cssText = [
      'position:fixed;inset:0;z-index:99999;',
      'display:flex;align-items:center;justify-content:center;',
      'background:rgba(0,0,0,0.55);backdrop-filter:blur(4px);',
      'animation:pgFadeIn 0.25s ease;'
    ].join('');

    modal.innerHTML = [
      '<style>',
        '@keyframes pgFadeIn{from{opacity:0}to{opacity:1}}',
        '@keyframes pgPulse{0%,100%{opacity:1}50%{opacity:0.6}}',
        '#pg-idle-countdown{animation:pgPulse 1s ease-in-out infinite;}',
      '</style>',
      '<div style="',
        'background:#fff;border-radius:16px;',
        'padding:32px 36px;max-width:400px;width:90%;',
        'box-shadow:0 24px 64px rgba(0,0,0,0.35);',
        'border:1px solid #E2DDD6;text-align:center;',
        'font-family:Inter,sans-serif;',
      '">',
        '<div style="',
          'width:56px;height:56px;border-radius:50%;',
          'background:#fff8f0;border:2px solid #E67E22;',
          'display:flex;align-items:center;justify-content:center;',
          'margin:0 auto 16px;',
        '">',
          '<span style="font-size:28px;">⏱️</span>',
        '</div>',
        '<h2 style="font-size:18px;font-weight:700;color:#1b1c1a;margin:0 0 8px;">Session Expiring Soon</h2>',
        '<p style="font-size:14px;color:#6B6860;margin:0 0 20px;line-height:1.5;">',
          'You have been inactive for 14 minutes.<br>',
          'Your session will automatically end in:',
        '</p>',
        '<div id="pg-idle-countdown" style="',
          'font-size:48px;font-weight:700;color:#E67E22;',
          'font-family:JetBrains Mono,monospace;',
          'margin:0 0 24px;line-height:1;',
        '">' + secondsLeft + 's</div>',
        '<div style="display:flex;gap:12px;justify-content:center;">',
          '<button id="pg-idle-stay" style="',
            'padding:10px 24px;border-radius:8px;',
            'background:#003720;color:#fff;',
            'font-size:14px;font-weight:700;border:none;cursor:pointer;',
            'transition:opacity 0.2s;',
          '" onmouseover="this.style.opacity=\'0.85\'" onmouseout="this.style.opacity=\'1\'">',
            '✅ Stay Logged In',
          '</button>',
          '<button id="pg-idle-logout" style="',
            'padding:10px 24px;border-radius:8px;',
            'background:#fff;color:#ba1a1a;',
            'border:1.5px solid #ba1a1a;',
            'font-size:14px;font-weight:700;cursor:pointer;',
            'transition:background 0.2s;',
          '" onmouseover="this.style.background=\'#fff5f5\'" onmouseout="this.style.background=\'#fff\'">',
            'Logout Now',
          '</button>',
        '</div>',
      '</div>'
    ].join('');

    document.body.appendChild(modal);

    // Wire buttons
    document.getElementById('pg-idle-stay').addEventListener('click', function () {
      _hideWarningModal();
      _resetIdleTimer();
    });
    document.getElementById('pg-idle-logout').addEventListener('click', function () {
      _forceLogout('user_logout');
    });

    // Countdown ticker
    var remaining = secondsLeft;
    _countdownInterval = setInterval(function () {
      remaining--;
      var el = document.getElementById('pg-idle-countdown');
      if (el) el.textContent = remaining + 's';
      if (remaining <= 0) {
        clearInterval(_countdownInterval);
      }
    }, 1000);
  }

  function _resetIdleTimer() {
    // Clear existing timers
    clearTimeout(_idleTimer);
    clearTimeout(_warningTimer);

    // Hide warning if user is active again
    if (_warningVisible) {
      _hideWarningModal();
    }

    // Set warning timer (fires WARNING_BEFORE_MS before logout)
    _warningTimer = setTimeout(function () {
      _showWarningModal(Math.round(WARNING_BEFORE_MS / 1000));
    }, IDLE_TIMEOUT_MS - WARNING_BEFORE_MS);

    // Set final logout timer
    _idleTimer = setTimeout(function () {
      _forceLogout('idle_timeout');
    }, IDLE_TIMEOUT_MS);
  }

  // Start idle monitoring only on authenticated, non-public pages
  if (!isPublicPage && currentUser) {
    // Events that count as user activity
    var _ACTIVITY_EVENTS = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll', 'click'];
    _ACTIVITY_EVENTS.forEach(function (evt) {
      document.addEventListener(evt, _resetIdleTimer, { passive: true });
    });

    // Start the timer on load
    _resetIdleTimer();

    // Expose logout function globally so profile/settings pages can call it
    window.pgLogout = function () { _forceLogout('user_logout'); };

    console.log('[ASTRA-Security] Idle session timeout active (' + (IDLE_TIMEOUT_MS / 60000) + ' min).');
  }

  if (!currentUser && !isPublicPage) {
    console.warn('[ASTRA-Security] No active session found. Redirecting to login.');
    window.location.href = 'login.html';
    return;
  }

  // ─── ROLE-BASED ACCESS CONTROL PERMISSIONS ────────────────────────────────
  var ROLE_PERMISSIONS = {
    "Super Admin": ["overview", "predictions", "equipment", "alerts", "maintenance", "maintenance_crud", "reports", "simulation", "settings", "support", "accounts"],
    "Admin": ["overview", "predictions", "alerts", "reports", "simulation", "settings", "support", "maintenance_crud"],
    "Maintenance": ["overview", "alerts", "equipment", "maintenance", "maintenance_crud", "settings", "support"],
    "Operator": ["overview", "alerts", "settings", "support"]
  };

  // ─── CLEARANCE-BASED ACCESS CONTROL REQUIREMENTS ──────────────────────────
  // Level 1 = Operator, Level 2 = Maintenance, Level 3 = Admin, Level 4 = Super Admin
  var CLEARANCE_REQUIREMENTS = {
    "overview": 1,
    "alerts": 1,
    "support": 1,
    "settings": 1,
    "equipment": 2,
    "maintenance": 2,
    "maintenance_crud": 2,
    "predictions": 3,
    "reports": 3,
    "simulation": 3,
    "accounts": 4
  };

  function getUserClearanceLevel(clearanceStr) {
    if (!clearanceStr) return 1;
    var num = parseInt(clearanceStr.replace(/[^0-9]/g, ''), 10);
    return isNaN(num) ? 1 : num;
  }

  var NAV_ITEMS = [
    { id: 'overview',    label: 'Overview',    icon: 'dashboard',               href: 'overview.html'    },
    { id: 'predictions', label: 'Predictions', icon: 'online_prediction',       href: 'prediction.html'  },
    { id: 'equipment',   label: 'Equipment',   icon: 'precision_manufacturing',  href: 'equipment.html'   },
    { id: 'alerts',      label: 'Alerts',      icon: 'warning',                 href: 'alerts.html'      },
    { id: 'maintenance', label: 'Maintenance', icon: 'construction',            href: 'maintenance.html' },
    { id: 'reports',     label: 'Reports',     icon: 'description',             href: 'reports.html'     },
    { id: 'simulation',  label: 'DB Simulation', icon: 'database',               href: 'simulation.html'  },
  ];

  var BOTTOM_ITEMS = [
    { id: 'accounts', label: 'Accounts', icon: 'manage_accounts', href: 'accounts.html' },
    { id: 'support',  label: 'Support',  icon: 'support_agent', href: 'support.html'           },
    { id: 'settings', label: 'Settings', icon: 'settings',      href: 'profilensettings.html'  },
  ];

  // Fallback avatar
  var AVATAR_SRC = 'https://lh3.googleusercontent.com/aida-public/AB6AXuAJB3nF963ZDZN5AzByGsqb2MxVyIvYYJZPDV3NOPF900ug_3y-d7MEHM9IcmdVDLg62EThO7ZZgtVfPH2qBLypFdU6CntX3pU3T1JaCfwVtgGdlrtJC5dzHHTfJxSNG-UN1NvfxKBe1DzYgQaD3aqaZg3Xxnt5j4CGxyaLfpyjHJO3tUUkGQIBvHZZAZPScXVH5c1S1afsZtZtXFKb6SEtVWsYVchjtnhJNUrqnmceziBRB5_XQGZV4hDOih0mFzLsvnv-I80nDtU';

  function buildLink(item, activePage) {
    var isActive = (item.id === activePage);
    var stateClasses = isActive
      ? 'bg-secondary-container text-on-secondary-container font-bold'
      : 'text-on-primary/70 hover:text-on-primary hover:bg-primary-fixed-dim/10 active:scale-95';
    return [
      '<a class="flex items-center gap-md px-md py-sm rounded-lg transition-all duration-150 ease-in-out ',
      stateClasses,
      '" href="', item.href, '"',
      ' aria-current="', (isActive ? 'page' : 'false'), '">',
      '<span class="material-symbols-outlined">', item.icon, '</span>',
      '<span class="font-data-label text-data-label">', item.label, '</span>',
      '</a>',
    ].join('');
  }

  function renderSidebar(activePage, positionClasses) {
    var user = currentUser || {
      name: "Guest Operator",
      role: "Operator",
      clearance: "Level 1",
      title: "Field Systems Operator",
      avatar: AVATAR_SRC
    };

    var userLevel = getUserClearanceLevel(user.clearance);

    // ─── ROUTE GUARD ─────────────────────────────────────────────────────────
    var allowedPages = ROLE_PERMISSIONS[user.role] || ["overview", "alerts", "support"];
    var reqLevel = CLEARANCE_REQUIREMENTS[activePage] || 1;

    if (activePage && (userLevel < reqLevel || !allowedPages.includes(activePage))) {
      console.warn('[ASTRA-Security] Access denied for:', activePage, 'Required level:', reqLevel, 'User level:', userLevel);
      alert('⚠️ Access Denied: You do not have sufficient clearance to access this page.\nRequired Clearance: Level ' + reqLevel + '\nYour Clearance: ' + user.clearance);
      window.location.href = 'overview.html';
      return;
    }

    var filteredNavItems = NAV_ITEMS.filter(function (item) {
      var itemReq = CLEARANCE_REQUIREMENTS[item.id] || 1;
      return userLevel >= itemReq && allowedPages.includes(item.id);
    });
    var filteredBottomItems = BOTTOM_ITEMS.filter(function (item) {
      var itemReq = CLEARANCE_REQUIREMENTS[item.id] || 1;
      return userLevel >= itemReq && allowedPages.includes(item.id);
    });

    var pos = positionClasses || 'top-0 h-screen z-[100]';

    var html = [
      // ── Sidebar ──────────────────────────────────────────────────────────
      '<aside id="app-sidebar"',
      ' class="fixed left-0 ', pos, ' w-64 bg-primary flex flex-col py-lg px-md',
      ' border-r border-outline/10 hidden md:flex"',
      ' aria-label="Main navigation">',

        // Brand
        '<div class="mb-xl px-sm">',
          '<h1 class="font-hero-lg text-body-lg text-on-primary tracking-tight">Project ASTRA</h1>',
          '<p class="font-data-label text-data-label text-on-primary/60 mt-1 uppercase tracking-widest">',
            'Motor Predictive Maintenance v1.0',
          '</p>',
        '</div>',

        // Primary navigation
        '<nav class="flex-1 flex flex-col gap-xs" aria-label="Primary navigation">',
          filteredNavItems.map(function (item) { return buildLink(item, activePage); }).join(''),
        '</nav>',

        // Active dataset chip
        '<div class="px-sm mb-md">',
          '<div class="bg-primary-container/30 rounded-lg p-sm border border-outline/10">',
            '<p class="text-[10px] font-data-label text-on-primary/50 uppercase tracking-tighter mb-1">',
              'Ingestion Database',
            '</p>',
            '<div class="flex justify-between items-end">',
              '<span class="text-body-sm font-bold text-on-primary">On-Premise DB</span>',
              '<span class="text-[10px] font-data-value text-green-good">LIVE</span>',
            '</div>',
          '</div>',
        '</div>',

        // Bottom links + user
        '<div class="border-t border-outline/10 pt-md flex flex-col gap-xs">',
          filteredBottomItems.map(function (item) { return buildLink(item, activePage); }).join(''),
          '<div class="mt-md flex items-center gap-md px-sm">',
            '<div class="w-8 h-8 rounded-full bg-secondary-container flex items-center',
            ' justify-center overflow-hidden flex-shrink-0">',
              '<img src="', user.avatar || AVATAR_SRC, '"',
              ' alt="', user.name, '" class="w-full h-full object-cover">',
            '</div>',
            '<div class="flex flex-col overflow-hidden">',
              '<span class="text-[12px] font-bold text-on-primary truncate">', user.name, '</span>',
              '<span class="text-[10px] text-on-primary/50">', user.role, ' (', user.clearance, ')</span>',
            '</div>',
          '</div>',
        '</div>',

      '</aside>',

      // ── Mobile backdrop ───────────────────────────────────────────────────
      '<div id="sidebar-overlay"',
      ' class="fixed inset-0 bg-black/50 z-[99] hidden"',
      ' aria-hidden="true"></div>',
    ].join('');

    document.body.insertAdjacentHTML('afterbegin', html);

    // Reveal page now that sidebar is in place (matches html { opacity:0 } in styles.css)
    document.documentElement.classList.add('pg-ready');

    // Wire every element that carries data-sidebar-toggle (hamburger buttons)
    document.querySelectorAll('[data-sidebar-toggle]').forEach(function (el) {
      el.addEventListener('click', toggleSidebar);
    });

    var overlay = document.getElementById('sidebar-overlay');
    if (overlay) {
      overlay.addEventListener('click', closeSidebar);
    }
  }

  // On mobile, toggle between hidden and flex.
  // On desktop, md:flex keeps the sidebar visible regardless of the hidden class.
  function toggleSidebar() {
    if (window.innerWidth >= 768) return;
    var sidebar = document.getElementById('app-sidebar');
    var overlay = document.getElementById('sidebar-overlay');
    var isHidden = sidebar.classList.contains('hidden');
    if (isHidden) {
      sidebar.classList.remove('hidden');
      sidebar.classList.add('flex');
      overlay.classList.remove('hidden');
    } else {
      sidebar.classList.add('hidden');
      sidebar.classList.remove('flex');
      overlay.classList.add('hidden');
    }
  }

  function closeSidebar() {
    var sidebar = document.getElementById('app-sidebar');
    var overlay = document.getElementById('sidebar-overlay');
    if (sidebar) { sidebar.classList.add('hidden'); sidebar.classList.remove('flex'); }
    if (overlay) { overlay.classList.add('hidden'); }
  }

  window.renderSidebar = renderSidebar;
  window.toggleSidebar = toggleSidebar;
  window.closeSidebar  = closeSidebar;
}());
