/**
 * Sahaaya AI - Conversational Agent Interface
 * Interacts with /api/agent/chat, /api/agent/reset, and /api/agent/status
 * Supports multi-turn memory, markdown formatting, tool citations, and fallback detection.
 */

let activeConversationId = null;
let isWaitingForResponse = false;

document.addEventListener('DOMContentLoaded', function () {
  initializeSession();
  checkAgentStatus();
  setupChatInput();
});

/**
 * Initialize or restore conversation session ID.
 */
async function initializeSession() {
  activeConversationId = sessionStorage.getItem('sahaaya_chat_conv_id');
  if (!activeConversationId) {
    activeConversationId = 'sess_' + Math.random().toString(36).substring(2, 12);
    sessionStorage.setItem('sahaaya_chat_conv_id', activeConversationId);
  }
  const badge = document.getElementById('conversationIdBadge');
  if (badge) {
    badge.textContent = `Session: ${activeConversationId}`;
  }

  // Restore conversation history if existing session
  try {
    const res = await fetch(`/api/agent/session/${activeConversationId}`);
    if (res.ok) {
      const data = await res.json();
      if (data.success && data.session && Array.isArray(data.session.messages) && data.session.messages.length > 0) {
        const container = document.getElementById('chatMessages');
        if (container) {
          // Keep welcome message, then append prior history
          data.session.messages.forEach(msg => {
            if (msg.role === 'user') {
              appendMessageBubble('user', msg.content);
            } else {
              appendAgentResponse({
                assistant_message: msg.content,
                is_fallback_mode: false
              });
            }
          });
        }
      }
    }
  } catch (err) {
    console.debug('No prior session history restored:', err);
  }
}

/**
 * Inspect agent status from /api/agent/status.
 */
async function checkAgentStatus() {
  const statusBadge = document.getElementById('agentStatusBadge');
  const fallbackBanner = document.getElementById('fallbackNoticeBanner');
  const modelLabel = document.getElementById('modelNameLabel');

  try {
    const res = await fetch('/api/agent/status');
    if (!res.ok) throw new Error('Status endpoint unavailable');
    const data = await res.json();

    if (data.success && data.gemini_status) {
      const gs = data.gemini_status;
      if (modelLabel && gs.model) {
        modelLabel.textContent = gs.model;
      }

      if (gs.is_connected && gs.api_key_configured) {
        if (statusBadge) {
          statusBadge.className = 'badge bg-success';
          statusBadge.innerHTML = '<i class="bi bi-circle-fill me-1 small"></i> Live Gemini Ready';
        }
        if (fallbackBanner) fallbackBanner.classList.add('d-none');
      } else {
        if (statusBadge) {
          statusBadge.className = 'badge bg-secondary';
          statusBadge.innerHTML = '<i class="bi bi-info-circle me-1 small"></i> Standard Mode';
        }
        if (fallbackBanner) fallbackBanner.classList.remove('d-none');
      }
    }
  } catch (err) {
    console.warn('Agent status check error:', err);
    if (statusBadge) {
      statusBadge.className = 'badge bg-secondary';
      statusBadge.innerHTML = '<i class="bi bi-info-circle me-1 small"></i> Standard Mode';
    }
  }
}

/**
 * Setup event listeners for message textarea and Enter key.
 */
function setupChatInput() {
  const input = document.getElementById('chatInput');
  if (input) {
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendUserMessage();
      }
    });
  }
}

/**
 * Insert query into chat input and trigger send.
 */
function suggestQuery(text) {
  const input = document.getElementById('chatInput');
  if (input) {
    input.value = text;
    sendUserMessage();
  }
}

/**
 * Send user query to /api/agent/chat.
 */
async function sendUserMessage() {
  if (isWaitingForResponse) return;

  const input = document.getElementById('chatInput');
  const sendBtn = document.getElementById('sendMessageBtn');
  if (!input) return;

  const messageText = input.value.trim();
  if (!messageText) return;

  // Append user message to chat UI
  appendMessageBubble('user', messageText);
  input.value = '';

  // Disable controls during turn
  input.disabled = true;
  if (sendBtn) sendBtn.disabled = true;

  // Show typing indicator
  showTypingIndicator(true);
  isWaitingForResponse = true;

  try {
    const payload = {
      message: messageText,
      conversation_id: activeConversationId
    };

    const res = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (data.success) {
      // Update conversation ID if returned
      if (data.conversation_id) {
        activeConversationId = data.conversation_id;
        sessionStorage.setItem('sahaaya_chat_conv_id', activeConversationId);
        const badge = document.getElementById('conversationIdBadge');
        if (badge) badge.textContent = `Session: ${activeConversationId}`;
      }

      // Append assistant bubble
      appendAgentResponse(data);
    } else {
      appendErrorMessage(data.error || 'The agent could not process your request.');
    }
  } catch (err) {
    console.error('Chat error:', err);
    appendErrorMessage('Connection error communicating with the agent server.');
  } finally {
    showTypingIndicator(false);
    isWaitingForResponse = false;
    input.disabled = false;
    if (sendBtn) sendBtn.disabled = false;
    input.focus();
  }
}

/**
 * Append user message bubble.
 */
function appendMessageBubble(role, text) {
  const container = document.getElementById('chatMessages');
  if (!container) return;

  const bubble = document.createElement('div');
  bubble.className = `message-bubble ${role === 'user' ? 'user-message' : 'agent-message'}`;
  bubble.innerHTML = escapeHtml(text).replace(/\n/g, '<br>');
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

/**
 * Append agent message bubble with formatting, citations, and tools.
 */
function appendAgentResponse(data) {
  const container = document.getElementById('chatMessages');
  if (!container) return;

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble agent-message';

  const isFallback = Boolean(data.is_fallback_mode || data.source === 'fallback');

  let html = `
    <div class="fw-semibold text-primary mb-1 d-flex justify-content-between align-items-center">
      <span><i class="bi bi-stars me-1 text-info"></i> Welfare Scheme Navigator</span>
      ${isFallback ? '<span class="badge bg-light text-secondary border" style="font-size: 0.7rem;">Standard Response</span>' : '<span class="badge bg-success-subtle text-success border border-success-subtle" style="font-size: 0.7rem;">Verified</span>'}
    </div>
  `;

  // Render message content with markdown formatting
  const messageContent = data.assistant_message || data.response || '';
  html += `<div class="agent-text mb-2">${formatMarkdown(messageContent)}</div>`;

  // If tools were executed, show small tool badges
  const toolsList = data.tools_executed || (data.tools_invoked ? data.tools_invoked.map(t => typeof t === 'object' ? t.tool_name : t) : []);
  if (Array.isArray(toolsList) && toolsList.length > 0) {
    html += `
      <div class="mt-2 pt-2 border-top small text-muted">
        <i class="bi bi-gear-fill me-1 text-secondary"></i>
        <span>Tools executed: ${toolsList.map(t => `<code class="text-secondary">${escapeHtml(t)}</code>`).join(', ')}</span>
      </div>
    `;
  }

  // If follow-up questions are suggested
  if (data.follow_up_questions && data.follow_up_questions.length > 0) {
    html += `
      <div class="mt-2 pt-2 border-top">
        <div class="small fw-semibold text-secondary mb-1"><i class="bi bi-question-circle me-1"></i> Recommended Next Questions:</div>
        <div class="d-flex flex-wrap gap-1">
          ${data.follow_up_questions.map(q => `
            <button class="btn btn-outline-primary btn-sm rounded-pill py-0 px-2" style="font-size: 0.75rem;" onclick="suggestQuery('${escapeHtml(q).replace(/'/g, "\\'")}')">
              ${escapeHtml(q)}
            </button>
          `).join('')}
        </div>
      </div>
    `;
  }

  // If citations are available, render clickable citation pills
  if (data.citations && data.citations.length > 0) {
    html += `
      <div class="mt-2 pt-2 border-top">
        <div class="small fw-semibold text-secondary mb-1"><i class="bi bi-journal-bookmark me-1"></i> Official Citations:</div>
        <div class="d-flex flex-wrap">
          ${data.citations.map(c => `
            <a href="${escapeHtml(c.official_source_url || '#')}" target="_blank" rel="noopener noreferrer" class="citation-pill" title="${escapeHtml(c.document_title || '')}">
              <i class="bi bi-file-earmark-check text-success"></i>
              <span>${escapeHtml(c.document_title || 'Official Document')}</span>
              ${c.page_number ? `<span class="badge bg-white text-dark border">P.${c.page_number}</span>` : ''}
              ${c.verification_status ? `<span class="badge ${c.verification_status === 'Verified' ? 'bg-success-subtle text-success' : 'bg-warning-subtle text-warning-emphasis'}">${escapeHtml(c.verification_status)}</span>` : ''}
            </a>
          `).join('')}
        </div>
      </div>
    `;
  }

  // If disclaimer is attached
  if (data.disclaimer) {
    html += `
      <div class="mt-2 p-2 rounded bg-light border text-muted" style="font-size: 0.75rem;">
        <i class="bi bi-shield-exclamation me-1"></i> ${escapeHtml(data.disclaimer)}
      </div>
    `;
  }

  bubble.innerHTML = html;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

/**
 * Append error message bubble.
 */
function appendErrorMessage(text) {
  const container = document.getElementById('chatMessages');
  if (!container) return;

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble agent-message border-danger-subtle bg-danger-subtle';
  bubble.innerHTML = `
    <div class="text-danger small">
      <i class="bi bi-exclamation-triangle-fill me-1"></i>
      <strong>Error:</strong> ${escapeHtml(text)}
    </div>
  `;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

/**
 * Reset conversation session on server and client.
 */
async function resetConversation() {
  if (!confirm('Are you sure you want to reset this chat conversation?')) return;

  try {
    if (activeConversationId) {
      await fetch('/api/agent/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: activeConversationId })
      });
    }
  } catch (err) {
    console.warn('Reset request error:', err);
  }

  sessionStorage.removeItem('sahaaya_chat_conv_id');
  initializeSession();

  const container = document.getElementById('chatMessages');
  if (container) {
    container.innerHTML = `
      <div class="message-bubble agent-message">
        <div class="fw-semibold text-primary mb-1"><i class="bi bi-shield-check me-1"></i> Welfare Scheme Navigator</div>
        <p class="mb-2">Conversation has been reset. How may I help you with Karnataka or Central Government welfare schemes?</p>
      </div>
    `;
  }
  showToast('Chat session reset.', 'info');
}

function showTypingIndicator(show) {
  const ind = document.getElementById('chatTypingIndicator');
  if (ind) {
    if (show) {
      ind.classList.remove('d-none');
    } else {
      ind.classList.add('d-none');
    }
  }
}

/**
 * Basic markdown parser for agent responses.
 */
function formatMarkdown(text) {
  if (!text) return '';
  let str = escapeHtml(text);

  // Bold **text**
  str = str.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // Italics *text*
  str = str.replace(/\*(.*?)\*/g, '<em>$1</em>');

  // Unordered list items (- item or * item)
  str = str.replace(/(?:^|\n)[-*]\s+(.+)/g, '<li class="small">$1</li>');
  str = str.replace(/(<li.*<\/li>)/s, '<ul class="mb-2 ps-3">$1</ul>');

  // Code blocks `code`
  str = str.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Paragraph line breaks
  str = str.replace(/\n\n+/g, '</p><p class="mb-2">');
  str = str.replace(/\n/g, '<br>');

  return `<p class="mb-2">${str}</p>`;
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
