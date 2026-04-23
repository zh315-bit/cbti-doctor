const API_BASE = `${location.protocol}//${location.hostname}:5000/api`;
const SESSION_KEY = 'cbti_session_id';

const els = {
  messages: document.getElementById('messages'),
  input: document.getElementById('user-input'),
  send: document.getElementById('send-btn'),
  reset: document.getElementById('reset-btn'),
  backendStatus: document.getElementById('backend-status'),
  sessionId: document.getElementById('session-id'),
};

function getSessionId() {
  return localStorage.getItem(SESSION_KEY) || '';
}

function setSessionId(id) {
  localStorage.setItem(SESSION_KEY, id);
  els.sessionId.textContent = id ? `会话: ${id}` : '';
}

// 对助手回复进行格式化：将 **text** 渲染为加粗并隐藏星号，同时做安全转义
function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatAssistantText(raw) {
  if (!raw) return '';
  const regex = /\*\*([\s\S]+?)\*\*/g; // 匹配 **...**
  let last = 0;
  let html = '';
  let m;
  while ((m = regex.exec(raw)) !== null) {
    const before = raw.slice(last, m.index);
    html += escapeHtml(before).replace(/\n/g, '<br/>');
    const bold = m[1];
    html += '<strong>' + escapeHtml(bold).replace(/\n/g, '<br/>') + '</strong>';
    last = regex.lastIndex;
  }
  html += escapeHtml(raw.slice(last)).replace(/\n/g, '<br/>');
  return html;
}

function appendMessage(role, text) {
  const div = document.createElement('div');
  div.className = `msg msg-${role}`;
  if (role === 'assistant') {
    div.innerHTML = formatAssistantText(text);
  } else {
    div.textContent = text;
  }
  els.messages.appendChild(div);
  els.messages.scrollTop = els.messages.scrollHeight;
}

async function healthCheck() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      els.backendStatus.textContent = '后端已连接';
      els.backendStatus.className = 'badge ok';
    } else {
      throw new Error('not ok');
    }
  } catch (e) {
    els.backendStatus.textContent = '后端未连接';
    els.backendStatus.className = 'badge warn';
  }
}

async function postChat(message) {
  const sessionId = getSessionId();
  const resp = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId || undefined }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.error || '请求失败');
  }
  return resp.json();
}

async function resetSession() {
  const sessionId = getSessionId();
  if (!sessionId) {
    setSessionId('');
    return;
  }
  try {
    await fetch(`${API_BASE}/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    });
  } catch (e) {
    // ignore
  }
  setSessionId('');
}

async function handleSend() {
  const text = els.input.value.trim();
  if (!text) return;
  appendMessage('user', text);
  els.input.value = '';
  els.send.disabled = true;
  els.send.textContent = '发送中...';

  try {
    const data = await postChat(text);
    if (data.session_id && !getSessionId()) {
      setSessionId(data.session_id);
    } else if (data.session_id && getSessionId() !== data.session_id) {
      setSessionId(data.session_id);
    }
    appendMessage('assistant', data.assistant || '(无响应)');
    if (Array.isArray(data.tools_used) && data.tools_used.length) {
      appendToolsUsed(data.tools_used);
    }
  } catch (e) {
    appendMessage('assistant', `请求失败：${e.message}`);
  } finally {
    els.send.disabled = false;
    els.send.textContent = '发送';
  }
}

function prettyToolName(name) {
  switch (name) {
    case 'dialogue_summary':
      return '对话总结';
    case 'negative_thinking_record':
      return '负性思维记录';
    case 'retrieval_augmentation_generation':
      return 'RAG检索';
    default:
      return name;
  }
}

function appendToolsUsed(tools) {
  const div = document.createElement('div');
  div.className = 'msg msg-tools';
  const names = tools.map(prettyToolName);
  div.textContent = `调用工具：${names.join('、')}`;
  els.messages.appendChild(div);
  els.messages.scrollTop = els.messages.scrollHeight;
}


function wireEvents() {
  els.send.addEventListener('click', handleSend);
  els.input.addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter') {
      handleSend();
    }
  });
  els.reset.addEventListener('click', async () => {
    await resetSession();
    els.messages.innerHTML = '';
    appendMessage('assistant', '会话已重置，我们可以重新开始。');
  });
}

(async function init() {
  wireEvents();
  setSessionId(getSessionId());
  await healthCheck();
})();