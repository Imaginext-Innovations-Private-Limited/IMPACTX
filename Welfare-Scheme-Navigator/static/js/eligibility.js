/**
 * Sahaaya AI - Deterministic Eligibility Checker Frontend
 * Connects to /api/eligibility/check and /api/eligibility/check-all
 * Strictly preserves all 4 deterministic statuses.
 */

if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', function () {
    // Check if a pre-selected scheme was passed via query parameter (?scheme=slug)
    const urlParams = new URLSearchParams(window.location.search);
    const schemeParam = urlParams.get('scheme');
    if (schemeParam) {
      const schemeSelect = document.getElementById('schemeSelect');
      if (schemeSelect) {
        schemeSelect.value = schemeParam;
      }
    }

    const form = document.getElementById('eligibilityForm');
    if (form) {
      form.addEventListener('submit', handleEligibilitySubmit);
    }

    // Attach input event listeners to clear field errors as user types
    const inputs = [
      'applicantAge', 'applicantGender', 'applicantState', 'applicantCaste',
      'annualIncome', 'applicantOccupation', 'rationCardType', 'graduationYear',
      'landholdingAcres', 'electricityUnits'
    ];
    inputs.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('input', () => clearFieldValidation(id));
        el.addEventListener('change', () => clearFieldValidation(id));
      }
    });

    // Dynamic income zero confirmation handling
    const incomeInput = document.getElementById('annualIncome');
    const zeroConfirmBox = document.getElementById('zeroIncomeConfirmation');
    const zeroConfirmChk = document.getElementById('confirmZeroIncomeCheckbox');
    if (incomeInput) {
      const handleIncomeInput = function () {
        const val = incomeInput.value.trim();
        if (val !== '' && Number(val) === 0 && !isNaN(Number(val))) {
          if (zeroConfirmBox) zeroConfirmBox.classList.remove('d-none');
        } else {
          if (zeroConfirmBox) zeroConfirmBox.classList.add('d-none');
          if (zeroConfirmChk) zeroConfirmChk.checked = false;
        }
      };
      incomeInput.addEventListener('input', handleIncomeInput);
      incomeInput.addEventListener('change', handleIncomeInput);
    }
    if (zeroConfirmChk) {
      zeroConfirmChk.addEventListener('change', function () {
        if (zeroConfirmChk.checked) {
          clearFieldValidation('annualIncome');
        }
      });
    }
  });
}

/**
 * Clear validation state for an individual form control.
 */
function clearFieldValidation(fieldId) {
  const el = document.getElementById(fieldId);
  if (el) {
    el.classList.remove('is-invalid');
  }
  const alertBox = document.getElementById('formValidationAlert');
  if (alertBox) {
    // Only hide if no remaining invalid fields
    const invalidFields = document.querySelectorAll('#eligibilityForm .is-invalid');
    if (invalidFields.length === 0) {
      alertBox.classList.add('d-none');
    }
  }
}

/**
 * Validate citizen profile form inputs before submission.
 * Enforces strict boundary checks and displays clear visual indicators.
 * Preserves entered values without clearing or silent conversions.
 */
function validateEligibilityForm() {
  const errors = {};
  const currentYear = new Date().getFullYear();

  // Reset existing validation styling
  const form = document.getElementById('eligibilityForm');
  if (form) {
    const invalidEls = form.querySelectorAll('.is-invalid');
    invalidEls.forEach(el => el.classList.remove('is-invalid'));
  }
  const alertBox = document.getElementById('formValidationAlert');
  if (alertBox) alertBox.classList.add('d-none');

  // 1. Age Validation
  const ageEl = document.getElementById('applicantAge');
  if (ageEl && ageEl.value.trim() !== '') {
    const rawAge = ageEl.value.trim();
    if (rawAge.includes('.')) {
      errors.applicantAge = 'Please enter a valid applicant age (whole numbers only).';
    } else {
      const parsedAge = Number(rawAge);
      if (isNaN(parsedAge)) {
        errors.applicantAge = 'Please enter a valid applicant age.';
      } else if (parsedAge < 0) {
        errors.applicantAge = 'Please enter a valid applicant age (negative ages are not allowed).';
      } else if (parsedAge === 0) {
        errors.applicantAge = 'Please enter a valid applicant age (age cannot be zero).';
      } else if (parsedAge < 18) {
        errors.applicantAge = 'Please enter a valid applicant age (must be at least 18 years).';
      } else if (parsedAge > 120) {
        errors.applicantAge = 'Please enter a valid applicant age (maximum 120 years).';
      }
    }
  }

  // 2. Annual Household Income Validation
  const incomeEl = document.getElementById('annualIncome');
  const zeroConfirmBox = document.getElementById('zeroIncomeConfirmation');
  const zeroConfirmChk = document.getElementById('confirmZeroIncomeCheckbox');
  if (incomeEl && incomeEl.value.trim() !== '') {
    const rawIncome = incomeEl.value.trim();
    const parsedIncome = Number(rawIncome);
    if (isNaN(parsedIncome)) {
      errors.annualIncome = 'Annual household income must be numeric.';
      if (zeroConfirmBox) zeroConfirmBox.classList.add('d-none');
    } else if (parsedIncome < 0) {
      errors.annualIncome = 'Annual household income cannot be negative.';
      if (zeroConfirmBox) zeroConfirmBox.classList.add('d-none');
    } else if (parsedIncome === 0) {
      if (zeroConfirmBox) zeroConfirmBox.classList.remove('d-none');
      if (!zeroConfirmChk || !zeroConfirmChk.checked) {
        errors.annualIncome = 'Your annual household income is entered as ₹0. Please confirm that this is correct.';
      }
    } else {
      if (zeroConfirmBox) zeroConfirmBox.classList.add('d-none');
    }
  } else {
    if (zeroConfirmBox) zeroConfirmBox.classList.add('d-none');
  }

  // 3. Gender Validation
  const genderEl = document.getElementById('applicantGender');
  if (genderEl && genderEl.value) {
    const validGenders = ['Female', 'Male', 'Transgender', 'Other'];
    if (!validGenders.includes(genderEl.value)) {
      errors.applicantGender = 'Please select a valid gender option.';
    }
  }

  // 4. Social Category Validation
  const casteEl = document.getElementById('applicantCaste');
  if (casteEl && casteEl.value) {
    const validCastes = ['General', 'OBC', 'SC', 'ST', 'Minority'];
    if (!validCastes.includes(casteEl.value)) {
      errors.applicantCaste = 'Please select a valid social category.';
    }
  }

  // 5. Ration Card Type Validation
  const rationEl = document.getElementById('rationCardType');
  if (rationEl && rationEl.value) {
    const validRation = ['BPL', 'AAY', 'APL', 'None'];
    if (!validRation.includes(rationEl.value)) {
      errors.rationCardType = 'Please select a valid ration card type.';
    }
  }

  // 6. Graduation Year Validation
  const gradEl = document.getElementById('graduationYear');
  if (gradEl && gradEl.value.trim() !== '') {
    const rawGrad = gradEl.value.trim();
    const parsedGrad = Number(rawGrad);
    const maxFutureYear = currentYear + 1;
    if (isNaN(parsedGrad) || rawGrad.includes('.')) {
      errors.graduationYear = 'Graduation year must be a whole number.';
    } else if (parsedGrad < 1950 || parsedGrad > maxFutureYear) {
      errors.graduationYear = `Graduation year must be between 1950 and ${maxFutureYear}.`;
    }
  }

  // 7. Landholding Validation
  const landEl = document.getElementById('landholdingAcres');
  if (landEl && landEl.value.trim() !== '') {
    const parsedLand = Number(landEl.value.trim());
    if (isNaN(parsedLand) || parsedLand < 0) {
      errors.landholdingAcres = 'Landholding must be a non-negative number.';
    }
  }

  // 8. Electricity Units Validation
  const elecEl = document.getElementById('electricityUnits');
  if (elecEl && elecEl.value.trim() !== '') {
    const rawElec = elecEl.value.trim();
    const parsedElec = Number(rawElec);
    if (isNaN(parsedElec) || rawElec.includes('.') || parsedElec < 0) {
      errors.electricityUnits = 'Electricity units must be a non-negative whole number.';
    }
  }

  // Apply visual feedback for any identified errors
  const errorKeys = Object.keys(errors);
  if (errorKeys.length > 0) {
    errorKeys.forEach(fieldId => {
      const el = document.getElementById(fieldId);
      const feedbackEl = document.getElementById(`${fieldId}Feedback`);
      if (el) el.classList.add('is-invalid');
      if (feedbackEl) feedbackEl.textContent = errors[fieldId];
    });

    // Display form error banner
    if (alertBox) {
      const alertText = document.getElementById('formValidationAlertText');
      if (alertText) {
        alertText.textContent = errors[errorKeys[0]] || 'Please correct the highlighted fields before submitting.';
      }
      alertBox.classList.remove('d-none');
    }

    // Scroll first invalid element into view
    const firstInvalid = document.getElementById(errorKeys[0]);
    if (firstInvalid && typeof firstInvalid.scrollIntoView === 'function') {
      firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
      if (typeof firstInvalid.focus === 'function') firstInvalid.focus();
    }

    return { isValid: false, errors: errors };
  }

  return { isValid: true, errors: {} };
}

/**
 * Handle form submission and run eligibility evaluation.
 */
async function handleEligibilitySubmit(e) {
  e.preventDefault();

  // Run client-side validation first
  const validation = validateEligibilityForm();
  if (!validation.isValid) {
    return;
  }

  const schemeSelect = document.getElementById('schemeSelect')?.value || 'ALL';
  const initialCard = document.getElementById('initialPromptCard');
  const loadingCard = document.getElementById('evaluationLoading');
  const resultsContainer = document.getElementById('resultsContainer');
  const evaluateBtn = document.getElementById('evaluateBtn');

  // Build citizen profile payload strictly using non-sensitive fields
  const profile = {};

  const age = document.getElementById('applicantAge')?.value;
  if (age !== '' && !isNaN(age)) profile.age = parseInt(age, 10);

  const gender = document.getElementById('applicantGender')?.value;
  if (gender) profile.gender = gender;

  const state = document.getElementById('applicantState')?.value;
  if (state) profile.state = state;

  const caste = document.getElementById('applicantCaste')?.value;
  if (caste) profile.caste_category = caste;

  const income = document.getElementById('annualIncome')?.value;
  if (income !== '' && !isNaN(income)) profile.annual_household_income = parseInt(income, 10);

  const occupation = document.getElementById('applicantOccupation')?.value;
  if (occupation) profile.occupation = occupation;

  const rationCard = document.getElementById('rationCardType')?.value;
  if (rationCard) {
    profile.ration_card_type = rationCard;
    if (rationCard === 'BPL' || rationCard === 'AAY') {
      profile.is_bpl_card_holder = true;
    }
  }

  const gradYear = document.getElementById('graduationYear')?.value;
  if (gradYear !== '' && !isNaN(gradYear)) profile.graduation_year = parseInt(gradYear, 10);

  const femaleHead = document.getElementById('femaleHeadOfFamily')?.checked;
  if (femaleHead) profile.is_female_head_of_family = true;

  const isStudent = document.getElementById('isStudent')?.checked;
  if (isStudent) profile.is_student = true;

  const hasDisability = document.getElementById('hasDisability')?.checked;
  if (hasDisability) profile.has_disability = true;

  const landholding = document.getElementById('landholdingAcres')?.value;
  if (landholding !== '' && !isNaN(landholding)) profile.landholding_acres = parseFloat(landholding);

  const electricity = document.getElementById('electricityUnits')?.value;
  if (electricity !== '' && !isNaN(electricity)) profile.monthly_electricity_consumption_units = parseInt(electricity, 10);

  // Show loading state
  if (initialCard) initialCard.classList.add('d-none');
  if (resultsContainer) resultsContainer.classList.add('d-none');
  if (loadingCard) loadingCard.classList.remove('d-none');
  if (evaluateBtn) evaluateBtn.disabled = true;

  try {
    let res, data;
    if (schemeSelect === 'ALL') {
      res = await fetch('/api/eligibility/check-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile: profile })
      });
      data = await res.json();
    } else {
      res = await fetch('/api/eligibility/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug: schemeSelect, profile: profile })
      });
      data = await res.json();
    }

    if (!res.ok) {
      // Check if backend returned structured validation details
      if (data && data.error === 'Validation Error' && data.details) {
        // Map backend details back to form fields
        const fieldMap = {
          age: 'applicantAge',
          annual_household_income: 'annualIncome',
          gender: 'applicantGender',
          state: 'applicantState',
          caste_category: 'applicantCaste',
          ration_card_type: 'rationCardType',
          graduation_year: 'graduationYear',
          landholding_acres: 'landholdingAcres',
          monthly_electricity_consumption_units: 'electricityUnits',
        };
        Object.keys(data.details).forEach(key => {
          const fieldId = fieldMap[key] || key;
          const el = document.getElementById(fieldId);
          const feedbackEl = document.getElementById(`${fieldId}Feedback`);
          if (el) el.classList.add('is-invalid');
          if (feedbackEl) feedbackEl.textContent = data.details[key];
        });

        const alertBox = document.getElementById('formValidationAlert');
        const alertText = document.getElementById('formValidationAlertText');
        if (alertBox && alertText) {
          alertText.textContent = data.message || 'Validation error in submitted profile.';
          alertBox.classList.remove('d-none');
        }
      }
      throw new Error(data.message || 'Evaluation request failed');
    }

    if (schemeSelect === 'ALL') {
      renderAllSchemesResults(data.data);
    } else {
      renderSingleSchemeResult(data.data);
    }
  } catch (err) {
    console.error('Eligibility evaluation error:', err);
    if (resultsContainer) {
      resultsContainer.innerHTML = `
        <div class="alert alert-danger shadow-sm">
          <div class="fw-bold mb-1"><i class="bi bi-exclamation-octagon-fill me-1"></i> Evaluation Error</div>
          <div class="small">${escapeHtml(err.message || 'Failed to communicate with the eligibility engine.')}</div>
        </div>
      `;
      resultsContainer.classList.remove('d-none');
    }
  } finally {
    if (loadingCard) loadingCard.classList.add('d-none');
    if (resultsContainer) resultsContainer.classList.remove('d-none');
    if (evaluateBtn) evaluateBtn.disabled = false;
  }
}

/**
 * Render single scheme evaluation result card.
 */
function renderSingleSchemeResult(evalData) {
  const container = document.getElementById('resultsContainer');
  if (!container || !evalData) return;

  const status = evalData.overall_status;
  const statusCfg = getStatusConfig(status);

  container.innerHTML = `
    <div class="sahaaya-card p-4 mb-4 ${statusCfg.cardClass}">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
          <span class="badge ${statusCfg.badgeClass} fs-6 mb-1">${statusCfg.icon} ${statusCfg.title}</span>
          <h4 class="fw-bold m-0 text-dark">${escapeHtml(evalData.scheme_name)}</h4>
        </div>
        <a href="/schemes/${evalData.scheme_slug}" class="btn btn-sm btn-outline-primary">View Scheme</a>
      </div>

      <div class="p-3 rounded bg-white border mb-3 small">
        <strong>Explanation:</strong> ${escapeHtml(evalData.explanation)}
      </div>

      <!-- Passed Rules -->
      ${renderRulesSection('Satisfied Verified Conditions', evalData.rules_passed, 'success', 'bi-check-circle-fill')}

      <!-- Failed Rules -->
      ${renderRulesSection('Unsatisfied / Failed Conditions', evalData.rules_failed, 'danger', 'bi-x-circle-fill')}

      <!-- Missing Information Rules -->
      ${renderRulesSection('Missing Demographic Information', evalData.rules_needing_info, 'warning', 'bi-question-circle-fill')}

      <!-- Follow-up Questions -->
      ${renderFollowUpQuestions(evalData.next_recommended_questions)}

      <div class="d-flex gap-2 mt-4 pt-3 border-top">
        <a href="/documents/${evalData.scheme_slug}" class="btn btn-sahaaya-teal btn-sm">
          <i class="bi bi-folder-check me-1"></i> View Document Checklist
        </a>
        <a href="${evalData.official_url}" target="_blank" rel="noopener noreferrer" class="btn btn-outline-secondary btn-sm">
          <i class="bi bi-box-arrow-up-right me-1"></i> Official Portal
        </a>
      </div>
    </div>
  `;
}

/**
 * Render multi-scheme evaluation results summary and scheme cards.
 */
function renderAllSchemesResults(allData) {
  const container = document.getElementById('resultsContainer');
  if (!container || !allData) return;

  const grouped = allData.results_by_status || {};
  const eligibleList = allData.eligible_schemes || grouped.potentially_eligible || [];
  const needsInfoList = allData.schemes_needing_info || grouped.needs_more_information || [];
  const notEligibleList = allData.ineligible_schemes || grouped.not_eligible || [];
  const unverifiedList = allData.unverified_schemes || grouped.unable_to_verify || [];

  const summary = allData.summary || {
    potentially_eligible_count: eligibleList.length,
    needs_more_information_count: needsInfoList.length,
    not_eligible_count: notEligibleList.length,
    unable_to_verify_count: unverifiedList.length,
  };

  container.innerHTML = `
    <!-- Summary Header -->
    <div class="sahaaya-card p-3 mb-4">
      <h6 class="fw-bold mb-2"><i class="bi bi-speedometer2 text-primary me-2"></i>Deterministic Evaluation Summary</h6>
      <div class="row g-2 text-center small">
        <div class="col-3">
          <div class="p-2 rounded bg-success-subtle text-success border border-success-subtle">
            <div class="fw-bold fs-5">${summary.potentially_eligible_count ?? eligibleList.length}</div>
            <div>Potentially Eligible</div>
          </div>
        </div>
        <div class="col-3">
          <div class="p-2 rounded bg-warning-subtle text-warning-emphasis border border-warning-subtle">
            <div class="fw-bold fs-5">${summary.needs_more_information_count ?? needsInfoList.length}</div>
            <div>Needs More Info</div>
          </div>
        </div>
        <div class="col-3">
          <div class="p-2 rounded bg-danger-subtle text-danger border border-danger-subtle">
            <div class="fw-bold fs-5">${summary.not_eligible_count ?? notEligibleList.length}</div>
            <div>Not Eligible</div>
          </div>
        </div>
        <div class="col-3">
          <div class="p-2 rounded bg-secondary-subtle text-secondary border border-secondary-subtle">
            <div class="fw-bold fs-5">${summary.unable_to_verify_count ?? unverifiedList.length}</div>
            <div>Under Review</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Grouped Sections -->
    ${renderSchemeGroup('Potentially Eligible Schemes', eligibleList, 'success', 'bi-check-circle-fill')}
    ${renderSchemeGroup('Schemes Requiring Additional Information', needsInfoList, 'warning', 'bi-question-circle-fill')}
    ${renderSchemeGroup('Ineligible Schemes', notEligibleList, 'danger', 'bi-x-circle-fill')}
  `;
}

function renderSchemeGroup(title, list, theme, icon) {
  if (!list || list.length === 0) return '';
  return `
    <div class="mb-4">
      <h6 class="fw-bold text-${theme} mb-3"><i class="bi ${icon} me-1"></i> ${title} (${list.length})</h6>
      <div class="d-flex flex-column gap-3">
        ${list.map(item => `
          <div class="sahaaya-card p-3 border-start border-${theme} border-4">
            <div class="d-flex justify-content-between align-items-start mb-1">
              <div>
                <h6 class="fw-bold m-0 text-dark">${escapeHtml(item.scheme_name)}</h6>
                <span class="badge bg-light text-muted border small">${escapeHtml(item.scheme_slug)}</span>
              </div>
              <div class="btn-group btn-group-sm">
                <a href="/schemes/${item.scheme_slug}" class="btn btn-outline-primary">Details</a>
                <a href="/documents/${item.scheme_slug}" class="btn btn-outline-secondary">Docs</a>
              </div>
            </div>
            <p class="text-secondary small mb-2">${escapeHtml(item.explanation || '')}</p>
            ${item.rules_failed && item.rules_failed.length > 0 ? `
              <div class="small text-danger bg-danger-subtle p-2 rounded mb-2">
                <strong>Failed Condition:</strong> ${escapeHtml(item.rules_failed.map(r => r.description).join('; '))}
              </div>
            ` : ''}
            ${item.rules_needing_info && item.rules_needing_info.length > 0 ? `
              <div class="small text-warning-emphasis bg-warning-subtle p-2 rounded mb-2">
                <strong>Missing Info Needed:</strong> ${escapeHtml(item.rules_needing_info.map(r => r.description).join('; '))}
              </div>
            ` : ''}
            ${renderFollowUpQuestions(item.next_recommended_questions)}
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

function renderRulesSection(title, rules, color, icon) {
  if (!rules || rules.length === 0) return '';
  return `
    <div class="mb-3">
      <h6 class="fw-bold small text-${color} mb-2"><i class="bi ${icon} me-1"></i> ${title} (${rules.length})</h6>
      <div class="list-group list-group-flush small">
        ${rules.map(r => `
          <div class="list-group-item px-2 py-1 bg-transparent">
            <div class="fw-medium">${escapeHtml(r.rule_name || r.field_name)}: ${escapeHtml(r.description || '')}</div>
            ${r.citizen_value !== undefined ? `<div class="text-muted" style="font-size: 0.8rem;">Provided: <code>${escapeHtml(String(r.citizen_value))}</code> | Required: <code>${escapeHtml(r.operator)} ${escapeHtml(r.expected_value)}</code></div>` : ''}
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

/**
 * Safely extract a human-readable question or clarification string from an item.
 * Supports:
 * - String inputs: "What is the applicant's age?"
 * - Object inputs:
 *   - item.question: "What is the applicant's age?"
 *   - item.prompt: "..."
 *   - item.clarification: "..."
 *   - item.message: "..."
 *   - item.description: "..."
 *   - item.text: "..."
 *   - item.field_name / item.field: "Please provide your age in years."
 *   - item.rule_name / item.rule: "Please clarify criteria: Age limit."
 * Strictly eliminates "[object Object]", "undefined", "null", or empty strings.
 */
function extractClarificationText(item) {
  if (item === null || item === undefined) return '';

  if (typeof item === 'string') {
    const trimmed = item.trim();
    if (!trimmed || trimmed === '[object Object]' || trimmed.toLowerCase() === 'undefined' || trimmed.toLowerCase() === 'null') {
      return '';
    }
    return trimmed;
  }

  if (typeof item === 'object') {
    // 1. Check direct textual properties in priority order
    const directProps = ['question', 'prompt', 'clarification', 'message', 'description', 'text'];
    for (const prop of directProps) {
      if (item[prop] && typeof item[prop] === 'string') {
        const trimmed = item[prop].trim();
        if (trimmed && trimmed !== '[object Object]' && trimmed.toLowerCase() !== 'undefined' && trimmed.toLowerCase() !== 'null') {
          return trimmed;
        }
      }
    }

    // 2. Check field_name / field with friendly human formatting
    const field = item.field_name || item.field;
    if (field && typeof field === 'string' && field.trim()) {
      const cleanField = field.trim().replace(/_/g, ' ');
      return `Please provide details for ${cleanField}.`;
    }

    // 3. Check rule_name / rule
    const rule = item.rule_name || item.rule;
    if (rule && typeof rule === 'string' && rule.trim()) {
      return `Please clarify criteria: ${rule.trim()}.`;
    }
  }

  return '';
}

/**
 * Render recommended follow-up questions / clarifications.
 * Returns empty string if no valid readable questions exist, completely hiding the section.
 */
function renderFollowUpQuestions(questions) {
  if (!questions || !Array.isArray(questions) || questions.length === 0) return '';

  const validQuestions = [];
  for (const q of questions) {
    const text = extractClarificationText(q);
    if (text) {
      validQuestions.push(text);
    }
  }

  // If no valid readable questions exist, completely hide section
  if (validQuestions.length === 0) return '';

  return `
    <div class="mb-3 p-3 rounded bg-warning-subtle border border-warning-subtle" id="clarificationsSection">
      <div class="fw-bold text-warning-emphasis small mb-1">
        <i class="bi bi-chat-left-dots-fill me-1"></i> Recommended Clarifications:
      </div>
      <ul class="mb-0 ps-3 small text-secondary">
        ${validQuestions.map(text => `<li>${escapeHtml(text)}</li>`).join('')}
      </ul>
    </div>
  `;
}

function getStatusConfig(status) {
  switch (status) {
    case 'potentially_eligible':
      return {
        cardClass: 'status-card-eligible',
        badgeClass: 'bg-success',
        title: 'Potentially Eligible',
        icon: '<i class="bi bi-check-circle-fill"></i>'
      };
    case 'not_eligible':
      return {
        cardClass: 'status-card-not-eligible',
        badgeClass: 'bg-danger',
        title: 'Not Eligible',
        icon: '<i class="bi bi-x-circle-fill"></i>'
      };
    case 'needs_more_information':
      return {
        cardClass: 'status-card-needs-info',
        badgeClass: 'bg-warning text-dark',
        title: 'Needs More Information',
        icon: '<i class="bi bi-exclamation-triangle-fill"></i>'
      };
    default:
      return {
        cardClass: 'status-card-unable-to-verify',
        badgeClass: 'bg-secondary',
        title: 'Unable to Verify',
        icon: '<i class="bi bi-question-circle-fill"></i>'
      };
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

// Export for testing environments and browser window
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    extractClarificationText,
    renderFollowUpQuestions,
    getStatusConfig,
    escapeHtml,
  };
}
if (typeof window !== 'undefined') {
  window.extractClarificationText = extractClarificationText;
  window.renderFollowUpQuestions = renderFollowUpQuestions;
}
