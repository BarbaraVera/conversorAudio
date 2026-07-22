/**
 * ConversorAudio — Frontend Logic
 * --------------------------------
 * Maneja interacción UI, detección de plataforma,
 * comunicación con la API y simulación mock.
 */

(function () {
  'use strict';

  // =============================================
  // DOM References
  // =============================================
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const dom = {
    urlInput:          $('#url-input'),
    urlHint:           $('#url-hint'),
    platformIcon:      $('#platform-icon'),
    btnClearInput:     $('#btn-clear-input'),
    btnMp3:            $('#btn-mp3'),
    btnMp4:            $('#btn-mp4'),
    qualitySelector:   $('#quality-selector'),
    btnDownload:       $('#btn-download'),
    btnDownloadText:   $('#btn-download-text'),
    progressSection:   $('#progress-section'),
    progressLabel:     $('#progress-label'),
    progressPercent:   $('#progress-percent'),
    progressBar:       $('#progress-bar'),
    progressDetail:    $('#progress-detail'),
    resultSection:     $('#result-section'),
    resultTitle:       $('#result-title'),
    resultMeta:        $('#result-meta'),
    resultLink:        $('#result-download-link'),
    errorSection:      $('#error-section'),
    errorTitle:        $('#error-title'),
    errorMessage:      $('#error-message'),
    statusPlatform:    $('#status-platform'),
  };

  // =============================================
  // State
  // =============================================
  let state = {
    format: 'mp3',
    quality: '192',
    platform: null,
    status: 'idle', // idle | processing | ready | error
    taskId: null,
  };

  // =============================================
  // Platform detection
  // =============================================
  const PLATFORMS = {
    youtube: {
      patterns: [
        /(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=[\w-]+/,
        /(?:https?:\/\/)?(?:www\.)?youtu\.be\/[\w-]+/,
        /(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/[\w-]+/,
      ],
      name: 'YouTube',
      icon: `<svg class="w-5 h-5 text-red-600" viewBox="0 0 24 24" fill="currentColor"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>`,
    },
  };

  function detectPlatform(url) {
    if (!url) return null;
    for (const [key, platform] of Object.entries(PLATFORMS)) {
      for (const pattern of platform.patterns) {
        if (pattern.test(url)) return { key, ...platform };
      }
    }
    return null;
  }

  // =============================================
  // Quality options
  // =============================================
  const QUALITY_OPTIONS = {
    mp3: [
      { value: '128', label: '128 kbps' },
      { value: '192', label: '192 kbps' },
      { value: '320', label: '320 kbps' },
    ],
    mp4: [
      { value: '360', label: '360p' },
      { value: '720', label: '720p' },
      { value: '1080', label: '1080p' },
    ],
  };

  function renderQualityOptions() {
    const options = QUALITY_OPTIONS[state.format];
    dom.qualitySelector.innerHTML = options
      .map(
        (opt) =>
          `<button type="button" class="os-chip ${opt.value === state.quality ? 'active' : ''}" data-quality="${opt.value}">${opt.label}</button>`
      )
      .join('');
  }

  // =============================================
  // UI State management
  // =============================================
  function setStatus(newStatus) {
    state.status = newStatus;

    // Ocultar todas las secciones
    dom.progressSection.classList.add('hidden');
    dom.resultSection.classList.add('hidden');
    dom.errorSection.classList.add('hidden');

    // Reset botón
    dom.btnDownload.disabled = false;
    dom.btnDownloadText.innerHTML = `
      <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
        <polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>
      </svg>
      Descargar`;

    switch (newStatus) {
      case 'processing':
        dom.progressSection.classList.remove('hidden');
        dom.btnDownload.disabled = true;
        dom.btnDownloadText.innerHTML = `
          <svg class="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <circle cx="12" cy="12" r="10" stroke-dasharray="60" stroke-dashoffset="15"/>
          </svg>
          Procesando...`;
        break;

      case 'ready':
        dom.resultSection.classList.remove('hidden');
        break;

      case 'error':
        dom.errorSection.classList.remove('hidden');
        break;
    }
  }

  function updateProgress(percent, label, detail) {
    dom.progressPercent.textContent = `${percent}%`;
    dom.progressBar.style.width = `${percent}%`;
    if (label) dom.progressLabel.textContent = label;
    if (detail) dom.progressDetail.textContent = detail;
  }

  function showError(title, message) {
    dom.errorTitle.textContent = title;
    dom.errorMessage.textContent = message;
    setStatus('error');
  }

  function showResult(title, meta, downloadUrl) {
    dom.resultTitle.textContent = title;
    dom.resultMeta.textContent = meta;
    dom.resultLink.href = downloadUrl;
    setStatus('ready');
  }

  // =============================================
  // API Communication (real + mock fallback)
  // =============================================
  const API_BASE = '';

  async function apiDownload(url, format, quality) {
    // Intentar API real primero
    try {
      const res = await fetch(`${API_BASE}/api/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, format, quality }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${res.status}`);
      }

      return await res.json();
    } catch (err) {
      // Solo usar mock si la API no responde (Connection refused)
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        console.warn('[Mock] API no disponible, usando simulación:', err.message);
        return mockDownload(url, format, quality);
      }
      throw err;
    }
  }

  async function apiStatus(taskId) {
    try {
      const res = await fetch(`${API_BASE}/api/status/${taskId}`);
      if (!res.ok) throw new Error(`Error ${res.status}`);
      return await res.json();
    } catch {
      return mockStatus(taskId);
    }
  }

  // =============================================
  // Mock API (simulación para desarrollo)
  // =============================================
  let mockTaskCounter = 0;
  const mockTasks = {};

  function mockDownload(url, format, quality) {
    mockTaskCounter++;
    const taskId = `mock-${mockTaskCounter}-${Date.now()}`;
    const startTime = Date.now();
    const duration = 4000 + Math.random() * 3000;

    mockTasks[taskId] = { startTime, duration, format };

    return { task_id: taskId, status: 'processing' };
  }

  function mockStatus(taskId) {
    const task = mockTasks[taskId];
    if (!task) return { task_id: taskId, status: 'completed', progress: 100 };

    const elapsed = Date.now() - task.startTime;
    const progress = Math.min(Math.floor((elapsed / task.duration) * 100), 100);

    if (progress >= 100) {
      return {
        task_id: taskId,
        status: 'completed',
        progress: 100,
        file_name: `descarga_${Date.now()}.${task.format}`,
        file_size: `${(Math.random() * 8 + 1).toFixed(1)} MB`,
        duration: `${Math.floor(Math.random() * 5 + 1)}:${String(Math.floor(Math.random() * 60)).padStart(2, '0')}`,
      };
    }

    return { task_id: taskId, status: 'processing', progress };
  }

  // =============================================
  // Main download flow
  // =============================================

  const PROGRESS_LABELS = [
    [10,  'Conectando...',            'Estableciendo conexión con el servidor'],
    [25,  'Extrayendo información...', 'Analizando el enlace'],
    [50,  'Descargando...',           'Descargando el contenido multimedia'],
    [75,  'Convirtiendo...',          state.format === 'mp3' ? 'Convirtiendo a MP3' : 'Procesando video'],
    [90,  'Finalizando...',           'Preparando el archivo'],
  ];

  function getProgressLabel(pct) {
    let label = 'Iniciando...';
    let detail = 'Preparando descarga';
    for (const [threshold, l, d] of PROGRESS_LABELS) {
      if (pct >= threshold) { label = l; detail = d; }
    }
    return { label, detail };
  }

  function pollStatus(taskId, format) {
    return new Promise((resolve, reject) => {
      const interval = setInterval(async () => {
        try {
          const data = await apiStatus(taskId);

          if (data.progress != null) {
            const { label, detail } = getProgressLabel(data.progress);
            updateProgress(data.progress, label, detail);
          }

          if (data.status === 'completed') {
            clearInterval(interval);
            resolve(data);
          } else if (data.status === 'error') {
            clearInterval(interval);
            reject(new Error(data.error || 'La descarga falló'));
          }
        } catch (err) {
          clearInterval(interval);
          reject(err);
        }
      }, 500);
    });
  }

  async function handleDownload() {
    const url = dom.urlInput.value.trim();

    if (!url) {
      showError('URL vacía', 'Pega un enlace de YouTube para comenzar.');
      return;
    }

    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      showError('URL inválida', 'El enlace debe comenzar con http:// o https://');
      return;
    }

    const platform = detectPlatform(url);
    if (!platform) {
      showError('Plataforma no soportada', 'Solo se aceptan enlaces de YouTube.');
      return;
    }

    setStatus('processing');
    updateProgress(0, 'Iniciando...', 'Preparando descarga');

    try {
      const result = await apiDownload(url, state.format, state.quality);
      const taskId = result.task_id;

      const finalStatus = await pollStatus(taskId, state.format);

      const meta = [
        state.format.toUpperCase(),
        finalStatus.duration || '',
        finalStatus.file_size || '',
      ]
        .filter(Boolean)
        .join(' · ');

      updateProgress(100, '¡Listo!', 'Archivo listo para descargar');

      showResult(
        finalStatus.title || `descarga.${state.format}`,
        meta,
        `${API_BASE}/api/download/${taskId}`
      );
    } catch (err) {
      showError('Error en la descarga', err.message || 'No se pudo completar la descarga.');
    }
  }

  // =============================================
  // Event listeners
  // =============================================
  function init() {
    // Input URL — detectar plataforma en tiempo real
    dom.urlInput.addEventListener('input', () => {
      const url = dom.urlInput.value;
      const hasText = url.length > 0;

      dom.btnClearInput.classList.toggle('opacity-30', !hasText);
      dom.btnClearInput.classList.toggle('pointer-events-none', !hasText);
      dom.btnClearInput.classList.toggle('opacity-100', hasText);
      dom.btnClearInput.classList.toggle('pointer-events-auto', hasText);

      const platform = detectPlatform(url);

      if (platform) {
        state.platform = platform.key;
        dom.platformIcon.innerHTML = platform.icon;
        dom.platformIcon.classList.remove('opacity-0');
        dom.platformIcon.classList.add('opacity-100');
        dom.urlHint.textContent = `${platform.name} detectado`;
        dom.urlHint.classList.remove('opacity-50');
        dom.urlHint.classList.add('text-green-700', 'font-bold');
        dom.statusPlatform.textContent = `Plataforma: ${platform.name}`;
      } else {
        state.platform = null;
        dom.platformIcon.classList.add('opacity-0');
        dom.platformIcon.classList.remove('opacity-100');
        dom.urlHint.textContent = 'Soporta YouTube';
        dom.urlHint.classList.add('opacity-50');
        dom.urlHint.classList.remove('text-green-700', 'font-bold');
        dom.statusPlatform.textContent = 'Plataforma: —';
      }
    });

    // Boton limpiar input
    dom.btnClearInput.addEventListener('click', () => {
      dom.urlInput.value = '';
      dom.urlInput.dispatchEvent(new Event('input'));
      dom.urlInput.focus();
    });

    // Toggle de formato
    dom.btnMp3.addEventListener('click', () => {
      state.format = 'mp3';
      state.quality = '192';
      dom.btnMp3.classList.add('active');
      dom.btnMp4.classList.remove('active');
      renderQualityOptions();
    });

    dom.btnMp4.addEventListener('click', () => {
      state.format = 'mp4';
      state.quality = '720';
      dom.btnMp4.classList.add('active');
      dom.btnMp3.classList.remove('active');
      renderQualityOptions();
    });

    // Selector de calidad (delegación de eventos)
    dom.qualitySelector.addEventListener('click', (e) => {
      const chip = e.target.closest('.os-chip');
      if (!chip) return;
      state.quality = chip.dataset.quality;
      $$('.os-chip').forEach((c) => c.classList.remove('active'));
      chip.classList.add('active');
    });

    // Boton descargar
    dom.btnDownload.addEventListener('click', handleDownload);

    // Descarga de resultado: ocultar seccion completa despues del primer click
    dom.resultLink.addEventListener('click', () => {
      dom.resultSection.classList.add('hidden');
    });

    // Enter en input dispara descarga
    dom.urlInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') handleDownload();
    });

    // Render inicial
    renderQualityOptions();

    // Iniciar reloj
    startClock();
  }

  // =============================================
  // Reloj digital en tiempo real
  // =============================================
  function startClock() {
    const clockEl = document.getElementById('os-clock');
    if (!clockEl) return;

    function updateClock() {
      const now = new Date();
      const h = String(now.getHours()).padStart(2, '0');
      const m = String(now.getMinutes()).padStart(2, '0');
      const s = String(now.getSeconds()).padStart(2, '0');
      clockEl.textContent = `${h}:${m}:${s}`;
    }

    updateClock();
    setInterval(updateClock, 1000);
  }

  // Arrancar
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
