/**
 * Sahaaya AI - Document Checklist Engine Integration
 * Interacts with /api/documents/<slug>
 * Allows citizens to track preparation progress without sensitive uploads.
 */

let currentChecklistData = null;
let collectedSet = new Set();

document.addEventListener('DOMContentLoaded', function () {
  const select = document.getElementById('schemeDocumentSelect');
  if (select) {
    select.addEventListener('change', function () {
      const slug = this.value;
      if (slug) {
        loadDocumentChecklist(slug);
      } else {
        hideChecklist();
      }
    });

    // If pre-selected on page load
    if (select.value) {
      loadDocumentChecklist(select.value);
    }
  }
});

/**
 * Load checklist for the specified scheme from /api/documents/<slug>.
 */
async function loadDocumentChecklist(slug) {
  const prompt = document.getElementById('noSchemeSelectedPrompt');
  const content = document.getElementById('checklistContent');
  const readinessCard = document.getElementById('readinessCard');

  collectedSet.clear();

  try {
    const res = await fetch(`/api/documents/${slug}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (data.success && data.data) {
      currentChecklistData = data.data;

      if (prompt) prompt.classList.add('d-none');
      if (content) content.classList.remove('d-none');
      if (readinessCard) readinessCard.classList.remove('d-none');

      renderChecklists(currentChecklistData);
      updateReadinessUI();
    }
  } catch (err) {
    console.error('Failed to load document checklist:', err);
    showToast('Failed to load document checklist for this scheme.', 'error');
  }
}

function hideChecklist() {
  const prompt = document.getElementById('noSchemeSelectedPrompt');
  const content = document.getElementById('checklistContent');
  const readinessCard = document.getElementById('readinessCard');

  if (prompt) prompt.classList.remove('d-none');
  if (content) content.classList.add('d-none');
  if (readinessCard) readinessCard.classList.add('d-none');
}

/**
 * Render mandatory and optional document lists into the DOM.
 */
function renderChecklists(data) {
  const mandatoryContainer = document.getElementById('mandatoryDocsList');
  const optionalContainer = document.getElementById('optionalDocsList');
  const mandatoryBadge = document.getElementById('mandatoryCountBadge');
  const optionalBadge = document.getElementById('optionalCountBadge');
  const portalBtn = document.getElementById('officialPortalBtn');

  if (mandatoryBadge) mandatoryBadge.textContent = data.mandatory_documents?.length || 0;
  if (optionalBadge) optionalBadge.textContent = data.optional_documents?.length || 0;
  if (portalBtn && data.official_url) portalBtn.href = data.official_url;

  if (mandatoryContainer) {
    if (!data.mandatory_documents || data.mandatory_documents.length === 0) {
      mandatoryContainer.innerHTML = '<div class="p-3 text-muted small">No mandatory documents listed.</div>';
    } else {
      mandatoryContainer.innerHTML = data.mandatory_documents.map(doc => `
        <div class="list-group-item p-3 d-flex align-items-start gap-3">
          <input class="form-check-input mt-1" type="checkbox" id="doc_chk_${doc.document_id}" value="${doc.document_id}" onchange="toggleDocumentCollected(${doc.document_id}, true)">
          <div class="flex-grow-1">
            <label class="form-check-label fw-semibold text-dark d-block mb-1" for="doc_chk_${doc.document_id}">
              ${escapeHtml(doc.document_name)}
            </label>
            <div class="text-secondary small mb-1">${escapeHtml(doc.description)}</div>
            <div class="text-muted small fst-italic" style="font-size: 0.8rem;">
              <i class="bi bi-file-text me-1"></i> ${escapeHtml(doc.source_reference)}
            </div>
          </div>
        </div>
      `).join('');
    }
  }

  if (optionalContainer) {
    if (!data.optional_documents || data.optional_documents.length === 0) {
      optionalContainer.innerHTML = '<div class="p-3 text-muted small">No optional documents listed.</div>';
    } else {
      optionalContainer.innerHTML = data.optional_documents.map(doc => `
        <div class="list-group-item p-3 d-flex align-items-start gap-3">
          <input class="form-check-input mt-1" type="checkbox" id="doc_chk_${doc.document_id}" value="${doc.document_id}" onchange="toggleDocumentCollected(${doc.document_id}, false)">
          <div class="flex-grow-1">
            <label class="form-check-label fw-semibold text-dark d-block mb-1" for="doc_chk_${doc.document_id}">
              ${escapeHtml(doc.document_name)}
            </label>
            <div class="text-secondary small mb-1">${escapeHtml(doc.description)}</div>
            <div class="text-muted small fst-italic" style="font-size: 0.8rem;">
              <i class="bi bi-file-text me-1"></i> ${escapeHtml(doc.source_reference)}
            </div>
          </div>
        </div>
      `).join('');
    }
  }
}

/**
 * Handle citizen toggling an item as collected.
 */
function toggleDocumentCollected(docId, isMandatory) {
  if (collectedSet.has(docId)) {
    collectedSet.delete(docId);
  } else {
    collectedSet.add(docId);
  }
  updateReadinessUI();
}

/**
 * Recompute readiness metrics and update progress bars.
 */
function updateReadinessUI() {
  if (!currentChecklistData) return;

  const mandatory = currentChecklistData.mandatory_documents || [];
  const totalMandatory = mandatory.length;

  let collectedMandatoryCount = 0;
  mandatory.forEach(doc => {
    if (collectedSet.has(doc.document_id)) {
      collectedMandatoryCount++;
    }
  });

  const percent = totalMandatory > 0 ? Math.round((collectedMandatoryCount / totalMandatory) * 100) : 100;
  const isReady = (collectedMandatoryCount === totalMandatory) && (totalMandatory > 0);

  const progressBar = document.getElementById('readinessProgressBar');
  const counterText = document.getElementById('collectedCounterText');
  const percentText = document.getElementById('percentageText');
  const statusBadge = document.getElementById('readinessStatusBadge');

  if (progressBar) {
    progressBar.style.width = `${percent}%`;
    progressBar.setAttribute('aria-valuenow', percent);
    if (isReady) {
      progressBar.className = 'progress-bar bg-success';
    } else {
      progressBar.className = 'progress-bar bg-warning';
    }
  }

  if (counterText) {
    counterText.textContent = `${collectedMandatoryCount} / ${totalMandatory} Mandatory collected`;
  }

  if (percentText) {
    percentText.textContent = `${percent}%`;
  }

  if (statusBadge) {
    if (isReady) {
      statusBadge.className = 'p-2 rounded text-center small fw-semibold mb-3 bg-success-subtle text-success border border-success-subtle';
      statusBadge.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> Ready to Apply on Official Portal';
    } else {
      const remaining = totalMandatory - collectedMandatoryCount;
      statusBadge.className = 'p-2 rounded text-center small fw-semibold mb-3 bg-warning-subtle text-warning-emphasis border border-warning-subtle';
      statusBadge.innerHTML = `<i class="bi bi-clock-history me-1"></i> ${remaining} mandatory document(s) remaining`;
    }
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
