#!/usr/bin/env python3
import argparse
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import threading
import urllib.request
from pathlib import Path

try:
    import evdev
    from evdev import ecodes, UInput
except ImportError:
    print('Fehler: python3-evdev fehlt (sudo apt install python3-evdev)', file=sys.stderr)
    raise SystemExit(2)

try:
    import websocket
except ImportError:
    websocket = None

try:
    import dbus
except ImportError:
    dbus = None

DEFAULT_CONFIG = Path(
    os.environ.get(
        'SHIELD_REMOTE_CONFIG',
        str(Path.home() / 'shield-remote' / 'profiles.json'),
    )
)
REMOTE_NAME = 'NVIDIA SHIELD Remote'
LAUNCHER_PATTERN = 'shield-launcher-test.py'
RUNTIME_DIR = Path(
    os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')
)
CONTROL_SOCKET = RUNTIME_DIR / 'shield-launcher-control.sock'
SHIELD_VLC_CONTROL_SOCKET = RUNTIME_DIR / 'shield-vlc-control.sock'
REMOTE_CONTROL_SOCKET = RUNTIME_DIR / 'shield-remote-control.sock'

# Raw key codes measured on this NVIDIA SHIELD Remote.  We keep these
# explicit as a direct fallback so the transport buttons cannot be confused
# with D-pad LEFT/RIGHT by any evdev/ecodes aliasing or profile layer.
SHIELD_KEY_REWIND = 168
SHIELD_KEY_FASTFORWARD = 208
OSK_MARKER = RUNTIME_DIR / 'shield-osk-visible'

PHYSICAL = {
    ecodes.KEY_UP: 'UP',
    ecodes.KEY_DOWN: 'DOWN',
    ecodes.KEY_LEFT: 'LEFT',
    ecodes.KEY_RIGHT: 'RIGHT',
    ecodes.KEY_SELECT: 'SELECT',
    ecodes.KEY_BACK: 'BACK',
    ecodes.KEY_HOMEPAGE: 'HOME',
    ecodes.KEY_MENU: 'MENU',
    ecodes.KEY_PLAYPAUSE: 'PLAYPAUSE',
    ecodes.KEY_REWIND: 'REWIND',
    ecodes.KEY_FASTFORWARD: 'FASTFORWARD',
    ecodes.KEY_VOLUMEUP: 'VOLUMEUP',
    ecodes.KEY_VOLUMEDOWN: 'VOLUMEDOWN',
    ecodes.KEY_SEARCH: 'SEARCH',
    ecodes.KEY_VIDEO: 'VIDEO',
}

OUTPUT_KEYS = sorted(set([
    ecodes.KEY_UP, ecodes.KEY_DOWN, ecodes.KEY_LEFT, ecodes.KEY_RIGHT,
    ecodes.KEY_ENTER, ecodes.KEY_ESC, ecodes.KEY_TAB, ecodes.KEY_SPACE, ecodes.KEY_BACKSPACE,
    ecodes.KEY_PLAYPAUSE, ecodes.KEY_REWIND, ecodes.KEY_FASTFORWARD,
    ecodes.KEY_VOLUMEUP, ecodes.KEY_VOLUMEDOWN,
    ecodes.KEY_LEFTSHIFT, ecodes.KEY_LEFTALT, ecodes.KEY_LEFTCTRL,
    ecodes.KEY_L, ecodes.KEY_C, ecodes.KEY_F, ecodes.KEY_F6, ecodes.KEY_F10,
    ecodes.KEY_SELECT, ecodes.KEY_BACK, ecodes.KEY_MENU,
    ecodes.KEY_SEARCH, ecodes.KEY_VIDEO,
]))

FT_NAV_INSTALL = r'''
if (!window.__shieldNavV8) {
  window.__shieldNavV8 = (() => {
    const LABELS = {
      CONTENT: 'INHALT',
      SIDE: 'HAUPTMENÜ',
      TOP: 'KOPFLEISTE',
      PLAYER: 'PLAYER',
      RECS: 'EMPFEHLUNGEN',
      PLAYLIST: 'PLAYLISTE',
      TABS: 'SEITENREITER',
      SETTINGS_MENU: 'EINSTELLUNGS-MENÜ',
      SETTINGS_CONTENT: 'EINSTELLUNGEN',
      CHANNELS: 'ABO-KANÄLE'
    };

    let area = 'CONTENT';
    let current = null;
    let currentKey = '';
    let pickerOpen = false;
    let pickerIndex = 0;
    let pickerAreas = [];
    let outline = null;
    let badge = null;
    let picker = null;
    let lastUrl = location.href;
    let routeTimer = 0;

    // PLAYER has two layers. VIDEO keeps the player's direct seek/play controls.
    // BAR gives the Shield remote access to the actual Shaka control buttons.
    let playerLayer = 'VIDEO';
    let playerControlKey = '';

    // FreeTube's Settings page is a two-level UI on our 720x576 CRT:
    // category menu first, then the controls of the chosen section.
    let settingsSectionKey = '';
    let settingsWidgetMode = false;

    function fullscreenElement() {
      return document.fullscreenElement || document.webkitFullscreenElement || null;
    }

    function overlayHost() {
      // In browser fullscreen only descendants of the fullscreen element are
      // rendered in the top layer. Keep Shield overlays inside that element so
      // MENU/focus remain visible while a FreeTube video is fullscreen.
      return fullscreenElement() || document.documentElement;
    }

    function mountOverlay(el) {
      if (!el) return;
      const host = overlayHost();
      if (host && el.parentNode !== host) {
        try { host.appendChild(el); } catch (_) {}
      }
    }

    function rendered(el) {
      if (!el || !el.isConnected) return false;
      const s = getComputedStyle(el);
      if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity) === 0) return false;
      const r = el.getBoundingClientRect();
      return r.width >= 8 && r.height >= 8;
    }

    function onScreen(el) {
      if (!rendered(el)) return false;
      const r = el.getBoundingClientRect();
      return r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth;
    }

    function uniq(list) {
      const out = [];
      const seen = new Set();
      for (const el of list) {
        if (!rendered(el) || el.disabled || seen.has(el)) continue;
        seen.add(el);
        out.push(el);
      }
      return out;
    }

    function videoCards() {
      return uniq(Array.from(document.querySelectorAll('.ft-list-video.ft-list-item')));
    }

    function playlistCards() {
      return videoCards().filter(el => el.classList.contains('watchPlaylistItem'));
    }

    function nonPlaylistVideoCards() {
      return videoCards().filter(el => !el.classList.contains('watchPlaylistItem'));
    }

    function genericCards() {
      const cards = Array.from(document.querySelectorAll([
        '.ft-list-video.ft-list-item',
        '.ft-list-channel.ft-list-item',
        '.ft-list-playlist.ft-list-item',
        '.ft-list-item'
      ].join(',')));
      return uniq(cards).filter(el => !el.closest('.sideNav') && !el.closest('.topNav'));
    }

    function sideItems() {
      // Main navigation only.  Active subscribed channels are deliberately kept
      // out of this list so Settings / History / Trending stay reachable with
      // just a few D-pad presses even when the user has many subscriptions.
      return uniq(Array.from(document.querySelectorAll('.sideNav .navOption')));
    }

    function sideChannelItems() {
      return uniq(Array.from(document.querySelectorAll('.sideNav .navChannel.channelLink')));
    }

    function pageTabItems() {
      // FreeTube uses real ARIA tabs for Trending (Gaming/Sports/Podcasts),
      // Subscriptions (Videos/Shorts/Live/Posts), Channel pages and similar views.
      const tabs = Array.from(document.querySelectorAll('[role="tablist"] [role="tab"]'));
      return uniq(tabs);
    }

    function settingsMenuItems() {
      return uniq(Array.from(document.querySelectorAll('.settingsPage .settingsMenu a.title')));
    }

    function activeSettingsSection() {
      const sections = Array.from(document.querySelectorAll('.settingsPage .settingsContent .section')).filter(rendered);
      if (!sections.length) return null;
      if (settingsSectionKey) {
        const exact = sections.find(el => (el.dataset.section || '') === settingsSectionKey);
        if (exact) return exact;
      }
      // Mobile FreeTube shows exactly one section.  In desktop mode choose the
      // section nearest the top of the viewport.
      const visible = sections.filter(onScreen);
      const pool = visible.length ? visible : sections;
      pool.sort((a,b) => Math.abs(a.getBoundingClientRect().top - 90) - Math.abs(b.getBoundingClientRect().top - 90));
      return pool[0];
    }

    function settingsContentItems() {
      const section = activeSettingsSection();
      if (!section) return [];
      const raw = Array.from(section.querySelectorAll([
        'button:not([disabled])',
        'a[href]',
        'select:not([disabled])',
        'textarea:not([disabled])',
        'input:not([disabled]):not([type="hidden"]):not(.switch-input)',
        '.switch-ctn:not(.disabled) .switch-label',
        '[role="button"]',
        '[role="checkbox"]',
        '[role="switch"]',
        '[role="radio"]'
      ].join(',')));
      return uniq(raw).filter(el => !el.closest('#__shield_area_picker, #__shield_nav_badge, #__shield_nav_outline'));
    }

    function topItems() {
      const top = document.querySelector('.topNav');
      if (!top) return [];
      const raw = Array.from(top.querySelectorAll([
        '.navIconButton',
        '.searchInput input',
        '.searchContainer input',
        '.navFilterButton',
        'select',
        '[role="combobox"]',
        '.profiles button',
        '.profiles [role="button"]'
      ].join(',')));
      return uniq(raw).filter(el => !el.classList.contains('menuButton'));
    }

    function isSearchInput(el) {
      if (!el || !el.isConnected) return false;
      try {
        return el.matches([
          '.topNav .searchInput input.ft-input',
          '.topNav .searchContainer input.ft-input',
          '.topNav .ft-input-component.search input.ft-input',
          '.topNav input[placeholder*="Search"]',
          '.topNav input[placeholder*="Suche"]'
        ].join(','));
      } catch (_) {
        return false;
      }
    }

    function activeSearchInput() {
      const active = document.activeElement;
      if (isSearchInput(active) && rendered(active)) return active;
      if (isSearchInput(current) && rendered(current)) return current;
      return null;
    }

    function searchSuggestionItems() {
      const input = activeSearchInput();
      if (!input) return [];
      const root = input.closest('.ft-input-component') || input.parentElement;
      if (!root) return [];
      return Array.from(root.querySelectorAll('.options .list > li')).filter(rendered);
    }

    function mainControls() {
      const raw = Array.from(document.querySelectorAll([
        'main button', 'main a[href]', 'main input', 'main textarea', 'main select',
        '#app > div:not(.topNav):not(.sideNav) button',
        '[role="tab"]', '[role="menuitem"]'
      ].join(',')));
      return uniq(raw).filter(el => {
        if (el.closest('.sideNav') || el.closest('.topNav')) return false;
        if (el.closest('.ft-list-video, .ft-list-channel, .ft-list-playlist')) return false;
        if (el.closest('#__shield_area_picker, #__shield_nav_badge, #__shield_nav_outline')) return false;
        if (el.closest('.shaka-video-container, [data-shaka-player-container], .shaka-controls-container')) return false;
        return true;
      });
    }

    function playerElement() {
      return Array.from(document.querySelectorAll('video')).find(el => {
        if (!el || !el.isConnected) return false;
        const r = el.getBoundingClientRect();
        return r.width >= 100 && r.height >= 60;
      }) || null;
    }

    function playerContainer() {
      const video = playerElement();
      if (!video) return null;
      return video.closest('.shaka-video-container, [data-shaka-player-container]') || video.parentElement;
    }

    function isWatchPage() {
      return !!playerElement() || /\/watch\//.test(location.href);
    }

    function isSettingsPage() {
      return /\/settings(?:[/?#]|$)/.test(location.href) || !!document.querySelector('.settingsPage');
    }

    function availableAreas() {
      const out = [];
      const watch = isWatchPage();
      const settings = isSettingsPage();
      const p = playerElement();
      const pl = playlistCards();
      const videos = nonPlaylistVideoCards();
      const cards = genericCards();

      if (watch && p) out.push('PLAYER');
      if (watch && videos.length) out.push('RECS');
      if (watch && pl.length) out.push('PLAYLIST');

      if (settings) {
        if (settingsMenuItems().length) out.push('SETTINGS_MENU');
        if (settingsContentItems().length) out.push('SETTINGS_CONTENT');
      } else {
        // Page-local tabs are a first-class coarse area.  This maps directly to
        // FreeTube's own Gaming/Sports/Podcasts and Videos/Shorts/Live/Posts tabs.
        if (pageTabItems().length) out.push('TABS');
        if (!watch && (cards.length || mainControls().length)) out.push('CONTENT');
      }

      if (sideItems().length) out.push('SIDE');
      if (sideChannelItems().length) out.push('CHANNELS');
      if (topItems().length) out.push('TOP');
      if (!out.length && cards.length) out.push('CONTENT');
      return out;
    }

    function areaItems(which = area) {
      if (which === 'SIDE') return sideItems();
      if (which === 'CHANNELS') return sideChannelItems();
      if (which === 'TOP') return topItems();
      if (which === 'TABS') return pageTabItems();
      if (which === 'SETTINGS_MENU') return settingsMenuItems();
      if (which === 'SETTINGS_CONTENT') return settingsContentItems();
      if (which === 'PLAYLIST') return playlistCards();
      if (which === 'RECS') return nonPlaylistVideoCards();
      if (which === 'CONTENT') {
        const cards = genericCards();
        return cards.length ? cards : mainControls().filter(el => !el.matches('[role="tab"]'));
      }
      return [];
    }

    function ensureOverlay() {
      if (!outline || !outline.isConnected) {
        outline = document.createElement('div');
        outline.id = '__shield_nav_outline';
        Object.assign(outline.style, {
          position: 'fixed', pointerEvents: 'none', zIndex: '2147483645',
          border: '4px solid #9cff1a', borderRadius: '8px',
          boxShadow: '0 0 15px rgba(156,255,26,.95)',
          transition: 'left .04s linear, top .04s linear, width .04s linear, height .04s linear'
        });
        overlayHost().appendChild(outline);
      }
      if (!badge || !badge.isConnected) {
        badge = document.createElement('div');
        badge.id = '__shield_nav_badge';
        Object.assign(badge.style, {
          position: 'fixed', left: '12px', top: '12px', zIndex: '2147483646',
          background: 'rgba(0,0,0,.92)', color: '#9cff1a', border: '2px solid #9cff1a',
          borderRadius: '7px', padding: '6px 10px', font: 'bold 15px sans-serif',
          pointerEvents: 'none', textShadow: '0 0 7px #9cff1a'
        });
        overlayHost().appendChild(badge);
      }
      if (!picker || !picker.isConnected) {
        picker = document.createElement('div');
        picker.id = '__shield_area_picker';
        Object.assign(picker.style, {
          position: 'fixed', left: '50%', top: '68px', transform: 'translateX(-50%)',
          zIndex: '2147483647', display: 'none', maxWidth: '94vw',
          background: 'rgba(0,0,0,.96)', border: '3px solid #9cff1a', borderRadius: '10px',
          boxShadow: '0 0 20px rgba(156,255,26,.75)', padding: '8px 10px',
          whiteSpace: 'nowrap', pointerEvents: 'none', font: 'bold 17px sans-serif'
        });
        overlayHost().appendChild(picker);
      }
      // Existing overlays may have been created before fullscreen was entered.
      // Re-parent them on every use so they stay in the browser fullscreen top layer.
      mountOverlay(outline);
      mountOverlay(badge);
      mountOverlay(picker);
    }

    function showBadge(text = null, timeout = 900) {
      ensureOverlay();
      badge.textContent = text || ('BEREICH: ' + (LABELS[area] || area));
      badge.style.display = 'block';
      clearTimeout(badge.__hideTimer);
      badge.__hideTimer = setTimeout(() => { if (badge) badge.style.display = 'none'; }, timeout);
    }

    function keyFor(el) {
      if (!el) return '';
      const link = el.matches('a[href]') ? el : el.querySelector('a.title[href], a.thumbnailLink[href], a[href]');
      if (link) return 'href:' + (link.getAttribute('href') || link.href || '');
      const aria = el.getAttribute('aria-label') || '';
      const title = el.getAttribute('title') || '';
      if (aria || title) return 'label:' + (aria || title);
      const cls = typeof el.className === 'string' ? el.className : '';
      if (cls && el.tagName === 'BUTTON') return 'class:' + cls;
      const text = (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 120);
      return text ? 'text:' + text : '';
    }

    function restoreCurrent(list) {
      if (current && list.includes(current) && rendered(current)) return current;
      if (currentKey) {
        const found = list.find(el => keyFor(el) === currentKey);
        if (found) return found;
      }
      return null;
    }

    function paint() {
      ensureOverlay();
      // Never place our full-size transparent focus rectangle over the video.
      // On ARM/Electron/Wayland such overlays can interfere with video-plane
      // composition. In PLAYER/VIDEO mode we deliberately draw nothing.
      if (area === 'PLAYER' && playerLayer === 'VIDEO') {
        outline.style.display = 'none';
        return;
      }
      if (!current || !rendered(current) || pickerOpen) {
        outline.style.display = 'none';
        return;
      }
      const r = current.getBoundingClientRect();
      if (r.bottom <= 0 || r.top >= innerHeight || r.right <= 0 || r.left >= innerWidth) {
        outline.style.display = 'none';
        return;
      }
      outline.style.display = 'block';
      outline.style.left = Math.max(0, r.left - 4) + 'px';
      outline.style.top = Math.max(0, r.top - 4) + 'px';
      outline.style.width = Math.max(8, Math.min(innerWidth - Math.max(0, r.left), r.width)) + 'px';
      outline.style.height = Math.max(8, Math.min(innerHeight - Math.max(0, r.top), r.height)) + 'px';
    }

    function mark(el, scroll = true) {
      if (!el || !rendered(el)) return false;
      current = el;
      currentKey = keyFor(el);
      if (scroll) {
        try { el.scrollIntoView({block: 'nearest', inline: 'nearest', behavior: 'auto'}); } catch (_) {}
      }
      try {
        const focusTarget = el.matches('input,textarea,select,button,a,[tabindex]') ? el : el.querySelector('a.title, button, input, a[href]');
        if (focusTarget) focusTarget.focus({preventScroll: true});
      } catch (_) {}
      paint();
      setTimeout(paint, 70);
      return true;
    }

    function firstItem(which = area) {
      if (which === 'PLAYER') {
        enterPlayerVideo(false);
        return !!playerElement();
      }
      const list = areaItems(which);
      if (!list.length) return false;
      const restored = restoreCurrent(list);
      if (restored) return mark(restored);
      const visible = list.filter(onScreen);
      const source = visible.length ? visible : list;
      source.sort((a,b) => {
        const A = a.getBoundingClientRect(), B = b.getBoundingClientRect();
        return (A.top - B.top) || (A.left - B.left);
      });
      return mark(source[0]);
    }

    function chooseDefaultArea() {
      const areas = availableAreas();
      if (!areas.length) return false;
      if (isWatchPage() && areas.includes('PLAYER')) area = 'PLAYER';
      else if (isSettingsPage() && areas.includes('SETTINGS_MENU')) area = 'SETTINGS_MENU';
      else if (isSettingsPage() && areas.includes('SETTINGS_CONTENT')) area = 'SETTINGS_CONTENT';
      else if (areas.includes('CONTENT')) area = 'CONTENT';
      else area = areas[0];
      current = null;
      currentKey = '';
      playerLayer = 'VIDEO';
      settingsWidgetMode = false;
      firstItem(area);
      showBadge(area === 'PLAYER' ? 'PLAYER: VIDEO' : null);
      return true;
    }

    function renderPicker() {
      ensureOverlay();
      picker.innerHTML = '';
      pickerAreas.forEach((a, i) => {
        const span = document.createElement('span');
        span.textContent = LABELS[a] || a;
        Object.assign(span.style, {
          display: 'inline-block', margin: '2px 4px', padding: '7px 10px', borderRadius: '7px',
          color: i === pickerIndex ? '#000' : '#d9d9d9',
          background: i === pickerIndex ? '#9cff1a' : 'rgba(40,40,40,.9)',
          border: i === pickerIndex ? '2px solid #d7ff8c' : '2px solid #555'
        });
        picker.appendChild(span);
      });
      picker.style.display = pickerOpen ? 'block' : 'none';
      if (outline) outline.style.display = pickerOpen ? 'none' : outline.style.display;
    }

    function openPicker() {
      pickerAreas = availableAreas();
      if (!pickerAreas.length) return 'NO_AREAS';
      const idx = pickerAreas.indexOf(area);
      pickerIndex = idx >= 0 ? idx : 0;
      pickerOpen = true;
      renderPicker();
      showBadge('MENÜ: ← → BEREICH   OK AUSWÄHLEN', 1500);
      return 'PICKER_OPEN';
    }

    function closePicker(commit) {
      if (!pickerOpen) return false;
      if (commit && pickerAreas[pickerIndex]) {
        area = pickerAreas[pickerIndex];
        current = null;
        currentKey = '';
        if (area === 'PLAYER') playerLayer = 'VIDEO';
      }
      pickerOpen = false;
      renderPicker();
      if (commit) {
        const fs = fullscreenElement();
        // Selecting a page area while the video is fullscreen should also leave
        // fullscreen, otherwise FreeTube's SideNav/TopNav remains hidden behind
        // the fullscreen player. Exiting fullscreen does not need a synthetic click.
        if (fs && area !== 'PLAYER') {
          try {
            const exit = document.exitFullscreen || document.webkitExitFullscreen;
            if (exit) {
              const ret = exit.call(document);
              if (ret && typeof ret.catch === 'function') ret.catch(() => {});
            }
          } catch (_) {}
          setTimeout(() => {
            ensureOverlay();
            firstItem(area);
            showBadge(null, 1200);
          }, 120);
        } else {
          firstItem(area);
          showBadge(area === 'PLAYER' ? 'PLAYER: VIDEO   ↑ BEDIENLEISTE' : null, 1200);
        }
      } else {
        paint();
      }
      return true;
    }

    function pickerMove(delta) {
      if (!pickerOpen || !pickerAreas.length) return false;
      pickerIndex = (pickerIndex + delta + pickerAreas.length) % pickerAreas.length;
      renderPicker();
      return true;
    }

    function center(el) {
      const r = el.getBoundingClientRect();
      return {x: r.left + r.width / 2, y: r.top + r.height / 2, r};
    }

    function linearMove(list, delta) {
      if (!list.length) return false;
      let cur = restoreCurrent(list);
      if (!cur) return mark(list[0]);
      let i = list.indexOf(cur);
      i = Math.max(0, Math.min(list.length - 1, i + delta));
      return mark(list[i]);
    }

    async function cardMove(dir, which) {
      let list = areaItems(which);
      if (!list.length) return 'EMPTY';
      let cur = restoreCurrent(list);
      if (!cur) {
        firstItem(which);
        return 'FIRST';
      }

      const c = center(cur);
      let best = null;
      let bestScore = Infinity;
      const horizontal = dir === 'LEFT' || dir === 'RIGHT';

      for (const el of list) {
        if (el === cur) continue;
        const p = center(el);
        const dx = p.x - c.x, dy = p.y - c.y;
        let ok = false;
        let score = Infinity;

        if (dir === 'LEFT' && dx < -5) {
          const rowTolerance = Math.max(55, Math.min(c.r.height, p.r.height) * 0.65);
          if (Math.abs(dy) <= rowTolerance) { ok = true; score = (-dx) * 4 + Math.abs(dy); }
        } else if (dir === 'RIGHT' && dx > 5) {
          const rowTolerance = Math.max(55, Math.min(c.r.height, p.r.height) * 0.65);
          if (Math.abs(dy) <= rowTolerance) { ok = true; score = dx * 4 + Math.abs(dy); }
        } else if (dir === 'UP' && dy < -8) {
          ok = true; score = (-dy) * 4 + Math.abs(dx) * 1.6;
        } else if (dir === 'DOWN' && dy > 8) {
          ok = true; score = dy * 4 + Math.abs(dx) * 1.6;
        }
        if (ok && score < bestScore) { bestScore = score; best = el; }
      }

      if (!best && horizontal) {
        const ordered = list.slice().sort((a,b) => {
          const A = a.getBoundingClientRect(), B = b.getBoundingClientRect();
          return (A.top - B.top) || (A.left - B.left);
        });
        const i = Math.max(0, ordered.indexOf(cur));
        const j = dir === 'RIGHT' ? Math.min(ordered.length - 1, i + 1) : Math.max(0, i - 1);
        best = ordered[j];
      }

      if (!best && (dir === 'DOWN' || dir === 'UP')) {
        window.scrollBy({top: dir === 'DOWN' ? Math.round(innerHeight * 0.72) : -Math.round(innerHeight * 0.72), behavior: 'auto'});
        await new Promise(resolve => setTimeout(resolve, 140));
        list = areaItems(which);
        const cur2 = restoreCurrent(list) || cur;
        if (cur2) {
          const c2 = center(cur2);
          let candidate = null, score2 = Infinity;
          for (const el of list) {
            if (el === cur2) continue;
            const p = center(el);
            const dy = p.y - c2.y, dx = p.x - c2.x;
            if ((dir === 'DOWN' && dy > 8) || (dir === 'UP' && dy < -8)) {
              const sc = Math.abs(dy) * 4 + Math.abs(dx) * 1.6;
              if (sc < score2) { score2 = sc; candidate = el; }
            }
          }
          best = candidate;
        }
      }

      if (best) {
        mark(best);
        return 'OK';
      }
      mark(cur, false);
      return 'EDGE';
    }

    function genericSpatialMove(dir, list) {
      if (!list.length) return 'EMPTY';
      let cur = restoreCurrent(list);
      if (!cur) { mark(list[0]); return 'FIRST'; }
      const c = center(cur);
      let best = null, bestScore = Infinity;
      for (const el of list) {
        if (el === cur) continue;
        const p = center(el), dx = p.x-c.x, dy=p.y-c.y;
        let ok=false, primary=0, secondary=0;
        if (dir==='LEFT' && dx < -4) { ok=true; primary=-dx; secondary=Math.abs(dy); }
        if (dir==='RIGHT' && dx > 4) { ok=true; primary=dx; secondary=Math.abs(dy); }
        if (dir==='UP' && dy < -4) { ok=true; primary=-dy; secondary=Math.abs(dx); }
        if (dir==='DOWN' && dy > 4) { ok=true; primary=dy; secondary=Math.abs(dx); }
        if (!ok) continue;
        const score=primary*3.5+secondary*1.4;
        if (score<bestScore) {bestScore=score;best=el;}
      }
      if (best) { mark(best); return 'OK'; }
      return 'EDGE';
    }

    // ------------------------------------------------------------
    // Shaka player navigation
    // ------------------------------------------------------------
    function playerControlsRoot() {
      const c = playerContainer();
      if (!c) return null;
      return c.querySelector('.shaka-controls-container') || document.querySelector('.shaka-controls-container');
    }

    function wakePlayerControls() {
      const video = playerElement();
      const container = playerContainer();
      if (!video || !container) return;
      try {
        const r = video.getBoundingClientRect();
        const opts = {bubbles: true, clientX: r.left + r.width / 2, clientY: r.bottom - 24};
        container.dispatchEvent(new MouseEvent('mousemove', opts));
        video.dispatchEvent(new MouseEvent('mousemove', opts));
      } catch (_) {}
      const root = playerControlsRoot();
      if (root && playerLayer !== 'VIDEO') {
        root.style.setProperty('opacity', '1', 'important');
        root.style.setProperty('visibility', 'visible', 'important');
        root.style.setProperty('pointer-events', 'auto', 'important');
      }
    }

    function releaseForcedPlayerControls() {
      const root = playerControlsRoot();
      if (!root) return;
      root.style.removeProperty('opacity');
      root.style.removeProperty('visibility');
      root.style.removeProperty('pointer-events');
    }

    function visiblePlayerMenus() {
      const container = playerContainer() || document;
      return Array.from(container.querySelectorAll('.shaka-settings-menu, .shaka-overflow-menu'))
        .filter(rendered);
    }

    function playerMenuItems() {
      const menus = visiblePlayerMenus();
      if (!menus.length) return [];
      // Shaka may keep the parent menu visible while a submenu is open.
      // Prefer the last visible menu in DOM order, which is normally the top layer.
      const menu = menus[menus.length - 1];
      const buttons = uniq(Array.from(menu.querySelectorAll('button:not([disabled]), [role="menuitem"]')));
      return buttons.sort((a,b) => {
        const A = a.getBoundingClientRect(), B = b.getBoundingClientRect();
        return (A.top - B.top) || (A.left - B.left);
      });
    }

    function playerBarItems() {
      wakePlayerControls();
      const root = playerControlsRoot();
      if (!root) return [];
      const raw = Array.from(root.querySelectorAll([
        '.shaka-controls-button-panel button:not([disabled])',
        '.shaka-bottom-controls button:not([disabled])',
        '.shaka-top-controls button:not([disabled])'
      ].join(',')));
      return uniq(raw).filter(el => !el.closest('.shaka-settings-menu, .shaka-overflow-menu'))
        .sort((a,b) => {
          const A = a.getBoundingClientRect(), B = b.getBoundingClientRect();
          return (A.top - B.top) || (A.left - B.left);
        });
    }

    function playerLabel(el) {
      if (!el) return 'BEDIENUNG';
      const aria = (el.getAttribute('aria-label') || '').trim();
      const title = (el.getAttribute('title') || '').trim();
      const text = (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40);
      let label = aria || title || text;
      if (!label) {
        const cls = typeof el.className === 'string' ? el.className : '';
        if (/fullscreen/i.test(cls)) label = 'VOLLBILD';
        else if (/overflow/i.test(cls)) label = 'OPTIONEN';
        else if (/play/i.test(cls)) label = 'PLAY / PAUSE';
        else if (/mute|volume/i.test(cls)) label = 'TON';
        else if (/caption/i.test(cls)) label = 'UNTERTITEL';
        else label = 'BEDIENUNG';
      }
      return label.toUpperCase();
    }

    function markPlayerControl(el, kind = 'BAR') {
      if (!el || !rendered(el)) return false;
      playerLayer = kind;
      current = el;
      currentKey = keyFor(el);
      playerControlKey = currentKey;
      wakePlayerControls();
      try { el.focus({preventScroll: true}); } catch (_) {}
      paint();
      showBadge('PLAYER: ' + playerLabel(el), 1150);
      return true;
    }

    function restorePlayerItem(list) {
      if (current && list.includes(current) && rendered(current)) return current;
      if (playerControlKey) {
        const found = list.find(el => keyFor(el) === playerControlKey);
        if (found) return found;
      }
      return null;
    }

    function enterPlayerVideo(show = true) {
      playerLayer = 'VIDEO';
      current = null;
      currentKey = '';
      releaseForcedPlayerControls();
      if (outline) outline.style.display = 'none';
      if (show) showBadge('PLAYER: VIDEO   ←→ SPULEN   OK PLAY/PAUSE   ↑ BEDIENUNG', 1450);
      return 'PLAYER_VIDEO';
    }

    function enterPlayerBar() {
      playerLayer = 'BAR';
      wakePlayerControls();
      const list = playerBarItems();
      if (!list.length) {
        playerLayer = 'VIDEO';
        releaseForcedPlayerControls();
        return 'NO_PLAYER_BAR';
      }
      const restored = restorePlayerItem(list);
      const target = restored || list[0];
      markPlayerControl(target, 'BAR');
      return 'PLAYER_BAR';
    }

    function playerLinearMove(list, delta, kind) {
      if (!list.length) return 'EMPTY';
      let cur = restorePlayerItem(list);
      let idx = cur ? list.indexOf(cur) : 0;
      idx = Math.max(0, Math.min(list.length - 1, idx + delta));
      markPlayerControl(list[idx], kind);
      return 'OK';
    }

    function currentPlayerItem(list) {
      let el = restorePlayerItem(list);
      if (!el && list.length) {
        el = list[0];
        markPlayerControl(el, playerLayer === 'MENU' ? 'MENU' : 'BAR');
      }
      return el;
    }

    function playerMove(dir) {
      const menu = playerMenuItems();
      if (menu.length) {
        playerLayer = 'MENU';
        wakePlayerControls();
        if (dir === 'UP') return playerLinearMove(menu, -1, 'MENU');
        if (dir === 'DOWN') return playerLinearMove(menu, 1, 'MENU');
        if (dir === 'LEFT') return 'NATIVE_ESC';
        if (dir === 'RIGHT') {
          // A real keyboard Enter is deliberately used instead of el.click().
          // Chromium treats the physical/uinput key as trusted user activation,
          // which is required by fullscreen and is also more reliable for Shaka
          // settings/submenus. The next D-pad event re-scans the current menu.
          const el = currentPlayerItem(menu);
          if (!el) return 'EMPTY';
          try { el.focus({preventScroll: true}); } catch (_) {}
          return 'NATIVE_ENTER';
        }
        return 'EDGE';
      }

      if (playerLayer === 'VIDEO') {
        if (dir === 'LEFT' || dir === 'RIGHT') return 'NATIVE_' + dir;
        if (dir === 'UP' || dir === 'DOWN') return enterPlayerBar();
        return 'EDGE';
      }

      const bar = playerBarItems();
      if (!bar.length) return enterPlayerVideo(true);
      if (dir === 'LEFT') return playerLinearMove(bar, -1, 'BAR');
      if (dir === 'RIGHT') return playerLinearMove(bar, 1, 'BAR');
      if (dir === 'DOWN') return enterPlayerVideo(true);
      if (dir === 'UP') {
        const cur = currentPlayerItem(bar);
        if (cur) showBadge('PLAYER: ' + playerLabel(cur) + '   OK AUSWÄHLEN   ↓ VIDEO', 1200);
        return 'PLAYER_BAR';
      }
      return 'EDGE';
    }

    function activatePlayer() {
      const menu = playerMenuItems();
      if (menu.length) {
        playerLayer = 'MENU';
        const el = currentPlayerItem(menu);
        if (!el) return 'EMPTY';
        try { el.focus({preventScroll: true}); } catch (_) {}
        // Do not call HTMLElement.click() through CDP here. Fullscreen and some
        // Shaka actions need a trusted user gesture. shield-remote sends a real
        // uinput Enter after this function returns.
        return 'NATIVE_ENTER';
      }

      if (playerLayer === 'VIDEO') return 'NATIVE_SPACE';
      const bar = playerBarItems();
      const el = currentPlayerItem(bar);
      if (!el) return 'NATIVE_SPACE';
      try { el.focus({preventScroll: true}); } catch (_) {}
      return 'NATIVE_ENTER';
    }

    function playerBack() {
      const menu = playerMenuItems();
      if (menu.length) {
        // Let Shaka/browser handle the currently open settings layer.
        return 'NATIVE_ESC';
      }
      if (fullscreenElement()) {
        // BACK is always the reliable escape hatch from FreeTube fullscreen.
        // Reset our local player state first; the real Escape key is sent by
        // shield-remote immediately after this command returns.
        pickerOpen = false;
        playerLayer = 'VIDEO';
        current = null;
        currentKey = '';
        playerControlKey = '';
        if (outline) outline.style.display = 'none';
        if (picker) picker.style.display = 'none';
        return 'NATIVE_ESC';
      }
      if (playerLayer !== 'VIDEO') return enterPlayerVideo(true);
      return null;
    }

    function switchArea(nextArea, badgeText = null) {
      if (!availableAreas().includes(nextArea)) return 'NO_AREA';
      area = nextArea;
      current = null;
      currentKey = '';
      settingsWidgetMode = false;
      firstItem(area);
      showBadge(badgeText || null, 1200);
      return 'AREA_' + nextArea;
    }

    function settingsMove(dir) {
      if (settingsWidgetMode) {
        // Native widgets such as <select> get the real D-pad until OK/BACK exits
        // the widget.  This preserves FreeTube/Electron's own dropdown behavior.
        return 'NATIVE_' + dir;
      }
      const list = settingsContentItems();
      if (!list.length) return 'EMPTY';
      let cur = restoreCurrent(list);
      if (!cur) { mark(list[0]); return 'FIRST'; }

      const tag = (cur.tagName || '').toLowerCase();
      const type = (cur.getAttribute && cur.getAttribute('type') || '').toLowerCase();
      if ((tag === 'input' && (type === 'range' || type === 'number')) && (dir === 'LEFT' || dir === 'RIGHT')) {
        try { cur.focus({preventScroll:true}); } catch (_) {}
        return 'NATIVE_' + dir;
      }

      return genericSpatialMove(dir, list);
    }

    async function move(dir) {
      // FreeTube's FtInput already implements the search suggestion list with
      // ArrowUp/ArrowDown and Enter. Keep the real input focused and pass the
      // D-pad through as native keyboard events instead of spatially moving to
      // unrelated TopNav controls. LEFT/RIGHT also remain native for text cursor
      // movement (and FreeTube's own optional history-remove behavior).
      const search = activeSearchInput();
      if (!pickerOpen && area === 'TOP' && search) {
        current = search;
        currentKey = keyFor(search);
        paint();
        if (dir === 'UP' || dir === 'DOWN' || dir === 'LEFT' || dir === 'RIGHT') {
          return 'NATIVE_' + dir;
        }
      }

      if (pickerOpen) {
        if (dir === 'LEFT' || dir === 'UP') pickerMove(-1);
        else pickerMove(1);
        return 'PICKER_MOVE';
      }

      if (area === 'PLAYER') return playerMove(dir);
      if (area === 'SIDE' || area === 'CHANNELS' || area === 'SETTINGS_MENU') {
        const list = areaItems(area);
        if (dir === 'UP') return linearMove(list, -1) ? 'OK' : 'EMPTY';
        if (dir === 'DOWN') return linearMove(list, 1) ? 'OK' : 'EMPTY';
        if (area === 'SETTINGS_MENU' && dir === 'RIGHT' && settingsContentItems().length) {
          return switchArea('SETTINGS_CONTENT', 'EINSTELLUNGEN: ↑↓ NAVIGIEREN   OK ÄNDERN');
        }
        return 'EDGE';
      }
      if (area === 'TABS') {
        const list = pageTabItems();
        if (dir === 'LEFT') return linearMove(list, -1) ? 'OK' : 'EMPTY';
        if (dir === 'RIGHT') return linearMove(list, 1) ? 'OK' : 'EMPTY';
        if (dir === 'DOWN' && availableAreas().includes('CONTENT')) return switchArea('CONTENT');
        return 'EDGE';
      }
      if (area === 'SETTINGS_CONTENT') {
        if (dir === 'LEFT' && !settingsWidgetMode && settingsMenuItems().length) {
          return switchArea('SETTINGS_MENU', 'EINSTELLUNGS-MENÜ: ↑↓   OK ÖFFNEN');
        }
        return settingsMove(dir);
      }
      if (area === 'CONTENT' || area === 'RECS' || area === 'PLAYLIST') {
        const list = areaItems(area);
        const hasCards = list.some(el => el.matches('.ft-list-item, .ft-list-video, .ft-list-channel, .ft-list-playlist'));
        if (hasCards) {
          const result = await cardMove(dir, area);
          // On tabbed feeds, UP at the top row moves naturally into the page tabs.
          if (result === 'EDGE' && dir === 'UP' && pageTabItems().length && area === 'CONTENT') return switchArea('TABS');
          return result;
        }
        const result = genericSpatialMove(dir, list);
        if (result === 'EDGE' && dir === 'UP' && pageTabItems().length && area === 'CONTENT') return switchArea('TABS');
        return result;
      }
      if (area === 'TOP') {
        const list = areaItems('TOP');
        if (dir === 'LEFT') return linearMove(list, -1) ? 'OK' : 'EMPTY';
        if (dir === 'RIGHT') return linearMove(list, 1) ? 'OK' : 'EMPTY';
        return genericSpatialMove(dir, list);
      }
      return 'EMPTY';
    }

    function activateCard(el) {
      const target = el.querySelector('a.title[href], a.thumbnailLink[href], a[href]');
      if (target) {
        try { target.click(); return 'CARD_CLICK'; } catch (_) {}
      }
      try { el.click(); return 'CARD_CLICK'; } catch (_) {}
      return 'FAIL';
    }

    function activateCurrent() {
      if (pickerOpen) {
        closePicker(true);
        return 'PICKER_SELECT';
      }
      if (area === 'PLAYER') return activatePlayer();
      const list = areaItems(area);
      let el = restoreCurrent(list);
      if (!el) {
        if (!firstItem(area)) return 'EMPTY';
        el = current;
      }
      if (!el) return 'EMPTY';

      if (area === 'TABS') {
        try { el.focus({preventScroll:true}); } catch (_) {}
        // Trending and Subscriptions both bind Enter on their role=tab elements.
        return 'NATIVE_ENTER';
      }

      if (area === 'SETTINGS_MENU') {
        settingsSectionKey = (el.dataset && el.dataset.section) || '';
        try { el.click(); } catch (_) { return 'FAIL'; }
        current = null;
        currentKey = '';
        settingsWidgetMode = false;
        setTimeout(() => {
          if (settingsContentItems().length) {
            area = 'SETTINGS_CONTENT';
            firstItem(area);
            showBadge('EINSTELLUNGEN: ↑↓ NAVIGIEREN   OK ÄNDERN   ← MENÜ', 1500);
          }
        }, 140);
        return 'SETTINGS_OPEN';
      }

      if (area === 'SETTINGS_CONTENT') {
        const tag = (el.tagName || '').toLowerCase();
        const type = (el.getAttribute && el.getAttribute('type') || '').toLowerCase();
        try { el.focus({preventScroll:true}); } catch (_) {}
        if (tag === 'select') {
          settingsWidgetMode = true;
          showBadge('AUSWAHL: ↑↓ WERT   OK BESTÄTIGEN   ZURÜCK ABBRECHEN', 1400);
          return 'NATIVE_ENTER';
        }
        if (tag === 'input' && (type === 'text' || type === 'number' || type === 'password' || type === 'url')) {
          return 'FOCUS_INPUT';
        }
        try { el.click(); return 'SETTINGS_CLICK'; } catch (_) { return 'FAIL'; }
      }

      if (el.matches('.ft-list-video, .ft-list-channel, .ft-list-playlist, .ft-list-item')) {
        return activateCard(el);
      }

      const tag = (el.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || el.isContentEditable) {
        try { el.focus(); } catch (_) {}
        // The TopNav search is an FtInput component. Its own keydown handler
        // uses Enter to either accept the highlighted suggestion or execute the
        // current query. Sending native Enter preserves that exact FreeTube logic.
        if (isSearchInput(el)) return 'NATIVE_ENTER';
        return 'FOCUS_INPUT';
      }
      try { el.click(); return 'CLICK'; } catch (_) {}
      return 'FAIL';
    }

    function focusSearchForOsk() {
      const selectors = [
        '.topNav .searchInput input',
        '.topNav .searchContainer input',
        'input[placeholder*="Search"]',
        'input[placeholder*="Suche"]'
      ];
      let search = null;
      for (const sel of selectors) {
        search = Array.from(document.querySelectorAll(sel)).find(rendered);
        if (search) break;
      }
      if (!search) {
        const active = document.activeElement;
        if (active && rendered(active) && (active.matches('input,textarea') || active.isContentEditable)) search = active;
      }
      if (!search) return 'NO_INPUT';
      area = 'TOP';
      playerLayer = 'VIDEO';
      releaseForcedPlayerControls();
      current = search;
      currentKey = keyFor(search);
      try { search.focus(); search.select && search.select(); } catch (_) {}
      mark(search);
      showBadge('SUCHE   ↑↓ VORSCHLÄGE   OK SUCHEN / AUSWÄHLEN', 1500);
      return 'SEARCH_INPUT';
    }

    function back() {
      if (pickerOpen) {
        closePicker(false);
        return 'PICKER_CLOSE';
      }
      if (area === 'PLAYER') return playerBack();
      if (settingsWidgetMode) {
        settingsWidgetMode = false;
        return 'NATIVE_ESC';
      }
      if (isSettingsPage() && area === 'SETTINGS_CONTENT') {
        const returnButton = Array.from(document.querySelectorAll('.settingsPage .returnToMenuMobileButton')).find(rendered);
        if (returnButton) {
          try { returnButton.click(); } catch (_) {}
          area = 'SETTINGS_MENU';
          current = null;
          currentKey = '';
          setTimeout(() => { firstItem('SETTINGS_MENU'); showBadge('EINSTELLUNGS-MENÜ: ↑↓   OK ÖFFNEN', 1300); }, 100);
          return 'SETTINGS_MENU';
        }
        if (settingsMenuItems().length) return switchArea('SETTINGS_MENU', 'EINSTELLUNGS-MENÜ: ↑↓   OK ÖFFNEN');
      }
      return null;
    }

    function routeChanged() {
      if (location.href === lastUrl) return;
      lastUrl = location.href;
      clearTimeout(routeTimer);
      routeTimer = setTimeout(() => {
        current = null;
        currentKey = '';
        playerControlKey = '';
        playerLayer = 'VIDEO';
        settingsSectionKey = '';
        settingsWidgetMode = false;
        releaseForcedPlayerControls();
        chooseDefaultArea();
      }, 260);
    }

    document.addEventListener('fullscreenchange', () => {
      setTimeout(() => {
        ensureOverlay();
        renderPicker();
        paint();
      }, 25);
    });
    document.addEventListener('webkitfullscreenchange', () => {
      setTimeout(() => {
        ensureOverlay();
        renderPicker();
        paint();
      }, 25);
    });

    async function command(cmd) {
      routeChanged();
      if (cmd === 'MENU') {
        if (!pickerOpen) return openPicker();
        pickerMove(1);
        return 'PICKER_NEXT';
      }
      if (cmd === 'BACK') return back();
      if (cmd === 'UP' || cmd === 'DOWN' || cmd === 'LEFT' || cmd === 'RIGHT') return await move(cmd);
      if (cmd === 'SELECT') return activateCurrent();
      if (cmd === 'OSK_FOCUS') return focusSearchForOsk();
      if (cmd === 'RESET') { current=null; currentKey=''; playerControlKey=''; playerLayer='VIDEO'; settingsSectionKey=''; settingsWidgetMode=false; return chooseDefaultArea() ? 'RESET' : 'EMPTY'; }
      if (cmd === 'AREA') return area;
      if (cmd === 'PLAYER_STATUS') {
        const v = playerElement();
        return v ? {time:v.currentTime, paused:v.paused, readyState:v.readyState, width:v.videoWidth, height:v.videoHeight, layer:playerLayer} : null;
      }
      return 'UNKNOWN';
    }

    addEventListener('scroll', () => { if (current && !pickerOpen) paint(); }, true);
    addEventListener('resize', () => { if (current && !pickerOpen) paint(); });
    addEventListener('popstate', routeChanged);
    addEventListener('hashchange', routeChanged);
    setInterval(routeChanged, 350);

    setTimeout(() => chooseDefaultArea(), 120);
    return {command};
  })();
}
'''


# Shield Pi drives a PAL 720x576 CRT output.  FreeTube normally preserves the
# source aspect ratio and letterboxes 16:9 material.  The requested TV mode is
# an intentional full-frame stretch: no crop and no black bars.
FT_ASPECT_4_3_INSTALL = r'''(() => {
  const id = "shield-force-4x3";
  let style = document.getElementById(id);
  if (!style) {
    style = document.createElement("style");
    style.id = id;
    (document.head || document.documentElement).appendChild(style);
  }
  style.textContent = "video{width:100% !important;height:100% !important;object-fit:fill !important;}";
  const video = document.querySelector("video");
  const box = video ? video.getBoundingClientRect() : null;
  return {
    installed: Boolean(document.getElementById(id)),
    videos: document.querySelectorAll("video").length,
    videoBox: box ? [Math.round(box.width), Math.round(box.height)] : null,
    objectFit: video ? getComputedStyle(video).objectFit : null,
  };
})()'''


class ShieldRemote:
    def __init__(self, config_path, no_grab=False, verbose=False):
        self.config_path = Path(config_path)
        self.no_grab = no_grab
        self.verbose = verbose
        self.config = self._load_config()
        self.double_home = float(self.config.get('double_home_ms', 380)) / 1000.0
        self.ft_port = int(self.config.get('freetube_debug_port', 9222))
        self.last_home_press = 0.0
        self.last_profile_check = 0.0
        self.cached_active = ''
        self.cached_profile = 'generic'
        self.vlc_menu_active = False
        self.vlc_ui_mode = False
        self.vlc_dialog_expected_until = 0.0

        # Application-specific long-press handling.  We deliberately keep this
        # in the single physical-remote daemon so Kodi and Shield VLC never
        # receive duplicate short/long actions from the same OK/Netflix press.
        self.kodi_select_down = None
        self.kodi_select_long_sent = False
        self.kodi_select_hold = 0.65
        self.kodi_select_timer = None
        self.kodi_select_token = 0
        self.shieldvlc_select_down = None
        self.shieldvlc_select_long_sent = False
        self.shieldvlc_select_hold = 0.65
        self.shieldvlc_select_timer = None
        self.shieldvlc_select_token = 0

        self._cdp = None
        self._cdp_id = 0
        self._cdp_last_error = 0.0
        self.cdp_lock = threading.RLock()
        self.media_lock = threading.RLock()
        self.kodi_paused_players = []
        self.mpris_paused_by_class = {}
        self.media_control_socket = None
        self.media_control_thread = None
        self.freetube_aspect_thread = None
        self.media_control_stop = threading.Event()
        self.ui_lock = threading.Lock()
        self.ui = UInput(
            {ecodes.EV_KEY: OUTPUT_KEYS},
            name='Shield Pi Remote',
            bustype=ecodes.BUS_USB,
            vendor=0x0955,
            product=0x0001,
            version=11,
        )

    def log(self, text):
        if self.verbose:
            print(text, flush=True)

    def _load_config(self):
        try:
            with self.config_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f'Fehler beim Laden von {self.config_path}: {e}', file=sys.stderr)
            raise SystemExit(2)

    def find_remote(self):
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
            except Exception:
                continue
            name = (dev.name or '').strip()
            phys = (dev.phys or '').lower()
            if name == REMOTE_NAME and 'uinput' not in phys and 'input-remapper' not in name.lower():
                return dev
            try:
                dev.close()
            except Exception:
                pass
        return None

    def active_window(self):
        now = time.monotonic()
        if now - self.last_profile_check < 0.10:
            return self.cached_active
        self.last_profile_check = now
        env = os.environ.copy()
        env.setdefault('XDG_RUNTIME_DIR', str(RUNTIME_DIR))
        env.setdefault('WAYLAND_DISPLAY', 'wayland-0')
        try:
            r = subprocess.run(
                ['wlrctl', 'toplevel', 'list', 'state:active'],
                env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=0.35,
            )
            self.cached_active = next((x.strip() for x in r.stdout.splitlines() if x.strip()), '')
        except Exception:
            self.cached_active = ''
        return self.cached_active

    def shieldvlc_window_active(self):
        """Treat libVLC/XWayland child windows as part of Shield VLC.

        The embedded libVLC video surface can temporarily expose a generic
        'vlc' app-id/title when focus changes to the player controls.  Without
        this guard the daemon falls into the old desktop-VLC profile, where
        LEFT/RIGHT are seek hotkeys.  While the Shield VLC control socket is
        alive, any foreground VLC-looking child belongs to our TV frontend.
        """
        if not SHIELD_VLC_CONTROL_SOCKET.exists():
            return False
        active = (self.active_window() or '').lower()
        if any(token in active for token in (
            'shield-vlc.py', 'shield vlc tv', 'shield-vlc',
            'org.videolan.vlc', 'vlc media player', 'vlc'
        )):
            return True
        return False

    def profile_for_active_window(self):
        active = self.active_window().lower()
        if self.shieldvlc_window_active():
            if self.cached_profile != 'shieldvlc':
                self.log(f'Shield VLC Fokus erzwungen fuer active={active!r}')
            self.cached_profile = 'shieldvlc'
            return 'shieldvlc'
        profiles = self.config.get('profiles', {})
        for name, spec in profiles.items():
            if name == 'generic':
                continue
            for token in spec.get('match', []):
                if str(token).lower() in active:
                    if self.cached_profile == 'vlc' and name != 'vlc':
                        self.vlc_menu_active = False
                        self.vlc_ui_mode = False
                        self.vlc_dialog_expected_until = 0.0
                    self.cached_profile = name
                    return name
        if self.cached_profile == 'vlc':
            self.vlc_menu_active = False
            self.vlc_ui_mode = False
            self.vlc_dialog_expected_until = 0.0
        self.cached_profile = 'generic'
        return 'generic'

    def launcher_pid(self):
        try:
            r = subprocess.run(
                ['pgrep', '-u', 'shield', '-f', LAUNCHER_PATTERN],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=0.5,
            )
            pids = [int(x) for x in r.stdout.split() if x.isdigit()]
            return pids[-1] if pids else None
        except Exception:
            return None

    def signal_launcher(self, sig):
        pid = self.launcher_pid()
        if not pid:
            self.log('Launcher-Prozess nicht gefunden')
            return False
        try:
            os.kill(pid, sig)
            return True
        except Exception as e:
            self.log(f'Signal an Launcher fehlgeschlagen: {e}')
            return False

    def send_launcher_control(self, command):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            sock.settimeout(0.15)
            sock.sendto(command.encode('utf-8'), str(CONTROL_SOCKET))
            return True
        except Exception as e:
            self.log(f'Launcher-Control {command!r} fehlgeschlagen: {e}')
            return False
        finally:
            sock.close()

    def send_shieldvlc_control(self, command):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            sock.sendto(command.encode('utf-8'), str(SHIELD_VLC_CONTROL_SOCKET))
            return True
        except Exception as e:
            self.log(f'Shield VLC IPC fehlgeschlagen ({command}): {e}')
            return False
        finally:
            try:
                sock.close()
            except Exception:
                pass

    # --------------------------------------------------------------
    # Launcher <-> media lifecycle control.
    # --------------------------------------------------------------
    def _start_media_control_socket(self):
        try:
            RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
            try:
                REMOTE_CONTROL_SOCKET.unlink()
            except FileNotFoundError:
                pass
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            sock.bind(str(REMOTE_CONTROL_SOCKET))
            os.chmod(REMOTE_CONTROL_SOCKET, 0o600)
            sock.settimeout(0.5)
            self.media_control_socket = sock
            self.media_control_stop.clear()
            self.media_control_thread = threading.Thread(
                target=self._media_control_loop,
                name='shield-media-control',
                daemon=True,
            )
            self.media_control_thread.start()
            self.freetube_aspect_thread = threading.Thread(
                target=self._freetube_aspect_guard_loop,
                name='shield-freetube-4x3',
                daemon=True,
            )
            self.freetube_aspect_thread.start()
            print(f'Shield Mediensteuerung bereit: {REMOTE_CONTROL_SOCKET}', flush=True)
        except Exception as e:
            print(f'Shield Mediensteuerung Fehler: {e}', file=sys.stderr, flush=True)
            self.media_control_socket = None

    def _stop_media_control_socket(self):
        self.media_control_stop.set()
        sock = self.media_control_socket
        self.media_control_socket = None
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass
        aspect_thread = self.freetube_aspect_thread
        self.freetube_aspect_thread = None
        if aspect_thread is not None and aspect_thread is not threading.current_thread():
            aspect_thread.join(timeout=1.0)
        try:
            REMOTE_CONTROL_SOCKET.unlink()
        except FileNotFoundError:
            pass
        except Exception:
            pass

    def _media_control_loop(self):
        while not self.media_control_stop.is_set():
            sock = self.media_control_socket
            if sock is None:
                return
            try:
                raw = sock.recv(2048)
            except socket.timeout:
                continue
            except OSError:
                return
            except Exception as e:
                print(f'Shield Mediensteuerung Empfangsfehler: {e}', flush=True)
                continue
            command = raw.decode('utf-8', errors='ignore').strip()
            try:
                payload = json.loads(command)
            except (TypeError, ValueError):
                payload = None
            if isinstance(payload, dict):
                action = str(payload.get('action') or '')
                app_class = str(payload.get('app_class') or '')
                backend = str(payload.get('backend') or '')
                match_hint = str(payload.get('match') or '')
                if action == 'pause':
                    self.pause_media_for_class(app_class, backend, match_hint)
                elif action == 'resume':
                    self.resume_media_for_class(app_class, backend, match_hint)
            elif command.startswith('media_pause:'):
                self.pause_media_for_class(command.split(':', 1)[1])
            elif command.startswith('media_resume:'):
                self.resume_media_for_class(command.split(':', 1)[1])

    @staticmethod
    def _media_profile_for_class(app_class):
        return {
            'shield-vlc': 'shieldvlc',
            'vlc': 'vlc',
            'freetube': 'freetube',
            'kodi': 'kodi',
        }.get((app_class or '').strip().lower())

    def pause_media_for_class(self, app_class, backend='', match_hint=''):
        profile = (backend or self._media_profile_for_class(app_class) or 'mpris').lower()
        if profile == 'ignore':
            return False
        with self.media_lock:
            if profile == 'shieldvlc':
                return self.send_shieldvlc_control('launcher_pause')
            if profile == 'freetube':
                direct = self._freetube_launcher_pause()
                return self._mpris_launcher_pause(app_class, profile, match_hint) or direct
            if profile == 'kodi':
                direct = self._kodi_launcher_pause()
                return self._mpris_launcher_pause(app_class, profile, match_hint) or direct
            return self._mpris_launcher_pause(app_class, profile, match_hint)

    def resume_media_for_class(self, app_class, backend='', match_hint=''):
        profile = (backend or self._media_profile_for_class(app_class) or 'mpris').lower()
        if profile == 'ignore':
            return False
        with self.media_lock:
            if profile == 'shieldvlc':
                return self.send_shieldvlc_control('launcher_resume')
            if profile == 'freetube':
                direct = self._freetube_launcher_resume()
                return self._mpris_launcher_resume(app_class) or direct
            if profile == 'kodi':
                direct = self._kodi_launcher_resume()
                return self._mpris_launcher_resume(app_class) or direct
            return self._mpris_launcher_resume(app_class)

    @staticmethod
    def _media_tokens(value):
        ignored = {
            'app', 'application', 'desktop', 'instance', 'media', 'mpris',
            'org', 'player', 'service',
        }
        return {
            token for token in re.split(r'[^a-z0-9]+', (value or '').lower())
            if len(token) >= 3 and token not in ignored
        }

    def _mpris_bus(self):
        if dbus is None:
            return None
        address = os.environ.get(
            'DBUS_SESSION_BUS_ADDRESS',
            f'unix:path={RUNTIME_DIR / "bus"}',
        )
        try:
            return dbus.bus.BusConnection(address)
        except Exception as e:
            self.log(f'MPRIS Session-Bus nicht erreichbar: {e}')
            return None

    def _mpris_sessions(self, bus):
        sessions = []
        if bus is None:
            return sessions
        try:
            names = bus.list_names()
        except Exception as e:
            self.log(f'MPRIS Namensliste fehlgeschlagen: {e}')
            return sessions
        for name in names:
            name = str(name)
            if not name.startswith('org.mpris.MediaPlayer2.'):
                continue
            try:
                obj = bus.get_object(name, '/org/mpris/MediaPlayer2')
                props = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
                status = str(props.Get('org.mpris.MediaPlayer2.Player', 'PlaybackStatus'))
                try:
                    identity = str(props.Get('org.mpris.MediaPlayer2', 'Identity'))
                except Exception:
                    identity = ''
                try:
                    desktop_entry = str(props.Get('org.mpris.MediaPlayer2', 'DesktopEntry'))
                except Exception:
                    desktop_entry = ''
                sessions.append({
                    'name': name,
                    'status': status,
                    'identity': identity,
                    'desktop_entry': desktop_entry,
                })
            except Exception:
                continue
        return sessions

    def _mpris_matches(self, session, app_class, backend, match_hint):
        description = ' '.join((
            session.get('name', ''),
            session.get('identity', ''),
            session.get('desktop_entry', ''),
        )).lower()
        backend = (backend or '').lower()
        if backend == 'chromium':
            return any(x in description for x in ('chromium', 'chrome'))
        if backend == 'firefox':
            return 'firefox' in description
        if backend == 'vlc':
            return 'vlc' in description
        if backend == 'kodi':
            return 'kodi' in description
        if backend == 'freetube':
            return 'freetube' in description
        wanted = self._media_tokens(f'{app_class} {match_hint}')
        present = self._media_tokens(description)
        return bool(wanted & present)

    def _mpris_launcher_pause(self, app_class, backend, match_hint):
        key = (app_class or '').strip().lower()
        if not key:
            return False
        if self.mpris_paused_by_class.get(key):
            return True
        bus = self._mpris_bus()
        paused = []
        for session in self._mpris_sessions(bus):
            if session.get('status') != 'Playing':
                continue
            if not self._mpris_matches(session, app_class, backend, match_hint):
                continue
            try:
                obj = bus.get_object(session['name'], '/org/mpris/MediaPlayer2')
                player = dbus.Interface(obj, 'org.mpris.MediaPlayer2.Player')
                player.Pause()
                paused.append(session['name'])
            except Exception as e:
                self.log(f'MPRIS Pause {session.get("name")} fehlgeschlagen: {e}')
        if paused:
            self.mpris_paused_by_class[key] = paused
        self.log(f'MPRIS Launcher-Pause class={app_class!r} -> {paused}')
        return bool(paused)

    def _mpris_launcher_resume(self, app_class):
        key = (app_class or '').strip().lower()
        names = list(self.mpris_paused_by_class.get(key) or [])
        if not names:
            return False
        bus = self._mpris_bus()
        handled = []
        for name in names:
            try:
                obj = bus.get_object(name, '/org/mpris/MediaPlayer2')
                props = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
                status = str(props.Get('org.mpris.MediaPlayer2.Player', 'PlaybackStatus'))
                if status == 'Paused':
                    player = dbus.Interface(obj, 'org.mpris.MediaPlayer2.Player')
                    player.Play()
                # Playing means somebody already resumed it; Stopped must never
                # be started automatically.  In both cases ownership is done.
                handled.append(name)
            except Exception as e:
                self.log(f'MPRIS Resume {name} fehlgeschlagen: {e}')
        if handled:
            remaining = [name for name in names if name not in handled]
            if remaining:
                self.mpris_paused_by_class[key] = remaining
            else:
                self.mpris_paused_by_class.pop(key, None)
        self.log(f'MPRIS Launcher-Resume class={app_class!r} -> {handled}')
        return bool(handled)

    def _freetube_launcher_pause(self):
        expression = r'''(function(){
          if (window.__shieldPausedByLauncher && window.__shieldPausedVideo) {
            return {paused:true, owned:true, time:window.__shieldPausedVideo.currentTime};
          }
          const videos = Array.from(document.querySelectorAll('video'));
          const video = videos.find(v => !v.paused && !v.ended);
          if (!video) return {paused:false, owned:false};
          video.pause();
          window.__shieldPausedByLauncher = true;
          window.__shieldPausedVideo = video;
          return {paused:video.paused, owned:true, time:video.currentTime};
        })()'''
        result = self._cdp_eval(expression)
        self.log(f'FreeTube Launcher-Pause -> {result}')
        return bool(isinstance(result, dict) and result.get('owned'))

    def _freetube_launcher_resume(self):
        expression = r'''(async function(){
          if (!window.__shieldPausedByLauncher) return {resumed:false, owned:false};
          const video = window.__shieldPausedVideo;
          if (!video || !video.isConnected) return {resumed:false, owned:true};
          try {
            await video.play();
            window.__shieldPausedByLauncher = false;
            window.__shieldPausedVideo = null;
            return {resumed:true, owned:false, time:video.currentTime};
          } catch (error) {
            return {resumed:false, owned:true, error:String(error)};
          }
        })()'''
        result = self._cdp_eval(expression)
        self.log(f'FreeTube Launcher-Resume -> {result}')
        return bool(isinstance(result, dict) and result.get('resumed'))

    def _kodi_rpc(self, method, params=None):
        request = {
            'jsonrpc': '2.0',
            'id': int(time.monotonic() * 1000) & 0x7fffffff,
            'method': method,
        }
        if params is not None:
            request['params'] = params
        try:
            with socket.create_connection(('127.0.0.1', 9090), timeout=0.35) as sock:
                sock.settimeout(0.35)
                sock.sendall((json.dumps(request) + '\n').encode('utf-8'))
                data = b''
                deadline = time.monotonic() + 0.7
                while time.monotonic() < deadline:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                    try:
                        return json.loads(data.decode('utf-8'))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            self.log(f'Kodi JSON-RPC {method} fehlgeschlagen: {e}')
        return None

    def _kodi_launcher_pause(self):
        # A second Home press opens the task manager.  Keep ownership of the
        # pause established by the first press instead of reclassifying it as
        # a user pause.
        if self.kodi_paused_players:
            return True
        response = self._kodi_rpc('Player.GetActivePlayers') or {}
        players = response.get('result') or []
        paused = []
        for player in players:
            player_id = player.get('playerid')
            if player_id is None or player.get('type') not in ('audio', 'video'):
                continue
            props = self._kodi_rpc(
                'Player.GetProperties',
                {'playerid': player_id, 'properties': ['speed']},
            ) or {}
            speed = ((props.get('result') or {}).get('speed') or 0)
            if speed > 0:
                changed = self._kodi_rpc(
                    'Player.PlayPause',
                    {'playerid': player_id, 'play': False},
                )
                if changed and 'error' not in changed:
                    paused.append(player_id)
        self.kodi_paused_players = paused
        self.log(f'Kodi Launcher-Pause -> {paused}')
        return bool(paused)

    def _kodi_launcher_resume(self):
        paused = list(self.kodi_paused_players)
        if not paused:
            return False
        resumed = []
        for player_id in paused:
            changed = self._kodi_rpc(
                'Player.PlayPause',
                {'playerid': player_id, 'play': True},
            )
            if changed and 'error' not in changed:
                resumed.append(player_id)
        if resumed:
            self.kodi_paused_players = [x for x in paused if x not in resumed]
        self.log(f'Kodi Launcher-Resume -> {resumed}')
        return bool(resumed)

    def osk_visible(self):
        return OSK_MARKER.exists()

    def show_osk(self):
        return self.send_launcher_control('osk_show')

    def close_osk(self):
        if self.osk_visible():
            self.send_launcher_control('osk_close')

    def toggle_osk(self, profile_name):
        if self.osk_visible():
            self.close_osk()
            return
        if profile_name == 'freetube':
            self.freetube_command('OSK_FOCUS')
            time.sleep(0.03)
        elif profile_name == 'browser':
            self.emit_combo([ecodes.KEY_LEFTCTRL], ecodes.KEY_L)
            time.sleep(0.03)
        self.show_osk()

    def handle_home(self):
        self.close_osk()
        self.vlc_menu_active = False
        self.vlc_ui_mode = False
        self.vlc_dialog_expected_until = 0.0
        now = time.monotonic()
        if self.last_home_press and (now - self.last_home_press) <= self.double_home:
            self.last_home_press = 0.0
            self.log('HOME x2 -> Taskmanager')
            self.signal_launcher(signal.SIGUSR2)
        else:
            self.last_home_press = now
            self.log('HOME -> Launcher')
            self.signal_launcher(signal.SIGUSR1)

    def vlc_active_text(self):
        return (self.active_window() or '').lower()

    def vlc_native_file_dialog_likely(self):
        """True for the actual Qt file/folder chooser, not VLC's Open Media tabs.

        In this chooser BACK should move one directory up and NETFLIX remains a
        safe cancel key.  MENU is still available as normal Qt focus traversal.
        """
        active = self.vlc_active_text()
        markers = (
            'open file', 'datei öffnen', 'datei oeffnen',
            'select file', 'datei auswählen', 'datei auswaehlen',
            'choose file', 'open directory', 'ordner öffnen', 'ordner oeffnen',
            'select directory', 'ordner auswählen', 'ordner auswaehlen',
            'qfiledialog', 'file dialog',
        )
        # Do not mistake VLC's own multi-tab Open Media window for QFileDialog.
        if 'open media' in active or 'medien öffnen' in active or 'medien oeffnen' in active:
            return False
        return any(m in active for m in markers)

    def vlc_tabbed_dialog_likely(self):
        """Detect VLC auxiliary windows that contain Qt tabs/categories.

        Open Media is a QTabWidget (File/Disc/Network/Capture).  Media info,
        effects and preferences also expose tab/category style navigation.
        NETFLIX therefore becomes the coarse next-register key in these windows.
        """
        active = self.vlc_active_text()
        markers = (
            'open media', 'medien öffnen', 'medien oeffnen',
            'preferences', 'simple preferences', 'einstellungen',
            'adjustments and effects', 'effects and filters',
            'anpassungen und effekte', 'effekte und filter',
            'media information', 'medieninformationen', 'medien-informationen',
            'codec information', 'codec-informationen', 'codecinformationen',
            'track synchronization', 'spursynchronisierung',
            'bookmarks', 'lesezeichen',
            'messages', 'meldungen',
            'plugins and extensions', 'plugins und erweiterungen',
            'vlm configurator', 'vlm-konfiguration',
        )
        return any(m in active for m in markers)

    def vlc_aux_dialog_likely(self):
        if self.vlc_native_file_dialog_likely() or self.vlc_tabbed_dialog_likely():
            return True
        # Short grace period immediately after a menu command catches localized
        # or uncommon VLC dialog titles until the toplevel title is refreshed.
        return time.monotonic() <= self.vlc_dialog_expected_until

    def vlc_dialog_likely(self):
        # Compatibility name used by the existing V10 state machine.
        return self.vlc_aux_dialog_likely()

    def activate_vlc_menubar(self):
        """Enter VLC UI mode and activate its Qt menu bar with a real Alt tap.

        F10 must not be emitted because the existing Shield/labwc setup uses
        that path for launcher control.  UI mode remains active after a menu
        item is chosen, which is crucial for QFileDialog: SELECT must stay
        Enter there instead of reverting to the player's Space shortcut.
        """
        self.vlc_ui_mode = True
        if not self.vlc_menu_active:
            self.emit_simple(ecodes.KEY_LEFTALT, 1)
            time.sleep(0.045)
            self.emit_simple(ecodes.KEY_LEFTALT, 0)
            self.vlc_menu_active = True
            self.log('VLC NETFLIX/VIDEO -> UI-Modus + Menueleiste (Alt)')
        else:
            self.tap(ecodes.KEY_RIGHT)
            self.log('VLC NETFLIX/VIDEO -> naechstes Hauptmenue')

    def emit_simple(self, keycode, value):
        with self.ui_lock:
            self.ui.write(ecodes.EV_KEY, keycode, value)
            self.ui.syn()

    def tap(self, keycode):
        with self.ui_lock:
            self.ui.write(ecodes.EV_KEY, keycode, 1)
            self.ui.syn()
            self.ui.write(ecodes.EV_KEY, keycode, 0)
            self.ui.syn()

    def emit_combo(self, modifiers, keycode):
        with self.ui_lock:
            for mod in modifiers:
                self.ui.write(ecodes.EV_KEY, mod, 1)
            self.ui.write(ecodes.EV_KEY, keycode, 1)
            self.ui.syn()
            self.ui.write(ecodes.EV_KEY, keycode, 0)
            for mod in reversed(modifiers):
                self.ui.write(ecodes.EV_KEY, mod, 0)
            self.ui.syn()

    # --------------------------------------------------------------
    # FreeTube: renderer-level spatial navigation via local CDP.
    # --------------------------------------------------------------
    def _cdp_close(self):
        with self.cdp_lock:
            if self._cdp is not None:
                try:
                    self._cdp.close()
                except Exception:
                    pass
            self._cdp = None

    def _cdp_error(self, text):
        now = time.monotonic()
        if now - self._cdp_last_error > 4.0:
            print('FreeTube-Navigation:', text, flush=True)
            self._cdp_last_error = now

    def _cdp_connect(self, quiet=False):
        if websocket is None:
            if not quiet:
                self._cdp_error('python3-websocket fehlt')
            return False
        if self._cdp is not None:
            return True
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{self.ft_port}/json', timeout=0.25) as r:
                targets = json.loads(r.read().decode('utf-8', errors='replace'))
            pages = [t for t in targets if t.get('type') == 'page' and t.get('webSocketDebuggerUrl')]
            if not pages:
                if not quiet:
                    self._cdp_error('kein FreeTube-Renderer auf Debug-Port gefunden')
                return False
            pages.sort(key=lambda t: ('freetube' not in ((t.get('title') or '') + ' ' + (t.get('url') or '')).lower(),))
            url = pages[0]['webSocketDebuggerUrl']
            self._cdp = websocket.create_connection(
                url,
                timeout=0.30,
                origin=f'http://127.0.0.1:{self.ft_port}',
            )
            return True
        except Exception as e:
            self._cdp_close()
            if not quiet:
                self._cdp_error(str(e))
            return False

    def _cdp_eval(self, expression, quiet=False):
        with self.cdp_lock:
            if not self._cdp_connect(quiet=quiet):
                return None
            self._cdp_id += 1
            msg_id = self._cdp_id
            payload = {
                'id': msg_id,
                'method': 'Runtime.evaluate',
                'params': {
                    'expression': expression,
                    'returnByValue': True,
                    'awaitPromise': True,
                },
            }
            try:
                self._cdp.send(json.dumps(payload))
                deadline = time.monotonic() + 0.45
                while time.monotonic() < deadline:
                    raw = self._cdp.recv()
                    obj = json.loads(raw)
                    if obj.get('id') != msg_id:
                        continue
                    if 'error' in obj:
                        raise RuntimeError(obj['error'])
                    return (((obj.get('result') or {}).get('result') or {}).get('value'))
            except Exception as e:
                self._cdp_close()
                if not quiet:
                    self._cdp_error(str(e))
            return None

    def _freetube_aspect_guard_loop(self):
        while not self.media_control_stop.is_set():
            result = self._cdp_eval(FT_ASPECT_4_3_INSTALL, quiet=True)
            if isinstance(result, dict) and result.get('installed'):
                self.log(f'FreeTube 4:3-Streckung -> {result}')
            self.media_control_stop.wait(2.0)

    def freetube_command(self, command):
        expression = '(function(){' + FT_NAV_INSTALL + ';return window.__shieldNavV8.command(' + json.dumps(command) + ');})()'
        result = self._cdp_eval(expression)
        self.log(f'FreeTube {command} -> {result}')
        return result

    def freetube_fallback(self, physical_name, value):
        if physical_name in ('UP','LEFT'):
            if value == 1:
                self.emit_combo([ecodes.KEY_LEFTSHIFT], ecodes.KEY_TAB)
        elif physical_name in ('DOWN','RIGHT'):
            if value == 1:
                self.tap(ecodes.KEY_TAB)
        elif physical_name == 'SELECT' and value == 1:
            self.tap(ecodes.KEY_ENTER)
        elif physical_name == 'BACK' and value == 1:
            self.emit_combo([ecodes.KEY_LEFTALT], ecodes.KEY_LEFT)

    def handle_freetube(self, physical_name, value):
        if physical_name == 'PLAYPAUSE':
            self.emit_simple(ecodes.KEY_SPACE, value)
            return
        if physical_name in ('VOLUMEUP','VOLUMEDOWN'):
            self.emit_simple(ecodes.KEY_VOLUMEUP if physical_name == 'VOLUMEUP' else ecodes.KEY_VOLUMEDOWN, value)
            return
        if physical_name == 'BACK':
            if value == 1:
                # V8 consumes BACK while a FreeTube sub-navigation layer needs it.
                # Otherwise preserve FreeTube's documented Alt+Left history action.
                result = self.freetube_command('BACK')
                if result == 'NATIVE_ESC':
                    self.tap(ecodes.KEY_ESC)
                elif result is None:
                    self.emit_combo([ecodes.KEY_LEFTALT], ecodes.KEY_LEFT)
            return
        if physical_name in ('MENU','SELECT','UP','DOWN','LEFT','RIGHT'):
            if value not in (1,2) or (physical_name in ('MENU','SELECT') and value != 1):
                return
            result = self.freetube_command(physical_name)
            if isinstance(result, str) and result.startswith('NATIVE_'):
                native = result[7:]
                keymap = {
                    'UP': ecodes.KEY_UP,
                    'DOWN': ecodes.KEY_DOWN,
                    'LEFT': ecodes.KEY_LEFT,
                    'RIGHT': ecodes.KEY_RIGHT,
                    'SPACE': ecodes.KEY_SPACE,
                    'ENTER': ecodes.KEY_ENTER,
                    'ESC': ecodes.KEY_ESC,
                }
                keycode = keymap.get(native)
                if keycode is not None:
                    # Tap on every physical press/repeat so no virtual key can
                    # remain held when switching between DOM and player mode.
                    self.tap(keycode)
                    return
            if result is not None:
                return
            self.freetube_fallback(physical_name, value)
            return

    # --------------------------------------------------------------
    # VLC: Netflix/VIDEO chooses the coarse Qt menu bar.
    # MENU is deliberately swallowed in VLC because the older Shield/labwc
    # setup associates the F10 path with returning to the launcher.
    # --------------------------------------------------------------
    def handle_vlc(self, physical_name, value):
        # Hardware volume and Play/Pause always stay directly available.
        if physical_name in ('VOLUMEUP','VOLUMEDOWN'):
            self.emit_simple(ecodes.KEY_VOLUMEUP if physical_name == 'VOLUMEUP' else ecodes.KEY_VOLUMEDOWN, value)
            return
        if physical_name == 'PLAYPAUSE':
            self.emit_simple(ecodes.KEY_SPACE, value)
            return

        # MENU is VLC's fine-navigation key.  It never emits F10.  V12 makes
        # it context-sensitive: in a QFileDialog it walks one focus zone BACK,
        # which is much more useful on a remote than another forward-only Tab.
        # In VLC's own tabbed dialogs it advances to the next control inside the
        # currently selected register.
        if physical_name == 'MENU':
            if value == 1:
                if self.vlc_native_file_dialog_likely() and self.vlc_ui_mode and not self.vlc_menu_active:
                    self.emit_combo([ecodes.KEY_LEFTSHIFT], ecodes.KEY_TAB)
                    self.log('VLC MENU -> vorheriger Dateidialog-Bereich (Shift+Tab)')
                elif self.vlc_ui_mode or self.vlc_aux_dialog_likely():
                    self.vlc_ui_mode = True
                    self.tap(ecodes.KEY_TAB)
                    self.log('VLC MENU -> naechstes Bedienelement (Tab)')
                else:
                    self.log('VLC MENU im Player ignoriert; NETFLIX oeffnet VLC-UI')
            return

        # Netflix/VIDEO is the coarse VLC navigation key.
        # - Main player: open/advance the Qt menu bar.
        # - VLC tab dialogs: choose the next register AND immediately move focus
        #   into that register, so D-pad/OK are usable straight away.
        # - QFileDialog/Open Directory: move to the next major focus zone rather
        #   than cancelling the chooser.  Once a list/tree/sidebar has focus,
        #   the four arrows are passed through natively.
        if physical_name == 'VIDEO':
            if value != 1:
                return
            if self.vlc_native_file_dialog_likely() and self.vlc_ui_mode and not self.vlc_menu_active:
                self.tap(ecodes.KEY_TAB)
                self.log('VLC NETFLIX/VIDEO -> naechster Dateidialog-Bereich (Tab)')
            elif self.vlc_tabbed_dialog_likely() and self.vlc_ui_mode and not self.vlc_menu_active:
                self.emit_combo([ecodes.KEY_LEFTCTRL], ecodes.KEY_TAB)
                time.sleep(0.055)
                self.tap(ecodes.KEY_TAB)
                self.log('VLC NETFLIX/VIDEO -> naechstes Register + in Inhalt wechseln')
            else:
                self.activate_vlc_menubar()
            return

        # UI mode deliberately survives selecting a menu command.  That fixes
        # the previous bug where OK became Space inside the file chooser.
        if self.vlc_ui_mode:
            if physical_name == 'UP':
                self.emit_simple(ecodes.KEY_UP, value)
            elif physical_name == 'DOWN':
                self.emit_simple(ecodes.KEY_DOWN, value)
            elif physical_name == 'LEFT':
                self.emit_simple(ecodes.KEY_LEFT, value)
            elif physical_name == 'RIGHT':
                self.emit_simple(ecodes.KEY_RIGHT, value)
            elif physical_name == 'SELECT':
                if value == 1:
                    self.tap(ecodes.KEY_ENTER)
                    # A chosen top-level/menu entry may open QFileDialog or
                    # another modal window.  Keep UI mode and remember a short
                    # grace period so Back can behave like folder-back there.
                    if self.vlc_menu_active:
                        self.vlc_dialog_expected_until = time.monotonic() + 3.0
                    self.vlc_menu_active = False
                    self.log('VLC UI OK -> Enter (UI-Modus bleibt aktiv)')
            elif physical_name == 'BACK':
                if value == 1:
                    if self.vlc_menu_active:
                        self.tap(ecodes.KEY_ESC)
                        self.vlc_menu_active = False
                        self.log('VLC ZURUECK -> Menue schliessen')
                    elif self.vlc_native_file_dialog_likely():
                        # In QFileDialog Backspace walks one directory upward.
                        self.tap(ecodes.KEY_BACKSPACE)
                        self.log('VLC ZURUECK -> ein Ordner zurueck')
                    elif self.vlc_tabbed_dialog_likely():
                        # V12 deliberately does NOT close a deep VLC dialog here.
                        # BACK means one navigation step backwards.  The user can
                        # still reach Close/Cancel with the D-pad and confirm it
                        # with OK, without losing the whole branch unexpectedly.
                        self.emit_combo([ecodes.KEY_LEFTSHIFT], ecodes.KEY_TAB)
                        self.log('VLC ZURUECK -> vorheriges Bedienelement im Unterfenster')
                    elif self.vlc_dialog_likely():
                        self.emit_combo([ecodes.KEY_LEFTSHIFT], ecodes.KEY_TAB)
                        self.log('VLC ZURUECK -> vorheriges Bedienelement (Shift+Tab)')
                    else:
                        # No blind Escape here: on the main VLC window Escape
                        # can have global effects.  Just return to player mode.
                        self.vlc_ui_mode = False
                        self.vlc_dialog_expected_until = 0.0
                        self.log('VLC ZURUECK -> Player-Modus (kein Escape)')
            return

        # Player mode: direct playback controls.
        if physical_name == 'UP':
            if value == 1:
                self.emit_combo([ecodes.KEY_LEFTCTRL], ecodes.KEY_UP)
        elif physical_name == 'DOWN':
            if value == 1:
                self.emit_combo([ecodes.KEY_LEFTCTRL], ecodes.KEY_DOWN)
        elif physical_name == 'LEFT':
            if value == 1:
                self.emit_combo([ecodes.KEY_LEFTSHIFT], ecodes.KEY_LEFT)
        elif physical_name == 'RIGHT':
            if value == 1:
                self.emit_combo([ecodes.KEY_LEFTSHIFT], ecodes.KEY_RIGHT)
        elif physical_name == 'SELECT':
            if value == 1:
                self.tap(ecodes.KEY_SPACE)
        elif physical_name == 'BACK':
            # Do not send Escape from player mode.  The previous behavior could
            # dismiss/close VLC and throw the user back to the launcher.
            if value == 1:
                self.log('VLC ZURUECK im Player-Modus ignoriert')

    def _cancel_shieldvlc_select_timer(self):
        timer = self.shieldvlc_select_timer
        self.shieldvlc_select_timer = None
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                pass

    def _shieldvlc_long_ok_fire(self, token):
        if (
            self.shieldvlc_select_down is not None
            and token == self.shieldvlc_select_token
            and not self.shieldvlc_select_long_sent
        ):
            self.shieldvlc_select_long_sent = True
            self.send_shieldvlc_control('select_long')
            self.log('Shield VLC OK lang -> Ordner-Wiedergabeliste')

    def handle_shieldvlc(self, physical_name, value):
        """Direct control for our TV-first libVLC frontend.

        Physical transport keys are dedicated to shuttle seek:
          REWIND      -> reverse x2/x4/x8/x16/x32
          FASTFORWARD -> forward x2/x4/x8/x16/x32

        SELECT is handled by Shield VLC itself: while shuttling it resumes
        normal playback; otherwise it opens/uses the Shield player controls.
        MENU and NETFLIX stay deliberately free in Shield VLC.
        """
        if physical_name in ('VOLUMEUP', 'VOLUMEDOWN'):
            code = ecodes.KEY_VOLUMEUP if physical_name == 'VOLUMEUP' else ecodes.KEY_VOLUMEDOWN
            self.emit_simple(code, value)
            return

        if physical_name == 'SELECT':
            now = time.monotonic()
            if value == 1:
                self._cancel_shieldvlc_select_timer()
                self.shieldvlc_select_down = now
                self.shieldvlc_select_long_sent = False
                self.shieldvlc_select_token += 1
                token = self.shieldvlc_select_token
                timer = threading.Timer(
                    self.shieldvlc_select_hold,
                    self._shieldvlc_long_ok_fire,
                    args=(token,),
                )
                timer.daemon = True
                self.shieldvlc_select_timer = timer
                timer.start()
                return
            if value == 2:
                return
            if value == 0:
                started = self.shieldvlc_select_down
                long_sent = self.shieldvlc_select_long_sent
                self._cancel_shieldvlc_select_timer()
                self.shieldvlc_select_down = None
                self.shieldvlc_select_long_sent = False
                self.shieldvlc_select_token += 1
                if started is None or long_sent:
                    return
                if now - started >= self.shieldvlc_select_hold:
                    self.send_shieldvlc_control('select_long')
                else:
                    self.send_shieldvlc_control('select')
                return

        if physical_name == 'REWIND':
            if value == 1:
                self.send_shieldvlc_control('rewind')
            return

        if physical_name == 'FASTFORWARD':
            if value == 1:
                self.send_shieldvlc_control('fastforward')
            return

        # No special VLC function on these two keys anymore.
        if physical_name in ('MENU', 'VIDEO'):
            return

        # Press and key-repeat navigate; releases are not needed by the TV UI.
        if physical_name in ('UP', 'DOWN', 'LEFT', 'RIGHT'):
            if value in (1, 2):
                self.send_shieldvlc_control(physical_name.lower())
            return

        if value != 1:
            return

        commands = {
            'BACK': 'back',
            'PLAYPAUSE': 'playpause',
        }
        command = commands.get(physical_name)
        if command:
            self.send_shieldvlc_control(command)

    def _cancel_kodi_select_timer(self):
        timer = self.kodi_select_timer
        self.kodi_select_timer = None
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                pass

    def _kodi_long_ok_fire(self, token):
        # Timer based long-press: the physical Shield remote does not have to
        # generate key-repeat events for Kodi's context menu to work.
        if (
            self.kodi_select_down is not None
            and token == self.kodi_select_token
            and not self.kodi_select_long_sent
        ):
            self.tap(ecodes.KEY_C)
            self.kodi_select_long_sent = True
            self.log('Kodi OK lang -> Kontextmenue (C)')

    def handle_kodi(self, physical_name, code, value):
        """Kodi: short OK = Enter, long OK = context menu (keyboard C).

        Long-press is timer-driven, not dependent on EV_KEY repeat events.
        That makes the Kodi context menu reliable with the NVIDIA Shield remote.
        """
        if physical_name != 'SELECT':
            self.emit_simple(code, value)
            return

        now = time.monotonic()
        if value == 1:
            self._cancel_kodi_select_timer()
            self.kodi_select_down = now
            self.kodi_select_long_sent = False
            self.kodi_select_token += 1
            token = self.kodi_select_token
            timer = threading.Timer(self.kodi_select_hold, self._kodi_long_ok_fire, args=(token,))
            timer.daemon = True
            self.kodi_select_timer = timer
            timer.start()
            return

        if value == 2:
            # Repeats are intentionally ignored.  The timer owns long-press.
            return

        if value == 0:
            started = self.kodi_select_down
            long_sent = self.kodi_select_long_sent
            self._cancel_kodi_select_timer()
            self.kodi_select_down = None
            self.kodi_select_long_sent = False
            self.kodi_select_token += 1
            if started is None:
                return
            held = now - started
            if long_sent:
                return
            if held >= self.kodi_select_hold:
                # Fallback in case the timer thread was delayed.
                self.tap(ecodes.KEY_C)
                self.log('Kodi OK lang -> Kontextmenue (C, release fallback)')
            else:
                self.tap(ecodes.KEY_ENTER)
                self.log('Kodi OK kurz -> Enter')
            return

    def handle_browser(self, physical_name, value):
        if physical_name in ('VOLUMEUP','VOLUMEDOWN','PLAYPAUSE'):
            code = {
                'VOLUMEUP': ecodes.KEY_VOLUMEUP,
                'VOLUMEDOWN': ecodes.KEY_VOLUMEDOWN,
                'PLAYPAUSE': ecodes.KEY_PLAYPAUSE,
            }[physical_name]
            self.emit_simple(code, value)
            return
        if value != 1:
            return
        if physical_name in ('DOWN','RIGHT','MENU'):
            self.tap(ecodes.KEY_TAB)
        elif physical_name in ('UP','LEFT'):
            self.emit_combo([ecodes.KEY_LEFTSHIFT], ecodes.KEY_TAB)
        elif physical_name == 'SELECT':
            self.tap(ecodes.KEY_ENTER)
        elif physical_name == 'BACK':
            self.emit_combo([ecodes.KEY_LEFTALT], ecodes.KEY_LEFT)

    def handle_generic(self, physical_name, code, value):
        if physical_name == 'SELECT':
            self.emit_simple(ecodes.KEY_ENTER, value)
        elif physical_name == 'BACK':
            self.emit_simple(ecodes.KEY_ESC, value)
        elif physical_name == 'MENU':
            self.emit_simple(ecodes.KEY_TAB, value)
        else:
            self.emit_simple(code, value)

    def handle_osk_input(self, physical_name, code, value):
        if physical_name in ('VOLUMEUP', 'VOLUMEDOWN'):
            self.emit_simple(code, value)
            return
        if physical_name == 'SEARCH' and value == 1:
            self.close_osk()
            return
        if physical_name == 'BACK' and value == 1:
            self.close_osk()
            return
        if physical_name == 'MENU':
            return
        if value != 1:
            return
        commands = {
            'UP': 'osk_up', 'DOWN': 'osk_down', 'LEFT': 'osk_left',
            'RIGHT': 'osk_right', 'SELECT': 'osk_select',
        }
        if physical_name in commands:
            self.send_launcher_control(commands[physical_name])
        elif physical_name == 'PLAYPAUSE':
            self.tap(ecodes.KEY_SPACE)

    def shieldvlc_transport_target_active(self):
        """True only when our Shield VLC frontend is the foreground target."""
        if self.shieldvlc_window_active():
            return True
        return SHIELD_VLC_CONTROL_SOCKET.exists() and self.cached_profile == 'shieldvlc'

    def dispatch(self, code, value):
        # Shield VLC transport keys: exact raw codes measured from this remote:
        #   << = 168 / KEY_REWIND, >> = 208 / KEY_FASTFORWARD.
        # They bypass every profile/key-remapping layer and go directly to the
        # Shield VLC control socket.  This is deliberately checked BEFORE the
        # D-pad map, so LEFT/RIGHT can never masquerade as transport buttons.
        if code in (SHIELD_KEY_REWIND, SHIELD_KEY_FASTFORWARD):
            if self.shieldvlc_transport_target_active():
                if value == 1:
                    command = 'rewind' if code == SHIELD_KEY_REWIND else 'fastforward'
                    ok = self.send_shieldvlc_control(command)
                    print(
                        f'Shield VLC RAW transport code={code} command={command} sent={ok}',
                        flush=True
                    )
                # Release/repeat is consumed in Shield VLC. One physical press
                # advances one shuttle stage: x2 -> x4 -> x8 -> x16 -> x32.
                return

        physical_name = PHYSICAL.get(code)
        if not physical_name:
            return

        if physical_name == 'HOME':
            if value == 1:
                self.handle_home()
            return
        if self.osk_visible():
            self.handle_osk_input(physical_name, code, value)
            return

        profile = self.profile_for_active_window()

        # Exactly one dedicated OSK key: microphone/search.
        if physical_name == 'SEARCH':
            if value == 1:
                self.toggle_osk(profile)
            return

        # Netflix/VIDEO is no longer a FreeTube launch shortcut.  FreeTube is
        # started normally from the Shield launcher.  The key is reserved for
        # application-specific coarse navigation; currently VLC uses it for
        # its Qt menu bar.
        if physical_name == 'VIDEO' and profile not in ('vlc', 'shieldvlc'):
            if value == 1:
                self.log(f'NETFLIX/VIDEO unbenutzt in profile={profile}')
            return

        self.log(f'{physical_name} value={value} active={self.cached_active!r} profile={profile}')

        if profile == 'freetube':
            self.handle_freetube(physical_name, value)
        elif profile == 'shieldvlc':
            self.handle_shieldvlc(physical_name, value)
        elif profile == 'vlc':
            self.handle_vlc(physical_name, value)
        elif profile == 'kodi':
            self.handle_kodi(physical_name, code, value)
        elif profile == 'browser':
            self.handle_browser(physical_name, value)
        else:
            self.handle_generic(physical_name, code, value)

    def run_device(self, dev):
        print(f'Shield Remote gefunden: {dev.path} -> {dev.name} | {dev.phys}', flush=True)
        if not self.no_grab:
            try:
                dev.grab()
                print('Fernbedienung exklusiv uebernommen (EVIOCGRAB).', flush=True)
            except OSError as e:
                print('Konnte Fernbedienung nicht uebernehmen.', file=sys.stderr)
                print('Laeuft input-remapper noch? sudo systemctl stop input-remapper', file=sys.stderr)
                print(f'Detail: {e}', file=sys.stderr)
                return
        try:
            for event in dev.read_loop():
                if event.type == ecodes.EV_KEY:
                    self.dispatch(event.code, event.value)
        finally:
            if not self.no_grab:
                try: dev.ungrab()
                except Exception: pass
            try: dev.close()
            except Exception: pass

    def run(self):
        print('Shield Pi Remote Daemon v20 gestartet (Kodi Long-OK + Shield-VLC Ordner-Playlist + Mediensteuerung).', flush=True)
        print('Mikrofon = virtuelle Tastatur | Kodi: OK halten=Kontext | Shield VLC: OK halten=Musikordner, Musik mit D-Pad/Transport Titel wechseln', flush=True)
        self._start_media_control_socket()
        try:
            while True:
                dev = self.find_remote()
                if dev is None:
                    print('NVIDIA SHIELD Remote nicht gefunden; neuer Versuch in 2 s.', flush=True)
                    time.sleep(2)
                    continue
                try:
                    self.run_device(dev)
                except KeyboardInterrupt:
                    break
                except OSError as e:
                    print(f'Fernbedienung getrennt/Fehler: {e}', flush=True)
                except Exception as e:
                    print(f'Unerwarteter Fehler: {e}', file=sys.stderr, flush=True)
                self._cdp_close()
                time.sleep(1)
        finally:
            self._stop_media_control_socket()


def main():
    ap = argparse.ArgumentParser(description='Shield Pi application-aware remote remapper v8')
    ap.add_argument('--config', default=str(DEFAULT_CONFIG))
    ap.add_argument('--no-grab', action='store_true')
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()
    daemon = ShieldRemote(args.config, no_grab=args.no_grab, verbose=args.verbose)
    try:
        daemon.run()
    finally:
        daemon._cdp_close()
        try: daemon.ui.close()
        except Exception: pass


if __name__ == '__main__':
    main()
