/**
 * Sahaaya AI - Global Application Utilities
 * Handles session storage, explored schemes tracking, saved schemes, and toast notifications.
 */

// Storage Keys
const STORAGE_EXPLORED_KEY = 'sahaaya_explored_schemes';
const STORAGE_SAVED_KEY = 'sahaaya_saved_schemes';
const STORAGE_COMPARE_KEY = 'sahaaya_compare_schemes';
const STORAGE_SESSION_ID_KEY = 'sahaaya_conversation_id';

/**
 * Record a scheme slug as explored in the current browser session.
 */
function markSchemeExplored(slug) {
  if (!slug) return;
  try {
    let list = JSON.parse(localStorage.getItem(STORAGE_EXPLORED_KEY) || '[]');
    if (!list.includes(slug)) {
      list.push(slug);
      localStorage.setItem(STORAGE_EXPLORED_KEY, JSON.stringify(list));
    }
  } catch (e) {
    console.warn('Storage unavailable:', e);
  }
}

/**
 * Get count of explored schemes.
 */
function getExploredCount() {
  try {
    const list = JSON.parse(localStorage.getItem(STORAGE_EXPLORED_KEY) || '[]');
    return list.length;
  } catch (e) {
    return 0;
  }
}

/**
 * Get currently selected scheme slugs for comparison from localStorage.
 */
function getComparedSlugs() {
  try {
    const list = JSON.parse(localStorage.getItem(STORAGE_COMPARE_KEY) || '[]');
    return Array.isArray(list) ? list : [];
  } catch (e) {
    return [];
  }
}

/**
 * Toggle bookmarking a scheme in localStorage.
 */
function toggleSaveScheme(slug, name) {
  try {
    let saved = JSON.parse(localStorage.getItem(STORAGE_SAVED_KEY) || '[]');
    const existingIndex = saved.findIndex(item => item.slug === slug);
    const saveBtnText = document.getElementById('saveBtnText');

    if (existingIndex > -1) {
      saved.splice(existingIndex, 1);
      localStorage.setItem(STORAGE_SAVED_KEY, JSON.stringify(saved));
      if (saveBtnText) saveBtnText.textContent = 'Save Scheme';
      showToast(`Removed '${name}' from saved schemes.`, 'info');
    } else {
      saved.push({ slug, name, savedAt: new Date().toISOString() });
      localStorage.setItem(STORAGE_SAVED_KEY, JSON.stringify(saved));
      if (saveBtnText) saveBtnText.textContent = 'Scheme Saved';
      showToast(`Saved '${name}' to your dashboard.`, 'success');
    }
    updateDashboardStats();
  } catch (e) {
    console.error('Failed to update saved schemes:', e);
  }
}

/**
 * Check if scheme is saved and update button.
 */
function checkIfSchemeSaved(slug) {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_SAVED_KEY) || '[]');
    const isSaved = saved.some(item => item.slug === slug);
    const saveBtnText = document.getElementById('saveBtnText');
    if (saveBtnText) {
      saveBtnText.textContent = isSaved ? 'Scheme Saved' : 'Save Scheme';
    }
  } catch (e) {
    // ignore
  }
}

/**
 * Update Dashboard dynamic counters from localStorage.
 */
function updateDashboardStats() {
  const exploredElem = document.getElementById('exploredCount');
  if (exploredElem) {
    exploredElem.textContent = getExploredCount();
  }

  const savedListElem = document.getElementById('savedSchemesList');
  const savedBadge = document.getElementById('savedCountBadge');
  if (savedListElem) {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_SAVED_KEY) || '[]');
      if (savedBadge) savedBadge.textContent = saved.length;

      if (saved.length === 0) {
        savedListElem.innerHTML = `
          <div class="text-muted small text-center py-3">
            <i class="bi bi-bookmark-dash fs-3 d-block mb-1"></i>
            No saved schemes yet.<br>Click "Save" on any scheme details page to pin it here.
          </div>
        `;
      } else {
        savedListElem.innerHTML = `
          <div class="list-group list-group-flush small">
            ${saved.map(item => `
              <div class="list-group-item d-flex justify-content-between align-items-center px-0">
                <a href="/schemes/${item.slug}" class="fw-semibold text-dark text-decoration-none text-truncate" style="max-width: 220px;">
                  ${item.name}
                </a>
                <button class="btn btn-sm btn-link text-danger p-0" onclick="toggleSaveScheme('${item.slug}', '${item.name}')" title="Remove">
                  <i class="bi bi-x-circle"></i>
                </button>
              </div>
            `).join('')}
          </div>
        `;
      }
    } catch (e) {
      console.warn('Dashboard stats error:', e);
    }
  }
}

/**
 * Global Toast / Notification banner.
 */
function showToast(message, type = 'info') {
  const container = document.getElementById('globalAlertContainer');
  if (!container) return;

  const alertDiv = document.createElement('div');
  alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show shadow-sm`;
  alertDiv.role = 'alert';
  alertDiv.innerHTML = `
    <div class="d-flex align-items-center gap-2">
      <i class="bi bi-${type === 'success' ? 'check-circle-fill' : type === 'error' ? 'exclamation-octagon-fill' : 'info-circle-fill'}"></i>
      <div>${message}</div>
    </div>
    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
  `;
  container.appendChild(alertDiv);

  setTimeout(() => {
    alertDiv.classList.remove('show');
    setTimeout(() => alertDiv.remove(), 200);
  }, 4000);
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
  updateDashboardStats();
});
