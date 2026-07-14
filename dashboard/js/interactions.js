(function () {
  'use strict';

  // ─── TOAST ─────────────────────────────────────────────────────────────────
  var ICONS  = { success: 'check_circle', warning: 'warning', error: 'error', info: 'info' };
  var STYLES = {
    success: 'background:#003720;color:#fff;border-left:4px solid #27AE60;',
    warning: 'background:#fff8f0;color:#92400e;border-left:4px solid #E67E22;',
    error:   'background:#fff5f5;color:#7f1d1d;border-left:4px solid #C0392B;',
    info:    'background:#f0f7f4;color:#003720;border-left:4px solid #003720;'
  };

  function pgPlaySound(type) {
    try {
      var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      if (type === 'error' || type === 'warning') {
        var osc1 = audioCtx.createOscillator();
        var gain1 = audioCtx.createGain();
        osc1.type = 'sine';
        osc1.frequency.setValueAtTime(520, audioCtx.currentTime);
        gain1.gain.setValueAtTime(0.12, audioCtx.currentTime);
        gain1.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.15);
        osc1.connect(gain1);
        gain1.connect(audioCtx.destination);
        osc1.start();
        osc1.stop(audioCtx.currentTime + 0.15);

        setTimeout(function () {
          var osc2 = audioCtx.createOscillator();
          var gain2 = audioCtx.createGain();
          osc2.type = 'sine';
          osc2.frequency.setValueAtTime(660, audioCtx.currentTime);
          gain2.gain.setValueAtTime(0.15, audioCtx.currentTime);
          gain2.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.25);
          osc2.connect(gain2);
          gain2.connect(audioCtx.destination);
          osc2.start();
          osc2.stop(audioCtx.currentTime + 0.25);
        }, 100);
      } else if (type === 'success') {
        var osc = audioCtx.createOscillator();
        var gain = audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(988, audioCtx.currentTime);
        gain.gain.setValueAtTime(0.10, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.2);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.2);
      } else {
        var osc = audioCtx.createOscillator();
        var gain = audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(784, audioCtx.currentTime);
        gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.15);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.15);
      }
    } catch (e) {
      console.warn('Audio Context sound play blocked by browser policy:', e.message);
    }
  }

  function pgToast(message, type, duration) {
    type     = type     || 'success';
    duration = duration || 3500;
    
    pgPlaySound(type);

    var container = document.getElementById('pg-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'pg-toast-container';
      container.style.cssText = [
        'position:fixed;bottom:24px;right:24px;z-index:9999;',
        'display:flex;flex-direction:column;gap:8px;',
        'pointer-events:none;max-width:360px;'
      ].join('');
      document.body.appendChild(container);
    }

    var toast = document.createElement('div');
    toast.style.cssText = [
      'display:flex;align-items:flex-start;gap:10px;',
      'padding:12px 16px;border-radius:8px;',
      'box-shadow:0 4px 16px rgba(0,0,0,0.14);',
      'font-family:inherit;font-size:13px;line-height:1.45;',
      'pointer-events:auto;',
      'opacity:0;transform:translateX(16px);',
      'transition:opacity 0.2s ease,transform 0.2s ease;',
      STYLES[type] || STYLES.info
    ].join('');

    toast.innerHTML =
      '<span class="material-symbols-outlined" style="font-size:18px;flex-shrink:0;margin-top:1px;">' +
        (ICONS[type] || 'info') +
      '</span>' +
      '<span>' + message + '</span>';

    container.appendChild(toast);

    // two rAFs to ensure layout before transition fires
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        toast.style.opacity   = '1';
        toast.style.transform = 'translateX(0)';
      });
    });

    setTimeout(function () {
      toast.style.opacity   = '0';
      toast.style.transform = 'translateX(16px)';
      setTimeout(function () {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 250);
    }, duration);
  }

  // ─── CONFIRMATION DIALOG ────────────────────────────────────────────────────
  function pgConfirm(message, onConfirm, opts) {
    opts        = opts        || {};
    var destr   = opts.destructive !== false && !!opts.destructive;
    var okLabel = destr ? 'Proceed' : 'Confirm';
    var okColor = destr ? '#C0392B' : '#003720';
    var iconName = destr ? 'warning' : 'help';

    var overlay = document.createElement('div');
    overlay.style.cssText = [
      'position:fixed;inset:0;background:rgba(0,0,0,0.45);',
      'z-index:9998;display:flex;align-items:center;justify-content:center;',
      'padding:24px;backdrop-filter:blur(2px);',
      'opacity:0;transition:opacity 0.15s ease;'
    ].join('');

    var dialog = document.createElement('div');
    dialog.style.cssText = [
      'background:#fff;border-radius:12px;padding:28px;',
      'max-width:400px;width:100%;',
      'box-shadow:0 20px 60px rgba(0,0,0,0.18);',
      'font-family:inherit;',
      'transform:scale(0.95);transition:transform 0.15s ease;'
    ].join('');

    dialog.innerHTML =
      '<div style="display:flex;align-items:flex-start;gap:14px;margin-bottom:22px;">' +
        '<span class="material-symbols-outlined" style="color:' + okColor + ';font-size:24px;flex-shrink:0;">' + iconName + '</span>' +
        '<p style="font-size:14px;color:#1a2e1c;line-height:1.55;margin:0;">' + message + '</p>' +
      '</div>' +
      '<div style="display:flex;gap:10px;justify-content:flex-end;">' +
        '<button id="pg-dlg-cancel" style="padding:8px 20px;border-radius:6px;font-size:13px;font-weight:600;border:1px solid #c0c9c1;background:#fff;color:#003720;cursor:pointer;">Cancel</button>' +
        '<button id="pg-dlg-ok"     style="padding:8px 20px;border-radius:6px;font-size:13px;font-weight:600;border:none;background:' + okColor + ';color:#fff;cursor:pointer;">' + okLabel + '</button>' +
      '</div>';

    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        overlay.style.opacity    = '1';
        dialog.style.transform   = 'scale(1)';
      });
    });

    function close() {
      overlay.style.opacity  = '0';
      dialog.style.transform = 'scale(0.95)';
      setTimeout(function () {
        if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      }, 160);
    }

    dialog.querySelector('#pg-dlg-cancel').onclick = close;
    dialog.querySelector('#pg-dlg-ok').onclick = function () {
      close();
      if (onConfirm) onConfirm();
    };
    overlay.onclick = function (e) { if (e.target === overlay) close(); };
  }

  // ─── MOCK DOWNLOAD ──────────────────────────────────────────────────────────
  function pgMockDownload(filename, ext) {
    ext = ext || 'pdf';
    pgToast('Preparing ' + filename + '.' + ext + '…', 'info', 2000);
    setTimeout(function () {
      var content, mime;
      if (ext === 'csv') {
        content = 'Report,Generated,Status\n' + filename + ',' + new Date().toISOString().slice(0, 10) + ',Completed';
        mime    = 'text/csv';
      } else {
        content = '%PDF-1.4\n% PredictaGuard — ' + filename + '\n1 0 obj<</Type/Catalog>>endobj\n';
        mime    = 'application/pdf';
      }
      var blob = new Blob([content], { type: mime });
      var url  = URL.createObjectURL(blob);
      var a    = document.createElement('a');
      a.href     = url;
      a.download = filename + '.' + ext;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      pgToast(filename + '.' + ext + ' downloaded', 'success', 2500);
    }, 900);
  }

  // ─── TIMELINE TOGGLE (DAY / WEEK / MONTH) ──────────────────────────────────
  function pgTimelineToggle(btn) {
    var siblings = btn.parentNode.querySelectorAll('button');
    siblings.forEach(function (b) {
      b.className = b.className
        .replace('bg-primary', 'bg-surface-container')
        .replace('text-white', 'text-on-surface-variant');
    });
    btn.className = btn.className
      .replace('bg-surface-container', 'bg-primary')
      .replace('text-on-surface-variant', 'text-white');
    pgToast('Timeline view: ' + btn.textContent.trim(), 'info', 1500);
  }

  // ─── NOTIFICATION SETTINGS PRE-LOAD & CACHE ───────────────────────────────
  var pgNotificationSettings = {
    recipient_email: 'recipient@example.com',
    recipient_whatsapp: '628999999999'
  };

  async function pgLoadNotificationSettings() {
    console.log('[ASTRA-Notifier] Pre-loading notification settings from database...');
    try {
      var apiBase = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';
      var url = apiBase + '/api/settings/notifications';
      var response = await fetch(url);
      if (response.ok) {
        var settings = await response.json();
        console.log('[ASTRA-Notifier] Settings loaded successfully:', settings);
        if (settings.recipient_email) {
          pgNotificationSettings.recipient_email = settings.recipient_email;
        }
        if (settings.recipient_whatsapp) {
          // Clean phone number: remove non-digits
          var phone = settings.recipient_whatsapp.replace(/\D/g, '');
          // Format local Indonesian prefix to international (e.g., 089... -> 6289... and 62089... -> 6289...)
          if (phone.startsWith('0')) {
            phone = '62' + phone.slice(1);
          } else if (phone.startsWith('620')) {
            phone = '62' + phone.slice(3);
          }
          pgNotificationSettings.recipient_whatsapp = phone;
          console.log('[ASTRA-Notifier] Resolved recipient_whatsapp to:', phone);
        }
      } else {
        console.warn('[ASTRA-Notifier] Non-OK response from settings API:', response.status);
      }
    } catch (err) {
      console.log('[ASTRA-Notifier] Failed to pre-load settings from API (using hardcoded defaults):', err);
    }
  }

  // Bind settings load to page execution
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', pgLoadNotificationSettings);
  } else {
    pgLoadNotificationSettings();
  }

  function pgDispatchAlert(machineId, machineName, message) {
    console.log('[ASTRA-Notifier] pgDispatchAlert (Backend Twilio + SMTP) invoked:', { machineId, machineName, message });
    pgToast('Dispatching alerts in background...', 'info', 1500);
    
    var apiBase = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';
    var url = apiBase + '/api/alerts/dispatch';
    console.log('[ASTRA-Notifier] Sending POST request to backend alert gateway:', url);
    
    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ machine_id: machineId, message: message })
    })
    .then(function(res) {
      console.log('[ASTRA-Notifier] Backend API response status:', res.status);
      if (!res.ok) throw new Error('HTTP status ' + res.status);
      return res.json();
    })
    .then(function(data) {
      console.log('[ASTRA-Notifier] Backend alerts successfully queued/dispatched:', data);
      pgToast('Alert dispatched via Email & WhatsApp (Twilio)!', 'success');
    })
    .catch(function(err) {
      console.error('[ASTRA-Notifier] Backend dispatch failed:', err);
      pgToast('Failed to dispatch alert: ' + err.message, 'error');
    });
  }

  function pgCreateWorkOrder(assetId, assetName, status, anomalyScore, faultClass, rul) {
    console.log('[ASTRA-CMMS] pgCreateWorkOrder invoked:', { assetId, assetName, status, anomalyScore, faultClass, rul });
    
    // Let's build a beautiful custom selection overlay modal!
    var overlay = document.createElement('div');
    overlay.style.cssText = [
      'position:fixed;inset:0;background:rgba(0,0,0,0.45);',
      'z-index:9999;display:flex;align-items:center;justify-content:center;',
      'padding:24px;backdrop-filter:blur(2px);'
    ].join('');

    var dialog = document.createElement('div');
    dialog.style.cssText = [
      'background:#fff;border-radius:12px;padding:28px;',
      'max-width:420px;width:100%;',
      'box-shadow:0 20px 60px rgba(0,0,0,0.18);',
      'font-family:inherit;color:#1b1c1a;'
    ].join('');

    var defaultTechs = [
      { name: "J. Sutherland" },
      { name: "M. Rossi" },
      { name: "S. O'Brien" },
      { name: "H. Tanaka" }
    ];

    var optionsHtml = defaultTechs.map(function(t) {
      return '<option value="' + t.name + '">' + t.name + '</option>';
    }).join('');

    dialog.innerHTML = [
      '<div style="display:flex;align-items:flex-start;gap:14px;margin-bottom:20px;">',
        '<span class="material-symbols-outlined" style="color:#003720;font-size:24px;flex-shrink:0;">engineering</span>',
        '<div>',
          '<h4 style="font-size:16px;font-weight:700;margin:0 0 4px 0;color:#003720;">Assign Work Order</h4>',
          '<p style="font-size:12px;color:#6B6860;line-height:1.45;margin:0;">Create a work order for <strong>' + assetName + '</strong>. Choose a technician for assignment:</p>',
        '</div>',
      '</div>',
      '<div style="margin-bottom:22px;">',
        '<label style="display:block;font-size:10px;font-weight:600;text-transform:uppercase;color:#6B6860;margin-bottom:6px;">Select Technician</label>',
        '<select id="dlg-assigned-tech" style="width:100%;padding:10px;border-radius:8px;border:1px solid #E2DDD6;background:#faf9f6;font-size:13px;color:#1A1A18;">',
          optionsHtml,
        '</select>',
      '</div>',
      '<div style="display:flex;gap:10px;justify-content:flex-end;">',
        '<button id="pg-dlg-cancel" style="padding:8px 20px;border-radius:6px;font-size:13px;font-weight:600;border:1px solid #c0c9c1;background:#fff;color:#003720;cursor:pointer;">Cancel</button>',
        '<button id="pg-dlg-ok"     style="padding:8px 20px;border-radius:6px;font-size:13px;font-weight:600;border:none;background:#003720;color:#fff;cursor:pointer;">Dispatch</button>',
      '</div>'
    ].join('');

    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    function close() {
      if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
    }

    dialog.querySelector('#pg-dlg-cancel').onclick = close;
    dialog.querySelector('#pg-dlg-ok').onclick = function () {
      var assignedTech = dialog.querySelector('#dlg-assigned-tech').value;
      close();
      
      pgToast('Creating work order in database...', 'info', 1500);
      var apiBase = window.location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '';
      var url = apiBase + '/api/workorders';
      var description = `Overview auto-dispatched. Status: ${status.toUpperCase()}. Anomaly: ${Math.round(anomalyScore * 100)}%. Fault: ${faultClass}. RUL: ${rul}.`;
      
      fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          asset_id: assetId,
          asset_name: assetName,
          description: description,
          assigned_tech: assignedTech
        })
      })
      .then(function(res) {
        if (!res.ok) throw new Error('HTTP status ' + res.status);
        return res.json();
      })
      .then(function(data) {
        pgToast(`Work order #${data.id} assigned to ${assignedTech}!`, 'success');
      })
      .catch(function(err) {
        console.error('[ASTRA-CMMS] Failed to create work order:', err);
        pgToast('Failed to create work order: ' + err.message, 'error');
      });
    };
    overlay.onclick = function (e) { if (e.target === overlay) close(); };
  }

  // ─── ANTI-FOUC FALLBACK ─────────────────────────────────────────────────────
  // Pages without sidebar.js never get .pg-ready from renderSidebar().
  // Add it on DOMContentLoaded so those pages aren't invisible forever.
  document.addEventListener('DOMContentLoaded', function () {
    document.documentElement.classList.add('pg-ready');
  });

  // ─── PUBLIC API ─────────────────────────────────────────────────────────────
  window.pgToast           = pgToast;
  window.pgConfirm         = pgConfirm;
  window.pgMockDownload    = pgMockDownload;
  window.pgTimelineToggle  = pgTimelineToggle;
  window.pgDispatchAlert   = pgDispatchAlert;
  window.pgCreateWorkOrder = pgCreateWorkOrder;
})();
