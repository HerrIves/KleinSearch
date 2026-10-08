import csv
import json
import os
import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

CSV_DATABASE_PATH = r"c:\work\donor_listings.csv"
HTML_DASHBOARD_PATH = r"c:\work\index.html"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ThinkPad P15 Gen 2 — Таблица доноров матрицы и SSD</title>
  <style>
    :root {
      --bg: #0b0f19;
      --surface: #151e2e;
      --surface-border: #23324a;
      --text: #f1f5f9;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --match: #10b981;
      --match-bg: rgba(16, 185, 129, 0.15);
      --match-border: rgba(16, 185, 129, 0.35);
      --potential: #f59e0b;
      --potential-bg: rgba(245, 158, 11, 0.15);
      --potential-border: rgba(245, 158, 11, 0.35);
      --radius: 12px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 24px;
      line-height: 1.5;
    }
    .container { max-width: 1480px; margin: 0 auto; }
    header {
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--surface-border);
    }
    .header-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }
    h1 {
      font-size: 1.75rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .subtitle { color: var(--text-muted); font-size: 0.95rem; margin-top: 6px; }

    .header-right {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .file-connect-btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: #1e293b;
      border: 1px solid #334155;
      color: #38bdf8;
      padding: 7px 14px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
    }
    .file-connect-btn:hover {
      background: #0284c7;
      color: #fff;
      border-color: #0284c7;
    }
    .file-connect-btn.connected {
      background: rgba(16, 185, 129, 0.12);
      border-color: rgba(16, 185, 129, 0.4);
      color: #34d399;
    }
    .file-connect-btn.connected:hover {
      background: rgba(16, 185, 129, 0.2);
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: currentColor;
      display: inline-block;
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      margin-bottom: 24px;
    }
    .stat-card {
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: var(--radius);
      padding: 16px 20px;
    }
    .stat-label { font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
    .stat-value { font-size: 1.8rem; font-weight: 700; margin-top: 4px; }
    .stat-value.green { color: var(--match); }
    .stat-value.amber { color: var(--potential); }

    .controls {
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
      background: var(--surface);
      padding: 14px 20px;
      border-radius: var(--radius);
      border: 1px solid var(--surface-border);
    }
    .search-box {
      flex: 1;
      min-width: 260px;
    }
    .search-input {
      width: 100%;
      background: #0b0f19;
      border: 1px solid var(--surface-border);
      border-radius: 8px;
      padding: 10px 14px;
      color: #fff;
      font-size: 0.95rem;
      outline: none;
      transition: border-color 0.15s;
    }
    .search-input:focus { border-color: var(--accent); }

    .filter-pills { display: flex; gap: 8px; flex-wrap: wrap; }
    .pill {
      background: #0b0f19;
      border: 1px solid var(--surface-border);
      color: var(--text-muted);
      padding: 8px 14px;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.875rem;
      font-weight: 500;
      transition: all 0.15s;
    }
    .pill:hover { color: #fff; border-color: var(--accent); }
    .pill.active { background: var(--accent); color: #0b0f19; border-color: var(--accent); font-weight: 700; }

    .extra-controls {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .sort-select {
      background: #0b0f19;
      border: 1px solid var(--surface-border);
      color: #fff;
      padding: 9px 12px;
      border-radius: 8px;
      font-size: 0.9rem;
      outline: none;
      cursor: pointer;
    }
    .btn-export {
      background: #0b0f19;
      border: 1px solid var(--surface-border);
      color: var(--text-muted);
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 0.875rem;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s;
    }
    .btn-export:hover {
      color: #fff;
      border-color: var(--accent);
    }

    /* Таблица */
    .table-container {
      width: 100%;
      max-width: 100%;
      box-sizing: border-box;
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: var(--radius);
      overflow-x: auto;
      box-shadow: 0 4px 25px rgba(0, 0, 0, 0.3);
      -webkit-overflow-scrolling: touch;
    }
    .listings-table {
      width: 100%;
      min-width: 1100px;
      table-layout: fixed;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.92rem;
    }
    .listings-table th {
      background: #101726;
      color: var(--text-muted);
      padding: 14px 14px;
      font-weight: 600;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 1px solid var(--surface-border);
      position: sticky;
      top: 0;
      z-index: 5;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .listings-table td {
      padding: 12px 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      vertical-align: middle;
      overflow: hidden;
    }
    .listings-table tbody tr {
      transition: background 0.15s;
    }
    .listings-table tbody tr:hover {
      background: rgba(255, 255, 255, 0.035);
    }
    .listings-table tbody tr.row-match {
      background: rgba(16, 185, 129, 0.06);
    }
    .listings-table tbody tr.row-match:hover {
      background: rgba(16, 185, 129, 0.12);
    }
    .listings-table tbody tr.row-match td:first-child {
      border-left: 4px solid var(--match);
    }
    .listings-table tbody tr:not(.row-match) td:first-child {
      border-left: 4px solid transparent;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      white-space: nowrap;
    }
    .badge-match {
      background: var(--match-bg);
      color: var(--match);
      border: 1px solid var(--match-border);
    }
    .badge-potential {
      background: var(--potential-bg);
      color: var(--potential);
      border: 1px solid var(--potential-border);
    }

    .title-cell {
      font-weight: 600;
      color: #fff;
      line-height: 1.4;
      word-break: break-word;
      overflow-wrap: break-word;
    }
    .title-link {
      color: #f1f5f9;
      text-decoration: none;
      transition: color 0.15s;
      word-break: break-word;
      overflow-wrap: break-word;
    }
    .title-link:hover {
      color: var(--accent);
      text-decoration: underline;
    }

    .price-cell {
      font-weight: 700;
      font-size: 1.05rem;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      color: #38bdf8;
    }
    .row-match .price-cell {
      color: #34d399;
    }

    .ssd-cell {
      white-space: nowrap;
    }
    .ssd-tag {
      display: inline-block;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.78rem;
      white-space: nowrap;
    }
    .ssd-tag.yes { background: rgba(16, 185, 129, 0.2); color: #34d399; }
    .ssd-tag.check { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }

    .location-cell {
      color: #cbd5e1;
      font-size: 0.85rem;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .shipping-tag {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.78rem;
      font-weight: 600;
      white-space: nowrap;
    }
    .shipping-tag.yes { background: rgba(16, 185, 129, 0.2); color: #34d399; }
    .shipping-tag.no { background: rgba(148, 163, 184, 0.15); color: #94a3b8; }

    .date-cell {
      color: var(--text-muted);
      font-size: 0.82rem;
      white-space: nowrap;
    }

    /* Интерактивное примечание с прямым сохранением в CSV */
    .comment-cell {
      color: #cbd5e1;
      font-size: 0.85rem;
      min-width: 240px;
      max-width: 320px;
    }
    .comment-display {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      padding: 6px 8px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid transparent;
      transition: all 0.15s;
      cursor: pointer;
    }
    .comment-display:hover {
      background: rgba(255, 255, 255, 0.06);
      border-color: rgba(255, 255, 255, 0.12);
    }
    .comment-text {
      flex: 1;
      word-break: break-word;
      line-height: 1.4;
    }
    .comment-empty {
      color: #64748b;
      font-style: italic;
    }
    .btn-edit-note {
      background: transparent;
      border: none;
      cursor: pointer;
      font-size: 0.85rem;
      opacity: 0.35;
      padding: 0 2px;
      transition: opacity 0.15s;
    }
    .comment-display:hover .btn-edit-note {
      opacity: 1;
    }
    .comment-editor {
      display: flex;
      flex-direction: column;
      gap: 6px;
      background: #0f172a;
      padding: 8px;
      border-radius: 8px;
      border: 1px solid var(--accent);
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
    }
    .comment-textarea {
      width: 100%;
      background: #0b0f19;
      border: 1px solid var(--surface-border);
      border-radius: 6px;
      padding: 8px;
      color: #fff;
      font-family: inherit;
      font-size: 0.85rem;
      line-height: 1.4;
      resize: vertical;
      min-height: 56px;
      outline: none;
      box-sizing: border-box;
    }
    .comment-textarea:focus {
      border-color: var(--accent);
    }
    .comment-actions {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }
    .btn-save-note {
      background: #0284c7;
      color: #fff;
      border: none;
      padding: 5px 12px;
      border-radius: 4px;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s;
    }
    .btn-save-note:hover {
      background: #0369a1;
    }
    .btn-cancel-note {
      background: #334155;
      color: #cbd5e1;
      border: none;
      padding: 5px 8px;
      border-radius: 4px;
      font-size: 0.78rem;
      cursor: pointer;
      transition: background 0.15s;
    }
    .btn-cancel-note:hover {
      background: #475569;
    }
    .save-status {
      font-size: 0.75rem;
      font-weight: 600;
      margin-left: 4px;
    }
    .save-status.success { color: #34d399; }
    .save-status.info { color: #38bdf8; }
    .save-status.warn { color: #fbbf24; }

    .action-cell {
      text-align: center;
      white-space: nowrap;
    }
    .table-btn {
      display: inline-block;
      background: #1e293b;
      color: #38bdf8;
      border: 1px solid #334155;
      padding: 7px 14px;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 600;
      font-size: 0.85rem;
      transition: all 0.15s;
    }
    .table-btn:hover {
      background: #0284c7;
      color: #fff;
      border-color: #0284c7;
    }
    .row-match .table-btn {
      background: #064e3b;
      color: #34d399;
      border-color: #059669;
    }
    .row-match .table-btn:hover {
      background: #059669;
      color: #fff;
    }

    .empty-row td {
      text-align: center;
      padding: 60px 20px;
      color: var(--text-muted);
    }

    /* Матрица: тир качества */
    .matrix-badge {
      display: inline-block;
      font-size: 0.65rem;
      font-weight: 700;
      letter-spacing: 0.03em;
      padding: 2px 6px;
      border-radius: 4px;
      margin-left: 6px;
      vertical-align: middle;
      white-space: nowrap;
    }
    .matrix-premium {
      background: rgba(251, 191, 36, 0.15);
      color: #fbbf24;
      border: 1px solid rgba(251, 191, 36, 0.35);
    }
    .matrix-ips {
      background: rgba(148, 163, 184, 0.1);
      color: #94a3b8;
      border: 1px solid rgba(148, 163, 184, 0.25);
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="header-top">
        <h1>📊 Таблица доноров для ThinkPad P15 Gen 2</h1>
        <div class="header-right">
          <button id="btnConnectFile" class="file-connect-btn" title="Подключить файл donor_listings.csv на диске для прямой записи правок из браузера">
            <span class="status-dot"></span>
            <span id="btnConnectText">📁 Подключить donor_listings.csv</span>
          </button>
        </div>
      </div>
      <p class="subtitle">Матрица: 15.6" Slim FHD (30-pin eDP без ушек) • 100% sRGB / 72% NTSC (≥300–500 нит) • Без 4K/UHD • Бюджет до 150 €</p>
    </header>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">🎯 Полных совпадений (MATCH)</div>
        <div class="stat-value green">__MATCH_COUNT__</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">⚠️ Кандидаты (Целый экран)</div>
        <div class="stat-value amber">__POTENTIAL_COUNT__</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">📦 Всего в таблице</div>
        <div class="stat-value">__TOTAL_COUNT__</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">💰 Бюджет</div>
        <div class="stat-value">≤ 150 €</div>
      </div>
    </div>

    <div class="controls">
      <div class="search-box">
        <input type="search" class="search-input" id="searchInput" placeholder="🔍 Быстрый поиск (город, модель, например: Berlin, E15, V15, 512)...">
      </div>
      <div class="filter-pills">
        <button class="pill active" data-filter="ALL">Все (__TOTAL_COUNT__)</button>
        <button class="pill" data-filter="MATCH">🎯 Только MATCH (__MATCH_COUNT__)</button>
        <button class="pill" data-filter="POTENTIAL">⚠️ Кандидаты (__POTENTIAL_COUNT__)</button>
        <button class="pill" data-filter="SHIPPING">📦 С доставкой</button>
      </div>
      <div class="extra-controls">
        <select class="sort-select" id="sortSelect">
          <option value="date-desc">Сначала самые свежие</option>
          <option value="price-asc">Сначала дешевые</option>
          <option value="price-desc">Сначала дорогие</option>
        </select>
        <button class="btn-export" id="btnExport" title="Скачать копию таблицы со всеми заметками в CSV">
          📥 Экспорт CSV
        </button>
      </div>
    </div>

    <div class="table-container">
      <table class="listings-table">
        <thead>
          <tr>
            <th style="width: 125px;">Статус</th>
            <th>Модель / Заголовок</th>
            <th style="width: 95px;">Цена</th>
            <th style="width: 105px;">SSD 512GB</th>
            <th style="width: 165px;">Локация 📍</th>
            <th style="width: 130px;">Доставка 📦</th>
            <th style="width: 110px;">Дата</th>
            <th style="width: 260px;">Примечание (клик для правки) ✏️</th>
            <th style="width: 95px; text-align: center;">Действие</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
    </div>
  </div>

  <script>
    let rawListings = __DATA_JSON__;

    // Резервное восстановление правок из локальной памяти браузера
    const localNotes = JSON.parse(localStorage.getItem('thinkpad_user_notes') || '{}');
    rawListings.forEach(item => {
      const id = String(item['ID'] || item['Ссылка']);
      if (localNotes[id]) {
        item['Комментарий'] = localNotes[id];
      }
    });

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    // Определяет тир матрицы по названию объявления
    function getMatrixBadge(title) {
      const t = (title || '').toLowerCase();
      // Группа 5 — стандартная IPS (~45-72% NTSC)
      const ipsModels = [
        /thinkpad\\s*t590\\b/, /\\bt590\\b/,
        /thinkpad\\s*p53s\\b/, /\\bp53s\\b/,
        /latitude\\s*5[45]\\d\\d\\b/,        // Dell Latitude 5400-5499, 5500-5599 (5500, 5510, 5520)
        /latitude\\s*55\\d\\d\\b/,           // fallback для 5500-серии
        /elitebook\\s*850\\s*g5\\b/,
        /zbook\\s*15\\s*g[3456]\\b/,        // ZBook 15 G3-G6 (без 'u' — стандартный IPS)
        /zbook\\s*15\\b(?!\\s*u\\b)/,        // ZBook 15 любой gen без 'u'
      ];
      for (const re of ipsModels) {
        if (re.test(t)) return '<span class="matrix-badge matrix-ips" title="Хорошая корпоративная IPS, ~45-72% NTSC">IPS</span>';
      }
      // Группы 1-4 — 100% sRGB / 72% NTSC
      const premiumModels = [
        /\\b(?:u758|u759|u7510)\\b/, /\\b(?:h7510|h7511)\\b/,
        /elitebook\\s*850\\s*g[678]\\b/,
        /elitebook\\s*850\\b/,             // EliteBook 850 без указания поколения → считаем премиум
        /zbook\\s*15u\\b/, /zbook\\s*firefly\\s*15\\b/, /firefly\\s*15\\b/,
        /latitude\\s*(?:7500|7510|7520)\\b/,
        /xps\\s*(?:15\\s*)?(?:9570|7590)\\b/, /\\b(?:9570|7590)\\b/,
        /thinkpad\\s*t15g\\b/, /thinkpad\\s*p15\\b(?!\\s*s)/,
        /msi\\s*prestige\\s*15\\b/,
      ];
      for (const re of premiumModels) {
        if (re.test(t)) return '<span class="matrix-badge matrix-premium" title="100% sRGB / 72% NTSC, 300-500 нит">★ 100% sRGB</span>';
      }
      return '';
    }



    function parseNumericPrice(str) {
      if (!str) return 0;
      if (str.toLowerCase().includes('zu verschenken')) return 0;
      // Немецкий формат: 1.200 € или 1.200,50 € → тысячи через точку, копейки через запятую
      // Захватываем: необязательные цифры с точками-разделителями тысяч, затем необязательную запятую с центами
      const match = str.match(/(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)/);

      if (!match) return 9999;
      // Убираем точки-разделители тысяч, заменяем запятую на точку для parseFloat
      return parseFloat(match[1].replace(/\./g, '').replace(',', '.'));
    }



    // ========================================================
    // FILE SYSTEM ACCESS API (Прямая запись в donor_listings.csv)
    // ========================================================
    let currentFileHandle = null;

    function getIDB() {
      return new Promise((resolve, reject) => {
        const req = indexedDB.open('ThinkPadDonorDB', 1);
        req.onupgradeneeded = () => req.result.createObjectStore('handles');
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      });
    }

    async function saveHandleToIDB(handle) {
      try {
        const db = await getIDB();
        const tx = db.transaction('handles', 'readwrite');
        tx.objectStore('handles').put(handle, 'csvHandle');
      } catch (e) {
        console.warn('Не удалось сохранить дескриптор файла в IDB:', e);
      }
    }

    async function loadHandleFromIDB() {
      try {
        const db = await getIDB();
        return new Promise(resolve => {
          const tx = db.transaction('handles', 'readonly');
          const req = tx.objectStore('handles').get('csvHandle');
          req.onsuccess = () => resolve(req.result || null);
          req.onerror = () => resolve(null);
        });
      } catch (e) {
        return null;
      }
    }

    function updateFileButtonUI(connected, filename = 'donor_listings.csv') {
      const btn = document.getElementById('btnConnectFile');
      const text = document.getElementById('btnConnectText');
      if (!btn || !text) return;

      if (connected) {
        btn.classList.add('connected');
        text.textContent = `🟢 Подключен: ${filename}`;
        btn.title = `Файл ${filename} подключен. Ваши правки сразу записываются прямо в него! Кликните, чтобы выбрать другой файл.`;
      } else {
        btn.classList.remove('connected');
        text.textContent = '📁 Подключить donor_listings.csv';
        btn.title = 'Подключить файл на диске для автоматической записи правок прямо в CSV';
      }
    }

    async function verifyPermission(handle, readWrite = true) {
      if (!handle) return false;
      const opts = readWrite ? { mode: 'readwrite' } : {};
      try {
        if ((await handle.queryPermission(opts)) === 'granted') {
          return true;
        }
        if ((await handle.requestPermission(opts)) === 'granted') {
          return true;
        }
      } catch (e) {
        console.warn('Ошибка проверки прав:', e);
      }
      return false;
    }

    window.connectFile = async function() {
      if (!window.showOpenFilePicker) {
        alert('Ваш браузер не поддерживает File System Access API. Рекомендуется использовать Google Chrome, Microsoft Edge или Яндекс.Браузер.');
        return;
      }

      try {
        const [handle] = await window.showOpenFilePicker({
          multiple: false,
          types: [{
            description: 'CSV файлы базы',
            accept: { 'text/csv': ['.csv'] }
          }]
        });

        if (handle) {
          const hasPerm = await verifyPermission(handle, true);
          if (hasPerm) {
            currentFileHandle = handle;
            await saveHandleToIDB(handle);
            updateFileButtonUI(true, handle.name);
          }
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error(err);
          alert('Не удалось подключить файл: ' + err.message);
        }
      }
    };

    document.getElementById('btnConnectFile').addEventListener('click', connectFile);

    // Автоматическая проверка ранее сохраненного дескриптора при открытии страницы
    async function initFileHandle() {
      if (!window.showOpenFilePicker) {
        const btn = document.getElementById('btnConnectFile');
        if (btn) btn.style.display = 'none';
        return;
      }

      const saved = await loadHandleFromIDB();
      if (saved) {
        currentFileHandle = saved;
        // Проверяем, есть ли уже выданные права без всплывающего окна
        try {
          if ((await saved.queryPermission({ mode: 'readwrite' })) === 'granted') {
            updateFileButtonUI(true, saved.name);
          } else {
            // Требуется подтверждение кликом
            const btn = document.getElementById('btnConnectFile');
            const text = document.getElementById('btnConnectText');
            if (btn && text) {
              text.textContent = `📁 Разрешить запись в ${saved.name}`;
            }
          }
        } catch (e) {
          updateFileButtonUI(false);
        }
      }
    }

    // Генерация валидного CSV-файла (UTF-8 с BOM, точка с запятой)
    function buildCsvText(items) {
      const headers = [
        "Дата добавления",
        "Статус",
        "Модель / Заголовок",
        "Цена",
        "SSD 512GB",
        "Местоположение",
        "Доставка",
        "Комментарий",
        "Ссылка",
        "ID"
      ];

      function escapeField(val) {
        if (val === null || val === undefined) return '';
        const str = String(val);
        if (str.includes(';') || str.includes('"') || str.includes('\\n') || str.includes('\\r')) {
          return '"' + str.replace(/"/g, '""') + '"';
        }
        return str;
      }

      let text = "\\uFEFF"; // UTF-8 BOM для корректного открытия в Excel
      text += headers.join(";") + "\\r\\n";
      for (const item of items) {
        const row = headers.map(h => escapeField(item[h]));
        text += row.join(";") + "\\r\\n";
      }
      return text;
    }

    async function writeCsvToDisk() {
      if (!currentFileHandle) {
        // Если еще не выбран, предлагаем пользователю выбрать файл
        await connectFile();
      }

      if (currentFileHandle) {
        const hasPerm = await verifyPermission(currentFileHandle, true);
        if (hasPerm) {
          const csvText = buildCsvText(rawListings);
          const writable = await currentFileHandle.createWritable();
          await writable.write(csvText);
          await writable.close();
          updateFileButtonUI(true, currentFileHandle.name);
          return true;
        }
      }
      return false;
    }

    // ========================================================
    // РЕНДЕРИНГ И ТАБЛИЦА
    // ========================================================
    let activeFilter = 'ALL';
    let searchQuery = '';
    let sortMode = 'date-desc';

    function render() {
      const tbody = document.getElementById('tableBody');
      tbody.innerHTML = '';

      let filtered = rawListings.filter(item => {
        if (activeFilter === 'MATCH' && item['Статус'] !== 'MATCH') return false;
        if (activeFilter === 'POTENTIAL' && item['Статус'] !== 'POTENTIAL') return false;
        if (activeFilter === 'SHIPPING' && !(item['Доставка'] || '').includes('Доставка возможна')) return false;

        if (searchQuery) {
          const text = (
            (item['Модель / Заголовок'] || '') + ' ' +
            (item['Местоположение'] || '') + ' ' +
            (item['Доставка'] || '') + ' ' +
            (item['Комментарий'] || '') + ' ' +
            (item['Цена'] || '')
          ).toLowerCase();
          if (!text.includes(searchQuery.toLowerCase())) return false;
        }
        return true;
      });

      filtered.sort((a, b) => {
        if (sortMode === 'date-desc') {
          const dateComp = (b['Дата добавления'] || '').localeCompare(a['Дата добавления'] || '');
          if (dateComp !== 0) return dateComp;
          return (b['Статус'] === 'MATCH' ? 1 : 0) - (a['Статус'] === 'MATCH' ? 1 : 0);
        } else if (sortMode === 'price-asc') {
          return parseNumericPrice(a['Цена']) - parseNumericPrice(b['Цена']);
        } else if (sortMode === 'price-desc') {
          return parseNumericPrice(b['Цена']) - parseNumericPrice(a['Цена']);
        }
        return 0;
      });

      if (filtered.length === 0) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="9"><h3>Объявлений не найдено</h3><p>Попробуйте изменить поисковый запрос или фильтр.</p></td></tr>';
        return;
      }

      filtered.forEach(item => {
        const isMatch = item['Статус'] === 'MATCH';
        const tr = document.createElement('tr');
        if (isMatch) tr.className = 'row-match';

        const badgeHtml = isMatch 
          ? '<span class="badge badge-match">🎯 MATCH</span>'
          : '<span class="badge badge-potential">⚠️ POTENTIAL</span>';

        const ssdTagHtml = item['SSD 512GB'] === 'Да'
          ? '<span class="ssd-tag yes">✓ 512 GB</span>'
          : '<span class="ssd-tag check">? Уточнить</span>';

        const isShipping = (item['Доставка'] || '').includes('Доставка возможна');
        const shipHtml = isShipping
          ? '<span class="shipping-tag yes">📦 Доставка</span>'
          : '<span class="shipping-tag no">🏠 Самовывоз</span>';

        const locText = item['Местоположение'] || 'Не указано';
        const itemId = String(item['ID'] || item['Ссылка']);
        const currentComment = item['Комментарий'] || '';

        tr.innerHTML = `
          <td>${badgeHtml}</td>
          <td class="title-cell">
            <a href="${item['Ссылка']}" target="_blank" rel="noopener noreferrer" class="title-link">
              ${escapeHtml(item['Модель / Заголовок'])}
            </a>${getMatrixBadge(item['Модель / Заголовок'])}
          </td>
          <td class="price-cell" title="${escapeHtml(item['Цена'])}">${escapeHtml(item['Цена'])}</td>
          <td class="ssd-cell">${ssdTagHtml}</td>
          <td class="location-cell" title="${escapeHtml(locText)}">📍 ${escapeHtml(locText)}</td>
          <td>${shipHtml}</td>
          <td class="date-cell">${escapeHtml(item['Дата добавления'] || '—')}</td>
          <td class="comment-cell" id="cell-${itemId}">
            <div class="comment-display" id="display-${itemId}" onclick="startEditNote('${itemId}')" title="Кликните, чтобы изменить примечание">
              <span class="comment-text" id="text-${itemId}">${escapeHtml(currentComment) || '<span class="comment-empty">Добавить примечание...</span>'}</span>
              <button type="button" class="btn-edit-note" title="Редактировать">✏️</button>
            </div>
            <div class="comment-editor" id="editor-${itemId}" style="display: none;">
              <textarea class="comment-textarea" id="input-${itemId}" placeholder="Введите ваше примечание (например: созвонился с продавцом, торг до 40€)..."></textarea>
              <div class="comment-actions">
                <button type="button" class="btn-save-note" onclick="saveNote('${itemId}')">💾 Сохранить</button>
                <button type="button" class="btn-cancel-note" onclick="cancelEditNote('${itemId}')">✕</button>
                <span class="save-status" id="status-${itemId}"></span>
              </div>
            </div>
          </td>
          <td class="action-cell">
            <a href="${item['Ссылка']}" target="_blank" rel="noopener noreferrer" class="table-btn">
              Открыть ↗
            </a>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    // Редактирование примечаний
    window.startEditNote = function(itemId) {
      const item = rawListings.find(i => String(i['ID'] || i['Ссылка']) === itemId);
      if (!item) return;

      const displayEl = document.getElementById(`display-${itemId}`);
      const editorEl = document.getElementById(`editor-${itemId}`);
      const inputEl = document.getElementById(`input-${itemId}`);
      const statusEl = document.getElementById(`status-${itemId}`);

      if (!displayEl || !editorEl || !inputEl) return;

      inputEl.value = item['Комментарий'] || '';
      if (statusEl) statusEl.textContent = '';

      displayEl.style.display = 'none';
      editorEl.style.display = 'flex';
      inputEl.focus();

      // Горячие клавиши: Ctrl+Enter для сохранения, Esc для отмены
      inputEl.onkeydown = function(e) {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
          e.preventDefault();
          saveNote(itemId);
        } else if (e.key === 'Escape') {
          e.preventDefault();
          cancelEditNote(itemId);
        }
      };
    };

    window.cancelEditNote = function(itemId) {
      const displayEl = document.getElementById(`display-${itemId}`);
      const editorEl = document.getElementById(`editor-${itemId}`);
      if (displayEl && editorEl) {
        displayEl.style.display = 'flex';
        editorEl.style.display = 'none';
      }
    };

    window.saveNote = async function(itemId) {
      const inputEl = document.getElementById(`input-${itemId}`);
      const statusEl = document.getElementById(`status-${itemId}`);
      const textEl = document.getElementById(`text-${itemId}`);
      const displayEl = document.getElementById(`display-${itemId}`);
      const editorEl = document.getElementById(`editor-${itemId}`);

      if (!inputEl) return;
      const newNote = inputEl.value.trim();

      // 1. Обновляем объект в оперативной памяти JS
      const item = rawListings.find(i => String(i['ID'] || i['Ссылка']) === itemId);
      if (item) {
        item['Комментарий'] = newNote;
      }

      // 2. Резервное сохранение в localStorage браузера
      localNotes[itemId] = newNote;
      try {
        localStorage.setItem('thinkpad_user_notes', JSON.stringify(localNotes));
      } catch (e) {}

      if (statusEl) {
        statusEl.className = 'save-status info';
        statusEl.textContent = 'Запись...';
      }

      // 3. Прямая запись в файл donor_listings.csv на жестком диске через File System Access API
      const written = await writeCsvToDisk();

      if (written) {
        if (statusEl) {
          statusEl.className = 'save-status success';
          statusEl.textContent = '✓ Записано в файл CSV!';
        }
      } else {
        if (statusEl) {
          statusEl.className = 'save-status warn';
          statusEl.textContent = '✓ Сохранено в браузере (подключите файл вверху)';
        }
      }

      setTimeout(() => {
        if (textEl) {
          textEl.innerHTML = escapeHtml(newNote) || '<span class="comment-empty">Добавить примечание...</span>';
        }
        if (displayEl && editorEl) {
          displayEl.style.display = 'flex';
          editorEl.style.display = 'none';
        }
      }, 700);
    };

    // Экспорт текущей таблицы со всеми заметками в CSV вручную
    document.getElementById('btnExport').addEventListener('click', () => {
      const csvContent = buildCsvText(rawListings);
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'donor_listings.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });

    document.getElementById('searchInput').addEventListener('input', e => {
      searchQuery = e.target.value.trim();
      render();
    });

    document.querySelectorAll('.pill').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        activeFilter = btn.dataset.filter;
        render();
      });
    });

    document.getElementById('sortSelect').addEventListener('change', e => {
      sortMode = e.target.value;
      render();
    });

    initFileHandle();
    render();
  </script>
</body>
</html>
"""

def generate_dashboard(csv_path: str = CSV_DATABASE_PATH, html_path: str = HTML_DASHBOARD_PATH):
    """Генерирует автономную интерактивную HTML-таблицу на основе CSV с поддержкой File System Access API."""
    rows = []
    if os.path.exists(csv_path):
        with open(csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            for r in reader:
                rows.append(r)

    matches_count = sum(1 for r in rows if r.get("Статус") == "MATCH")
    potential_count = sum(1 for r in rows if r.get("Статус") != "MATCH")
    total_count = len(rows)

    data_json = json.dumps(rows, ensure_ascii=False)

    html = HTML_TEMPLATE.replace("__MATCH_COUNT__", str(matches_count))
    html = html.replace("__POTENTIAL_COUNT__", str(potential_count))
    html = html.replace("__TOTAL_COUNT__", str(total_count))
    html = html.replace("__DATA_JSON__", data_json)

    with open(html_path, mode="w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML-таблица успешно сгенерирована: {html_path} ({total_count} строк)")
    return html_path

if __name__ == "__main__":
    generate_dashboard()
