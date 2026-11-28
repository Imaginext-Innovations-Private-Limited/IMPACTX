/**
 * Sahaaya AI - Scheme Discovery and Filtering Module
 * Interacts with /api/schemes and /api/schemes/categories
 */

let allLoadedSchemes = [];
let debounceTimer = null;

document.addEventListener('DOMContentLoaded', function () {
  loadCategories();
  loadSchemesFromQuery();
  setupFilterListeners();
  updateCompareBadge();
});

/**
 * Load filter categories from the backend.
 */
async function loadCategories() {
  try {
    const res = await fetch('/api/schemes/categories');
    if (!res.ok) return;
    const data = await res.json();
    if (data.success && data.categories) {
      const select = document.getElementById('categoryFilterSelect');
      if (!select) return;
      data.categories.forEach(cat => {
        const opt = document.createElement('option');
        opt.value = cat;
        opt.textContent = cat;
        select.appendChild(opt);
      });
    }
  } catch (err) {
    console.error('Failed to load categories:', err);
  }
}

/**
 * Fetch schemes from /api/schemes with active query params.
 */
async function fetchSchemes(params = {}) {
  const spinner = document.getElementById('loadingSpinner');
  const grid = document.getElementById('schemesGrid');
  const emptyAlert = document.getElementById('noSchemesAlert');
  const resultsCount = document.getElementById('resultsCount');

  if (spinner) spinner.classList.remove('d-none');

  const urlParams = new URLSearchParams(params);
  try {
    const res = await fetch(`/api/schemes?${urlParams.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (spinner) spinner.classList.add('d-none');

    if (data.success) {
      allLoadedSchemes = data.schemes || [];
      if (resultsCount) resultsCount.textContent = allLoadedSchemes.length;
      renderSchemes(allLoadedSchemes);

      if (allLoadedSchemes.length === 0) {
        if (emptyAlert) emptyAlert.classList.remove('d-none');
      } else {
        if (emptyAlert) emptyAlert.classList.add('d-none');
      }
    }
  } catch (err) {
    if (spinner) spinner.classList.add('d-none');
    console.error('Error fetching schemes:', err);
    if (grid) {
      grid.innerHTML = `
        <div class="col-12 text-center text-danger py-4">
          <i class="bi bi-exclamation-triangle fs-3 d-block mb-2"></i>
          Failed to load government schemes. Please check your connection or try again.
        </div>
      `;
    }
  }
}

/**
 * Render scheme cards into the DOM.
 */
function renderSchemes(schemes) {
  const grid = document.getElementById('schemesGrid');
  if (!grid) return;

  if (schemes.length === 0) {
    grid.innerHTML = '';
    return;
  }

  const comparedList = getComparedSlugs();

  grid.innerHTML = schemes.map(s => {
    const isCompared = comparedList.includes(s.slug);
    const levelBadgeClass = s.government_level === 'State' ? 'bg-primary' : 'bg-secondary';

    return `
      <div class="col-lg-4 col-md-6">
        <div class="sahaaya-card h-100 d-flex flex-column">
          <div class="sahaaya-card-header d-flex justify-content-between align-items-center">
            <span class="badge ${levelBadgeClass}">${s.government_level} Level</span>
            <span class="badge bg-light text-dark border">${s.category || 'General'}</span>
          </div>
          <div class="sahaaya-card-body flex-grow-1">
            <h5 class="fw-bold mb-1">${escapeHtml(s.name)}</h5>
            <div class="small text-muted mb-2"><i class="bi bi-building me-1"></i>${escapeHtml(s.department)}</div>
            <p class="text-secondary small mb-3 text-truncate-2" style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
              ${escapeHtml(s.description)}
            </p>
            <div class="p-2 rounded bg-light border small mb-3">
              <strong>Benefits:</strong> <span class="text-muted">${escapeHtml(s.benefits)}</span>
            </div>
            <div class="d-flex justify-content-between align-items-center small text-muted">
              <span><i class="bi bi-geo-alt me-1"></i>${escapeHtml(s.state || 'All India')}</span>
              <span class="badge-verified-official">
                <i class="bi bi-patch-check-fill"></i> Verified
              </span>
            </div>
          </div>
          <div class="p-3 bg-light border-top d-flex justify-content-between align-items-center gap-2">
            <div class="form-check form-check-inline m-0">
              <input class="form-check-input" type="checkbox" id="cmp_card_${s.slug}" value="${s.slug}" ${isCompared ? 'checked' : ''} onchange="toggleCompareSlug('${s.slug}')">
              <label class="form-check-label small text-muted" for="cmp_card_${s.slug}">Compare</label>
            </div>
            <div class="btn-group btn-group-sm">
              <a href="/schemes/${s.slug}" class="btn btn-outline-primary" onclick="markSchemeExplored('${s.slug}')">Details</a>
              <a href="/eligibility?scheme=${s.slug}" class="btn btn-sahaaya-teal">Eligible?</a>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Setup listeners for search input and dropdown filters.
 */
function setupFilterListeners() {
  const searchInput = document.getElementById('schemeSearchInput');
  const levelSelect = document.getElementById('levelFilterSelect');
  const catSelect = document.getElementById('categoryFilterSelect');
  const resetBtn = document.getElementById('resetFiltersBtn');

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        applyFilters();
      }, 300);
    });
  }

  if (levelSelect) {
    levelSelect.addEventListener('change', applyFilters);
  }

  if (catSelect) {
    catSelect.addEventListener('change', applyFilters);
  }

  if (resetBtn) {
    resetBtn.addEventListener('click', resetAllFilters);
  }
}

/**
 * Read query string and populate initial filters.
 */
function loadSchemesFromQuery() {
  const params = new URLSearchParams(window.location.search);
  const q = params.get('q') || '';
  const level = params.get('level') || '';
  const category = params.get('category') || '';

  const searchInput = document.getElementById('schemeSearchInput');
  const levelSelect = document.getElementById('levelFilterSelect');
  const catSelect = document.getElementById('categoryFilterSelect');

  if (searchInput && q) searchInput.value = q;
  if (levelSelect && level) levelSelect.value = level;
  if (catSelect && category) catSelect.value = category;

  applyFilters();
}

/**
 * Gather filter values and execute fetch.
 */
function applyFilters() {
  const q = document.getElementById('schemeSearchInput')?.value || '';
  const level = document.getElementById('levelFilterSelect')?.value || '';
  const category = document.getElementById('categoryFilterSelect')?.value || '';

  const params = {};
  if (q.trim()) params.q = q.trim();
  if (level) params.level = level;
  if (category) params.category = category;

  fetchSchemes(params);
}

/**
 * Reset all filter controls and reload.
 */
function resetAllFilters() {
  const searchInput = document.getElementById('schemeSearchInput');
  const levelSelect = document.getElementById('levelFilterSelect');
  const catSelect = document.getElementById('categoryFilterSelect');

  if (searchInput) searchInput.value = '';
  if (levelSelect) levelSelect.value = '';
  if (catSelect) catSelect.value = '';

  fetchSchemes({});
}

/**
 * Toggle scheme in comparison list (max 3).
 */
function toggleCompareSlug(slug) {
  let list = getComparedSlugs();
  const idx = list.indexOf(slug);
  if (idx > -1) {
    list.splice(idx, 1);
  } else {
    if (list.length >= 3) {
      showToast('You can compare a maximum of 3 schemes at a time.', 'warning');
      const chk = document.getElementById(`cmp_card_${slug}`);
      if (chk) chk.checked = false;
      return;
    }
    list.push(slug);
  }
  localStorage.setItem('sahaaya_compare_schemes', JSON.stringify(list));
  updateCompareBadge();
}

function getComparedSlugs() {
  try {
    return JSON.parse(localStorage.getItem('sahaaya_compare_schemes') || '[]');
  } catch (e) {
    return [];
  }
}

function updateCompareBadge() {
  const badge = document.getElementById('compareBadgeCount');
  if (badge) {
    badge.textContent = getComparedSlugs().length;
  }
}

function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
