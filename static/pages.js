const SEARCH_MODES = [
  ['starts_with', 'Empieza por'],
  ['contains', 'Contiene'],
  ['ends_with', 'Termina por'],
  ['exact', 'Exacta'],
];

const state = {
  catalog: [],
  filters: {
    q: '',
    categoria: '',
    subcategoria: '',
    variante: '',
    searchMode: 'contains',
    letter: '',
  },
  requests: loadJson('araia_requests', []),
  feedback: loadJson('araia_feedback', []),
  library: loadJson('araia_library', []),
};

function loadJson(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key)) || fallback;
  } catch {
    return fallback;
  }
}

function saveJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function normalize(value) {
  return (value || '')
    .toString()
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '');
}

function matchSearch(word, needle, mode) {
  if (!needle) return true;
  if (mode === 'starts_with') return word.startsWith(needle);
  if (mode === 'ends_with') return word.endsWith(needle);
  if (mode === 'exact') return word === needle;
  return word.includes(needle);
}

function buildAlphabet() {
  const wrapper = document.getElementById('alphabet-modes');
  const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
  wrapper.innerHTML = SEARCH_MODES.map(([mode, label]) => {
    const links = ['<a class="alphabet-pill ' + (state.filters.searchMode === mode && !state.filters.letter ? 'active' : '') + '" data-mode="' + mode + '" data-letter="">Todas</a>']
      .concat(letters.map(letter => '<a class="alphabet-pill ' + (state.filters.searchMode === mode && state.filters.letter === letter ? 'active' : '') + '" data-mode="' + mode + '" data-letter="' + letter + '">' + letter + '</a>'))
      .join('');
    return '<div class="alpha-mode-row"><strong class="mode-label ' + (state.filters.searchMode === mode ? 'active' : '') + '">' + label + '</strong><div class="alphabet-row compact-alphabet">' + links + '</div></div>';
  }).join('');

  wrapper.querySelectorAll('[data-mode]').forEach((item) => {
    item.addEventListener('click', () => {
      state.filters.searchMode = item.dataset.mode;
      state.filters.letter = item.dataset.letter;
      render();
    });
  });
}

function filteredCatalog() {
  const q = normalize(state.filters.q);
  return state.catalog.filter((record) => {
    const word = normalize(record.palabra);
    if (state.filters.categoria && record.categoria_gramatical !== state.filters.categoria) return false;
    if (state.filters.subcategoria && record.subcategoria !== state.filters.subcategoria) return false;
    if (state.filters.variante && record.variante !== state.filters.variante) return false;
    if (!matchSearch(word, q, state.filters.searchMode)) return false;
    if (state.filters.letter && !matchSearch(word, normalize(state.filters.letter), state.filters.searchMode)) return false;
    return true;
  });
}

function requestScore(item) {
  return (item.votes || 0) + (item.requests || 0) + (item.commentCount || 0);
}

function renderRequests() {
  const list = document.getElementById('request-priority-list');
  const items = [...state.requests]
    .sort((a, b) => requestScore(b) - requestScore(a) || b.updatedAt.localeCompare(a.updatedAt))
    .slice(0, 6);
  if (!items.length) {
    list.innerHTML = '<p class="description">Todavía no hay solicitudes guardadas en este navegador.</p>';
    return;
  }
  list.innerHTML = items.map((item, index) => `
    <article class="request-card ${index < 2 ? 'highlighted' : ''} stack-card">
      <strong>${escapeHtml(item.palabra)}</strong>
      <p>${escapeHtml(item.categoria || 'sin categoría')} · ${escapeHtml(item.subcategoria || 'sin subcategoría')}</p>
      <span>Prioridad ${requestScore(item)}</span>
      <button class="compact vote-button" data-request-id="${item.id}">Subir prioridad</button>
    </article>
  `).join('');
  list.querySelectorAll('[data-request-id]').forEach((button) => {
    button.addEventListener('click', () => {
      const target = state.requests.find((item) => item.id === button.dataset.requestId);
      if (!target) return;
      target.votes += 1;
      target.updatedAt = new Date().toISOString();
      persistLocalState();
      renderRequests();
    });
  });
}

function renderFeedback() {
  const list = document.getElementById('feedback-list');
  const items = [...state.feedback].sort((a, b) => b.createdAt.localeCompare(a.createdAt)).slice(0, 5);
  if (!items.length) {
    list.innerHTML = '<p class="description">Todavía no hay opiniones guardadas en este navegador.</p>';
    return;
  }
  list.innerHTML = items.map((item) => `
    <article class="feedback-card compact-feedback-card">
      <strong>${escapeHtml(item.tipo)}</strong>
      <p>${escapeHtml(item.texto)}</p>
    </article>
  `).join('');
}

function renderRecent() {
  const recent = [...state.catalog]
    .sort((a, b) => (b.fecha_creacion || '').localeCompare(a.fecha_creacion || ''))
    .slice(0, 8);
  const grid = document.getElementById('recent-grid');
  grid.innerHTML = recent.map((record) => `
    <article class="mini-card">
      <img src="${escapeAttribute(record.image_path)}" alt="${escapeAttribute(record.palabra)}">
      <strong>${escapeHtml(record.palabra)}</strong>
    </article>
  `).join('');
}

function renderStats(records) {
  document.getElementById('quick-stats').innerHTML = `
    <span>${records.length} visibles</span>
    <span>${state.library.length} guardados</span>
    <span>${state.catalog.length} total</span>
  `;
}

function renderResults() {
  const records = filteredCatalog();
  const grid = document.getElementById('results-grid');
  const emptyState = document.getElementById('empty-state');
  document.getElementById('results-count').textContent = `${records.length} pictogramas`;
  renderStats(records);

  if (!records.length) {
    grid.innerHTML = '';
    emptyState.classList.remove('hidden');
    return;
  }

  emptyState.classList.add('hidden');
  grid.innerHTML = records.map((record) => {
    const isSaved = state.library.includes(record.image_path);
    return `
      <article class="picto-card">
        <div class="picto-visual">
          <img src="${escapeAttribute(record.image_path)}" alt="${escapeAttribute(record.palabra)}">
        </div>
        <div class="picto-title">
          <h3>${escapeHtml(record.palabra)}</h3>
          <p>${escapeHtml(record.categoria_gramatical)} · ${escapeHtml(record.subcategoria || 'sin subcategoría')}</p>
        </div>
        <div class="picto-meta">
          <span>${escapeHtml(record.variante || 'sin variante')}</span>
          <span>${escapeHtml(record.categoria_semantica || 'general')}</span>
        </div>
        <div class="card-actions">
          <button class="secondary compact" data-save="${escapeAttribute(record.image_path)}">${isSaved ? 'Quitar' : 'Guardar'}</button>
          <a class="compact-download" href="${escapeAttribute(record.image_path)}" download>Descargar</a>
        </div>
      </article>
    `;
  }).join('');

  grid.querySelectorAll('[data-save]').forEach((button) => {
    button.addEventListener('click', () => {
      const path = button.dataset.save;
      if (state.library.includes(path)) {
        state.library = state.library.filter((item) => item !== path);
      } else {
        state.library.push(path);
      }
      persistLocalState();
      renderResults();
    });
  });
}

function persistLocalState() {
  saveJson('araia_requests', state.requests);
  saveJson('araia_feedback', state.feedback);
  saveJson('araia_library', state.library);
}

function populateFilters() {
  const categories = [...new Set(state.catalog.map((item) => item.categoria_gramatical).filter(Boolean))].sort();
  const subcategories = [...new Set(state.catalog.map((item) => item.subcategoria).filter(Boolean))].sort();

  document.getElementById('category-select').innerHTML = '<option value="">Todas</option>' + categories.map((item) => `<option value="${escapeAttribute(item)}">${escapeHtml(item)}</option>`).join('');
  document.getElementById('subcategory-select').innerHTML = '<option value="">Todas</option>' + subcategories.map((item) => `<option value="${escapeAttribute(item)}">${escapeHtml(item)}</option>`).join('');
}

function bindForms() {
  document.getElementById('search-input').addEventListener('input', (event) => {
    state.filters.q = event.target.value;
    render();
  });
  document.getElementById('category-select').addEventListener('change', (event) => {
    state.filters.categoria = event.target.value;
    render();
  });
  document.getElementById('subcategory-select').addEventListener('change', (event) => {
    state.filters.subcategoria = event.target.value;
    render();
  });
  document.getElementById('variant-select').addEventListener('change', (event) => {
    state.filters.variante = event.target.value;
    render();
  });

  document.getElementById('request-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const palabra = document.getElementById('request-word').value.trim();
    if (!palabra) return;
    state.requests.push({
      id: `${normalize(palabra)}-${Date.now()}`,
      palabra,
      categoria: document.getElementById('request-category').value.trim(),
      subcategoria: document.getElementById('request-subcategory').value.trim(),
      detalle: document.getElementById('request-detail').value.trim(),
      votes: 1,
      requests: 1,
      commentCount: 0,
      updatedAt: new Date().toISOString(),
    });
    event.target.reset();
    persistLocalState();
    renderRequests();
  });

  document.getElementById('feedback-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const texto = document.getElementById('feedback-text').value.trim();
    if (!texto) return;
    state.feedback.push({
      tipo: document.getElementById('feedback-type').value,
      palabra: document.getElementById('feedback-word').value.trim(),
      texto,
      createdAt: new Date().toISOString(),
    });
    event.target.reset();
    persistLocalState();
    renderFeedback();
  });
}

function escapeHtml(value) {
  return (value || '').replace(/[&<>\"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[char]));
}

function escapeAttribute(value) {
  return escapeHtml(value).replace(/'/g, '&#39;');
}

function render() {
  buildAlphabet();
  renderResults();
}

fetch('./catalogo_web.json')
  .then((response) => response.json())
  .then((payload) => {
    state.catalog = payload.records || [];
    populateFilters();
    bindForms();
    renderRecent();
    renderFeedback();
    renderRequests();
    render();
  })
  .catch(() => {
    document.getElementById('results-grid').innerHTML = '<p class="description">No se ha podido cargar el catálogo web.</p>';
  });
