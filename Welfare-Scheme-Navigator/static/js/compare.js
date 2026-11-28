/**
 * Sahaaya AI - Scheme Comparison Frontend
 * Connects to /api/schemes/compare
 * Supports comparing 2 or 3 schemes side-by-side.
 */

let selectedSlugs = [];

/**
 * Safe retrieval of compared slugs from localStorage.
 */
function getComparedSlugs() {
  try {
    const list = JSON.parse(localStorage.getItem('sahaaya_compare_schemes') || '[]');
    return Array.isArray(list) ? list : [];
  } catch (e) {
    return [];
  }
}

/**
 * Display comparison error or alert banner.
 */
function showComparisonAlert(message, type = 'danger') {
  const alertEl = document.getElementById('comparisonAlert');
  const alertText = document.getElementById('comparisonAlertText');
  if (alertEl && alertText) {
    alertEl.className = `alert alert-${type} mb-4 py-2 small`;
    alertText.textContent = message;
    alertEl.classList.remove('d-none');
    if (typeof alertEl.scrollIntoView === 'function') {
      alertEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }
}

/**
 * Hide comparison alert banner.
 */
function hideComparisonAlert() {
  const alertEl = document.getElementById('comparisonAlert');
  if (alertEl) {
    alertEl.classList.add('d-none');
  }
}

document.addEventListener('DOMContentLoaded', function () {
  // Check if comparison was initiated from explore page or previous visit (via localStorage)
  const savedCompared = getComparedSlugs();
  const validSaved = Array.isArray(savedCompared)
    ? savedCompared.filter(s => typeof s === 'string' && s.trim())
    : [];

  // Deduplicate and cap at 3
  selectedSlugs = [...new Set(validSaved)].slice(0, 3);
  localStorage.setItem('sahaaya_compare_schemes', JSON.stringify(selectedSlugs));

  // Sync checkboxes
  selectedSlugs.forEach(slug => {
    const chk = document.getElementById(`cmp_${slug}`);
    if (chk) chk.checked = true;
  });

  updateCompareSelectionUI();

  // Bind checkbox events
  const checkboxes = document.querySelectorAll('.compare-checkbox');
  checkboxes.forEach(chk => {
    chk.addEventListener('change', function () {
      const slug = this.value;
      hideComparisonAlert();
      if (this.checked) {
        if (selectedSlugs.length >= 3) {
          this.checked = false;
          showToast('You can compare a maximum of 3 schemes at a time.', 'warning');
          showComparisonAlert('You can compare a maximum of 3 schemes at a time.', 'warning');
          return;
        }
        if (!selectedSlugs.includes(slug)) selectedSlugs.push(slug);
      } else {
        selectedSlugs = selectedSlugs.filter(s => s !== slug);
      }
      localStorage.setItem('sahaaya_compare_schemes', JSON.stringify(selectedSlugs));
      updateCompareSelectionUI();
    });
  });

  // If already at least 2 selected from previous navigation, auto-run comparison
  if (selectedSlugs.length >= 2) {
    executeComparison();
  }
});

function updateCompareSelectionUI() {
  const countText = document.getElementById('selectedCountText');
  const runBtn = document.getElementById('runCompareBtn');

  if (countText) countText.textContent = selectedSlugs.length;
  if (runBtn) {
    runBtn.disabled = selectedSlugs.length < 2;
  }
}

function clearSelectedCompare() {
  selectedSlugs = [];
  localStorage.removeItem('sahaaya_compare_schemes');
  const checkboxes = document.querySelectorAll('.compare-checkbox');
  checkboxes.forEach(chk => chk.checked = false);
  updateCompareSelectionUI();
  hideComparisonAlert();

  const tableWrapper = document.getElementById('comparisonTableWrapper');
  const notesBox = document.getElementById('comparisonNotesBox');
  if (tableWrapper) tableWrapper.classList.add('d-none');
  if (notesBox) notesBox.classList.add('d-none');
}

/**
 * Execute side-by-side comparison for 2 or 3 selected schemes.
 */
async function executeComparison() {
  hideComparisonAlert();

  // Deduplicate before submission
  selectedSlugs = [...new Set(selectedSlugs)];

  if (selectedSlugs.length < 2) {
    const msg = 'Please select at least 2 schemes to compare (up to 3).';
    showToast(msg, 'warning');
    showComparisonAlert(msg, 'warning');
    return;
  }

  if (selectedSlugs.length > 3) {
    selectedSlugs = selectedSlugs.slice(0, 3);
    localStorage.setItem('sahaaya_compare_schemes', JSON.stringify(selectedSlugs));
  }

  const loading = document.getElementById('comparisonLoading');
  const tableWrapper = document.getElementById('comparisonTableWrapper');
  const notesBox = document.getElementById('comparisonNotesBox');
  const runBtn = document.getElementById('runCompareBtn');

  if (loading) loading.classList.remove('d-none');
  if (tableWrapper) tableWrapper.classList.add('d-none');
  if (notesBox) notesBox.classList.add('d-none');
  if (runBtn) runBtn.disabled = true;

  try {
    const res = await fetch('/api/schemes/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slugs: selectedSlugs })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.error || data.message || 'Failed to compare schemes');
    }

    if (data.schemes && data.schemes.length >= 2) {
      renderComparisonTable(data.schemes);
      renderComparisonNotes(data.comparison_notes);
      if (tableWrapper) tableWrapper.classList.remove('d-none');
      if (notesBox) notesBox.classList.remove('d-none');
    } else {
      throw new Error('Comparison data could not be retrieved for the selected schemes.');
    }
  } catch (err) {
    console.error('Comparison error:', err);
    showToast(err.message || 'Error executing comparison.', 'error');
    showComparisonAlert(err.message || 'Error executing comparison.', 'danger');
  } finally {
    if (loading) loading.classList.add('d-none');
    if (runBtn) runBtn.disabled = selectedSlugs.length < 2;
  }
}

function renderComparisonTable(schemes) {
  const thead = document.getElementById('comparisonTableHead');
  const tbody = document.getElementById('comparisonTableBody');
  const badge = document.getElementById('comparedCountBadge');

  if (badge) badge.textContent = `${schemes.length} Schemes`;

  // Header Row: Feature | Scheme 1 | Scheme 2 | Scheme 3
  const colWidth = (80 / schemes.length).toFixed(1);
  thead.innerHTML = `
    <tr>
      <th style="width: 20%; background-color: #f8fafc;">Feature</th>
      ${schemes.map(s => `
        <th class="text-center" style="width: ${colWidth}%;">
          <div class="fw-bold fs-6 text-primary mb-1">${escapeHtml(s.scheme_name)}</div>
          <span class="badge ${s.government_level === 'State' ? 'bg-primary' : 'bg-secondary'} me-1">${s.government_level} Level</span>
          <span class="badge bg-light text-dark border">${escapeHtml(s.category)}</span>
        </th>
      `).join('')}
    </tr>
  `;

  // Rows to compare
  const rows = [
    {
      label: 'Department',
      render: s => `<div class="small fw-medium">${escapeHtml(s.department)}</div>`
    },
    {
      label: 'Government Level & State',
      render: s => `<div class="small">${escapeHtml(s.government_level)} (${escapeHtml(s.state)})</div>`
    },
    {
      label: 'Benefits',
      render: s => `<div class="p-2 rounded bg-light small">${escapeHtml(s.benefits)}</div>`
    },
    {
      label: 'Key Eligibility Criteria',
      render: s => `
        <ul class="ps-3 mb-0 small text-secondary">
          ${(s.key_eligibility_criteria || []).map(r => `<li>${escapeHtml(r)}</li>`).join('')}
        </ul>
      `
    },
    {
      label: 'Mandatory Documents',
      render: s => `
        <ul class="ps-3 mb-0 small text-secondary">
          ${(s.mandatory_documents || []).map(d => `<li>${escapeHtml(d)}</li>`).join('')}
        </ul>
      `
    },
    {
      label: 'Official Links',
      render: s => `
        <div class="d-flex flex-column gap-1">
          <a href="${s.official_portal_url}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-outline-primary">
            <i class="bi bi-box-arrow-up-right me-1"></i> Official Portal
          </a>
          <a href="/schemes/${s.scheme_slug}" class="btn btn-sm btn-sahaaya-teal">
            View Full Details
          </a>
        </div>
      `
    }
  ];

  tbody.innerHTML = rows.map(r => `
    <tr>
      <td class="fw-bold bg-light small align-middle">${r.label}</td>
      ${schemes.map(s => `<td>${r.render(s)}</td>`).join('')}
    </tr>
  `).join('');
}

function renderComparisonNotes(notes) {
  const notesList = document.getElementById('comparisonNotesList');
  if (!notesList || !notes) return;
  notesList.innerHTML = notes.map(n => `<li>${escapeHtml(n)}</li>`).join('');
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
