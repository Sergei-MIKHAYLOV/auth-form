// js/admin.js
// Модуль админ-панели

const ADMIN_API_BASE = '';

// Состояние
let adminState = {
  users: [],
  roles: [],
  rules: [],
  currentUser: null
};

// ==================== ХЕЛПЕРЫ ====================

async function authFetch(url, options = {}) {
  const token = localStorage.getItem('authToken');
  const headers = {
    'Authorization': `Bearer ${token}`,
    ...options.headers
  };
  
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  
  const response = await fetch(url, { ...options, headers });
  
  if (response.status === 401) {
    localStorage.removeItem('authToken');
    window.location.href = '/';
    throw new Error('Сессия истекла');
  }
  
  if (response.status === 403) {
    throw new Error('Недостаточно прав');
  }
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Ошибка запроса');
  }
  
  return response.json();
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ==================== ИНИЦИАЛИЗАЦИЯ ====================

function initAdminModule() {
  setupAdminModalHandlers();
  setupTabHandlers();
  setupActionHandlers();
}

// ==================== МОДАЛКА ====================

function setupAdminModalHandlers() {
  const modal = document.getElementById('adminModal');
  const closeBtn = document.getElementById('adminModalClose');
  const overlay = document.getElementById('adminModal');
  
  closeBtn?.addEventListener('click', () => {
    modal?.classList.remove('show');
  });
  
  overlay?.addEventListener('click', (e) => {
    if (e.target === overlay) {
      modal?.classList.remove('show');
    }
  });
  
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal?.classList.contains('show')) {
      modal.classList.remove('show');
    }
  });
}

// ==================== ВКЛАДКИ ====================

// # исправлено: ограничил селектор только контентом внутри #adminModal
function setupTabHandlers() {
  document.querySelectorAll('.admin-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.admin-tab-btn').forEach(b => b.classList.remove('active'));
      // 🔧 Только вкладки внутри основной админки, не затрагиваем модальные окна
      document.querySelectorAll('#adminModal .admin-tab-content').forEach(c => c.classList.remove('active'));
      
      btn.classList.add('active');
      const tabId = btn.dataset.tab;
      document.getElementById(`admin${tabId.charAt(0).toUpperCase() + tabId.slice(1)}Tab`)?.classList.add('active');
      
      loadTabData(tabId);
    });
  });
}

async function loadTabData(tab) {
  if (tab === 'users') {
    await loadUsers();
  } else if (tab === 'roles') {
    await loadRoles();
  } else if (tab === 'rules') {
    await loadRules();
  }
}

// ==================== ЗАГРУЗКА ДАННЫХ ====================

// # исправлено: пользователи не загружаются при пустом поиске
async function loadUsers(query = '') {
  try {
    // 🔧 Если запрос пустой — показываем пустую таблицу, не делаем API-запрос
    if (!query) {
      adminState.users = [];
      renderUsersTable();
      return;
    }
    
    const params = new URLSearchParams();
    params.set('email', query);
    
    const url = `${ADMIN_API_BASE}/admin/users/search?${params.toString()}`;
    const data = await authFetch(url);
    
    adminState.users = data.users || [];
    renderUsersTable();
    
  } catch (error) {
    console.error('Error loading users:', error);
    showToast(error.message || 'Не удалось загрузить пользователей');
  }
}

// # исправлено: loadRoles использует description из БД
async function loadRoles() {
  try {
    const data = await authFetch(`${ADMIN_API_BASE}/admin/roles/`);
    const rawRoles = data.roles || [];
    
    // 🔧 Берём description из API
    adminState.roles = rawRoles.map(r => ({
      id: r.id,
      name: r.name,
      description: r.description || ''
    }));
    
    renderRolesTable();
  } catch (error) {
    console.error('Error loading roles:', error);
    showToast(error.message || 'Не удалось загрузить роли');
  }
}

async function loadRules() {
  try {
    const data = await authFetch(`${ADMIN_API_BASE}/admin/access-rules`);
    adminState.rules = data.rules || [];
    renderRulesTable();
  } catch (error) {
    console.error('Error loading rules:', error);
    showToast(error.message || 'Не удалось загрузить правила');
  }
}

// ==================== РЕНДЕРИНГ ====================

function renderUsersTable() {
  const tbody = document.getElementById('adminUsersTableBody');
  const empty = document.getElementById('adminUsersEmpty');
  
  if (!tbody) return;
  
  if (adminState.users.length === 0) {
    tbody.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  
  empty.style.display = 'none';
  
  // 🔧 Проверяем роль текущего пользователя
  const userRoles = JSON.parse(localStorage.getItem('userRoles') || '[]');
  const isAdmin = userRoles.includes('admin');
  
  tbody.innerHTML = adminState.users.map(user => `
    <tr>
      <td>${user.id}</td>
      <td>${escapeHtml(user.name)}</td>
      <td>${escapeHtml(user.email)}</td>
      <td>${user.roles?.map(r => `<span class="status-badge">${r}</span>`).join(' ') || '-'}</td>
      <td>
        <span class="status-badge ${user.is_active ? 'status-active' : 'status-inactive'}">
          ${user.is_active ? 'Активен' : 'Заблокирован'}
        </span>
      </td>
      <td>
        ${isAdmin ? `<button class="admin-action-btn" data-action="edit-user" data-id="${user.id}">✏️</button>` : ''}
        <button class="admin-action-btn danger" data-action="toggle-user" data-id="${user.id}">
          ${user.is_active ? '🚫 В блок.' : 'Разблок.'}
        </button>
      </td>
    </tr>
  `).join('');
}

function renderRolesTable() {
  const tbody = document.getElementById('adminRolesTableBody');
  if (!tbody) return;
  
  tbody.innerHTML = adminState.roles.map(role => `
    <tr>
      <td>${role.id}</td>
      <td><strong>${escapeHtml(role.name)}</strong></td>
      <td>${escapeHtml(role.description || '-')}</td>
      <td>
        <button class="admin-action-btn" data-action="edit-role" data-id="${role.id}">✏️</button>
        <button class="admin-action-btn danger" data-action="delete-role" data-id="${role.id}">🗑️</button>
      </td>
    </tr>
  `).join('');
}

function getPermissionIcon(permission, allPermission) {
  if (allPermission) {
    return '♾️';  // Бесконечность для _all_permission
  }
  return permission ? '✔️' : '❌';
}


function renderRulesTable() {
  const tbody = document.getElementById('adminRulesTableBody');
  if (!tbody) return;
  
  tbody.innerHTML = adminState.rules.map(rule => `
    <tr>
      <td><span class="status-badge">${escapeHtml(rule.role_name)}</span></td>
      <td>${escapeHtml(rule.resource_name)}</td>
      <td title="${rule.read_all_permission ? 'Чтение всех' : 'Чтение'}">${getPermissionIcon(rule.read_permission, rule.read_all_permission)}</td>
      <td title="${rule.create_all_permission ? 'Создание всех' : 'Создание'}">${getPermissionIcon(rule.create_permission, rule.create_all_permission)}</td>
      <td title="${rule.update_all_permission ? 'Обновление всех' : 'Обновление'}">${getPermissionIcon(rule.update_permission, rule.update_all_permission)}</td>
      <td title="${rule.delete_all_permission ? 'Удаление всех' : 'Удаление'}">${getPermissionIcon(rule.delete_permission, rule.delete_all_permission)}</td>
      <td>
        <button class="admin-action-btn" data-action="edit-rule" data-id="${rule.id}">✏️</button>
        <button class="admin-action-btn danger" data-action="delete-rule" data-id="${rule.id}">🗑️</button>
      </td>
    </tr>
  `).join('');
}

// ==================== ОБРАБОТЧИКИ ДЕЙСТВИЙ ====================

function setupActionHandlers() {
  document.getElementById('refreshUsersBtn')?.addEventListener('click', loadUsers);
  
  const searchInput = document.getElementById('adminUserSearch');
  searchInput?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      loadUsers(e.target.value.trim());
    }
  });
  
  document.getElementById('clearSearchBtn')?.addEventListener('click', () => {
    const input = document.getElementById('adminUserSearch');
    if (input) {
      input.value = '';
      adminState.users = [];
      renderUsersTable();
    }
  });
  
  document.getElementById('adminUsersTableBody')?.addEventListener('click', handleUserAction);
  document.getElementById('adminRolesTableBody')?.addEventListener('click', handleRoleAction);
  document.getElementById('adminRulesTableBody')?.addEventListener('click', handleRuleAction);
  
  // 🔧 Было: () => showAddRoleForm()
  // 🔧 Стало:
  document.getElementById('addRoleBtn')?.addEventListener('click', () => showAddRoleModal());
  
  // 🔧 Было: () => showAddRuleForm()
  // 🔧 Стало:
  document.getElementById('addRuleBtn')?.addEventListener('click', () => showAddRuleModal());
}

function handleUserAction(e) {
  const btn = e.target.closest('.admin-action-btn');
  if (!btn) return;
  
  const action = btn.dataset.action;
  const id = parseInt(btn.dataset.id);
  
  if (action === 'edit-user') {
    editUser(id);
  } else if (action === 'toggle-user') {
    toggleUserStatus(id);
  }
}

function handleRoleAction(e) {
  const btn = e.target.closest('.admin-action-btn');
  if (!btn) return;
  
  const action = btn.dataset.action;
  const id = parseInt(btn.dataset.id);
  
  if (action === 'edit-role') {
    editRole(id);
  } else if (action === 'delete-role') {
    deleteRole(id);
  }
}

function handleRuleAction(e) {
  const btn = e.target.closest('.admin-action-btn');
  if (!btn) return;
  
  const action = btn.dataset.action;
  const id = parseInt(btn.dataset.id);
  
  if (action === 'edit-rule') {
    editRule(id);
  } else if (action === 'delete-rule') {
    deleteRule(id);
  }
}

// ==================== ДЕЙСТВИЯ — ПОЛЬЗОВАТЕЛИ ====================

function editUser(id) {
  const user = adminState.users.find(u => u.id === id);
  if (!user) return;
  
  showEditUserRolesModal(id, user.name, user.roles || []);
}

// # исправлено: используем showConfirmModal вместо confirm()
async function toggleUserStatus(id) {
  const user = adminState.users.find(u => u.id === id);
  if (!user) return;
  
  const newStatus = !user.is_active;
  
  showConfirmModal(
    `${newStatus ? 'Разблокировать' : 'Заблокировать'} пользователя`,
    `Вы действительно хотите ${newStatus ? 'разблокировать' : 'заблокировать'} пользователя ${user.name}?`,
    async () => {
      try {
        const formData = new FormData();
        formData.append('is_active', newStatus.toString());
        
        await authFetch(`${ADMIN_API_BASE}/admin/users/${id}/status`, {
          method: 'PATCH',
          body: formData
        });
        
        user.is_active = newStatus;
        renderUsersTable();
        showToast(`Пользователь ${newStatus ? 'разблокирован' : 'заблокирован'}`);
      } catch (error) {
        console.error('Error toggling user:', error);
        showToast(error.message || 'Не удалось изменить статус');
      }
    }
  );
}

// ==================== ДЕЙСТВИЯ — РОЛИ ====================

function editRole(id) {
  const role = adminState.roles.find(r => r.id === id);
  if (!role) return;
  
  showEditRoleModal(id, role.name, role.description);
}

// # исправлено: используем showConfirmModal вместо confirm()
async function deleteRole(id) {
  const role = adminState.roles.find(r => r.id === id);
  if (!role) return;
  
  showConfirmModal(
    'Удалить роль',
    `Удалить роль "${role.name}"? Это действие нельзя отменить.`,
    async () => {
      try {
        await authFetch(`${ADMIN_API_BASE}/admin/roles/${id}`, {
          method: 'DELETE'
        });
        
        adminState.roles = adminState.roles.filter(r => r.id !== id);
        renderRolesTable();
        showToast('Роль удалена');
      } catch (error) {
        console.error('Error deleting role:', error);
        showToast(error.message || 'Не удалось удалить роль');
      }
    }
  );
}


// ==================== ДЕЙСТВИЯ — ПРАВИЛА ====================

function editRule(id) {
  const rule = adminState.rules.find(r => r.id === id);
  if (!rule) return;
  
  showEditRuleModal(id, rule);
}

// # исправлено: используем showConfirmModal вместо confirm()
async function deleteRule(id) {
  showConfirmModal(
    'Удалить правило',
    'Удалить это правило доступа?',
    async () => {
      try {
        await authFetch(`${ADMIN_API_BASE}/admin/access-rules/${id}`, {
          method: 'DELETE'
        });
        
        adminState.rules = adminState.rules.filter(r => r.id !== id);
        renderRulesTable();
        showToast('Правило удалено');
      } catch (error) {
        console.error('Error deleting rule:', error);
        showToast(error.message || 'Не удалось удалить правило');
      }
    }
  );
}


// ==================== МОДАЛЬНЫЕ ОКНА ====================

function showEditUserRolesModal(userId, userName, currentRoles) {
  const modal = document.getElementById('editUserRolesModal');
  if (!modal) {
    showToast('Форма редактирования ролей в разработке');
    return;
  }
  
  document.getElementById('editUserRolesTitle').textContent = `Роли: ${userName}`;
  document.getElementById('editUserRolesUserId').value = userId;
  
  loadAvailableRolesForModal(currentRoles);
  
  modal.classList.add('show');
}

function loadAvailableRolesForModal(currentRoles) {
  const container = document.getElementById('editUserRolesList');
  if (!container) return;
  
  container.innerHTML = adminState.roles.map(role => `
    <div class="permission-item">
      <input type="checkbox" id="role_${role.id}" 
             ${currentRoles.includes(role.name) ? 'checked' : ''} 
             data-role-id="${role.id}" 
             data-role-name="${role.name}">
      <label for="role_${role.id}">${role.name}</label>
    </div>
  `).join('');
}

// # исправлено: передаём description в модальное окно
function showEditRoleModal(roleId, roleName, roleDescription = '') {
  const modal = document.getElementById('editRoleModal');
  if (!modal) {
    showToast('Форма редактирования роли в разработке');
    return;
  }
  
  document.getElementById('editRoleTitle').textContent = `Редактировать: ${roleName}`;
  document.getElementById('editRoleId').value = roleId;
  document.getElementById('editRoleName').value = roleName;
  // 🔧 Заполняем поле описания
  const descInput = document.getElementById('editRoleDescription');
  if (descInput) {
    descInput.value = roleDescription || '';
  }
  
  modal.classList.add('show');
}

function showEditRuleModal(ruleId, rule) {
  const modal = document.getElementById('editRuleModal');
  if (!modal) {
    showToast('Форма редактирования правила в разработке');
    return;
  }
  
  document.getElementById('editRuleTitle').textContent = `Правило: ${rule.role_name} → ${rule.resource_name}`;
  document.getElementById('editRuleId').value = ruleId;
  
  const permissions = [
    'read_permission', 'create_permission', 'update_permission', 'delete_permission',
    'read_all_permission', 'update_all_permission', 'delete_all_permission'
  ];
  
  permissions.forEach(perm => {
    const checkbox = document.getElementById(`editRule_${perm}`);
    if (checkbox) {
      checkbox.checked = rule[perm] || false;
    }
  });
  
  modal.classList.add('show');
}

function closeEditUserRolesModal() {
  document.getElementById('editUserRolesModal')?.classList.remove('show');
}

function closeEditRoleModal() {
  document.getElementById('editRoleModal')?.classList.remove('show');
}

function closeEditRuleModal() {
  document.getElementById('editRuleModal')?.classList.remove('show');
}

async function saveUserRoles() {
  const userId = document.getElementById('editUserRolesUserId').value;
  const checkboxes = document.querySelectorAll('#editUserRolesList input[type="checkbox"]');
  
  const currentRoles = adminState.users.find(u => u.id == userId)?.roles || [];
  const newRoles = Array.from(checkboxes)
    .filter(cb => cb.checked)
    .map(cb => ({ id: cb.dataset.roleId, name: cb.dataset.roleName }));
  
  const toAdd = newRoles.filter(r => !currentRoles.includes(r.name));
  const toRemove = currentRoles.filter(r => !newRoles.find(nr => nr.name === r));
  
  try {
    for (const role of toRemove) {
      const roleObj = adminState.roles.find(r => r.name === role);
      if (roleObj) {
        await authFetch(`${ADMIN_API_BASE}/admin/users/${userId}/role/${roleObj.id}`, {
          method: 'DELETE'
        });
      }
    }
    
    for (const role of toAdd) {
      const formData = new FormData();
      formData.append('role_id', role.id);
      
      await authFetch(`${ADMIN_API_BASE}/admin/users/${userId}/role`, {
        method: 'PATCH',
        body: formData
      });
    }
    
    showToast('Роли обновлены');
    closeEditUserRolesModal();
    await loadUsers();
  } catch (error) {
    console.error('Error saving user roles:', error);
    showToast(error.message || 'Не удалось сохранить роли');
  }
}

// # исправлено: сохраняем description роли
async function saveRole() {
  const roleId = document.getElementById('editRoleId').value;
  const newName = document.getElementById('editRoleName').value.trim();
  const newDescription = document.getElementById('editRoleDescription')?.value || '';
  
  if (!newName) {
    showToast('Введите название роли');
    return;
  }
  
  try {
    const formData = new FormData();
    formData.append('name', newName);
    if (newDescription) formData.append('description', newDescription);
    
    await authFetch(`${ADMIN_API_BASE}/admin/roles/${roleId}`, {
      method: 'PATCH',
      body: formData
    });
    
    const role = adminState.roles.find(r => r.id == roleId);
    if (role) {
      role.name = newName;
      role.description = newDescription;
    }
    
    renderRolesTable();
    showToast('Роль обновлена');
    closeEditRoleModal();
  } catch (error) {
    console.error('Error saving role:', error);
    showToast(error.message || 'Не удалось сохранить роль');
  }
}

async function saveRule() {
  const ruleId = document.getElementById('editRuleId').value;
  
  const permissions = [
    'read_permission', 'create_permission', 'update_permission', 'delete_permission',
    'read_all_permission', 'update_all_permission', 'delete_all_permission'
  ];
  
  const updateData = {};
  permissions.forEach(perm => {
    const checkbox = document.getElementById(`editRule_${perm}`);
    if (checkbox) {
      updateData[perm] = checkbox.checked;
    }
  });
  
  try {
    await authFetch(`${ADMIN_API_BASE}/admin/access-rules/${ruleId}`, {
      method: 'PATCH',
      body: JSON.stringify(updateData)
    });
    
    showToast('Правило обновлено');
    closeEditRuleModal();
    await loadRules();
  } catch (error) {
    console.error('Error saving rule:', error);
    showToast(error.message || 'Не удалось сохранить правило');
  }
}

// ==================== ПУБЛИЧНЫЙ API ====================

function showAdminPanel() {
  const token = localStorage.getItem('authToken');
  if (!token) {
    showToast('Требуется авторизация');
    return;
  }
  
  // 🔧 Получаем роли текущего пользователя
  const userRoles = JSON.parse(localStorage.getItem('userRoles') || '[]');
  const isModerator = userRoles.includes('moderator') && !userRoles.includes('admin');
  
  const modal = document.getElementById('adminModal');
  const rolesTab = document.querySelector('.admin-tab-btn[data-tab="roles"]');
  const rulesTab = document.querySelector('.admin-tab-btn[data-tab="rules"]');
  const rolesContent = document.getElementById('adminRolesTab');
  const rulesContent = document.getElementById('adminRulesTab');
  
  // 🔧 Скрываем/показываем вкладки для модераторов
  if (isModerator) {
    rolesTab?.style.setProperty('display', 'none');
    rulesTab?.style.setProperty('display', 'none');
    rolesContent?.style.setProperty('display', 'none');
    rulesContent?.style.setProperty('display', 'none');
  } else {
    // 🔧 Для админа показываем все вкладки
    rolesTab?.style.removeProperty('display');
    rulesTab?.style.removeProperty('display');
    rolesContent?.style.removeProperty('display');
    rulesContent?.style.removeProperty('display');
    
    // 🔧 Загружаем данные для всех вкладок
    loadRoles();
    loadRules();
  }
  
  modal?.classList.add('show');
  loadTabData('users');  // 🔧 Всегда открываем вкладку пользователей
}

// ==================== МОДАЛКИ: ДОБАВЛЕНИЕ ====================

// Показать модальное окно добавления роли
function showAddRoleModal() {
  const modal = document.getElementById('addRoleModal');
  if (!modal) {
    showToast('Форма добавления роли в разработке');
    return;
  }
  
  document.getElementById('addRoleName').value = '';
  document.getElementById('addRoleDescription').value = '';
  modal.classList.add('show');
}

function closeAddRoleModal() {
  document.getElementById('addRoleModal')?.classList.remove('show');
}

async function saveNewRole() {
  const name = document.getElementById('addRoleName').value.trim();
  const description = document.getElementById('addRoleDescription').value.trim();
  
  if (!name) {
    showToast('Введите название роли');
    return;
  }
  
  try {
    const formData = new FormData();
    formData.append('name', name);
    if (description) formData.append('description', description);
    
    const data = await authFetch(`${ADMIN_API_BASE}/admin/roles/`, {
      method: 'POST',
      body: formData
    });
    
    adminState.roles.push({
      id: data.id,
      name: name,
      description: description
    });
    
    renderRolesTable();
    showToast('Роль добавлена');
    closeAddRoleModal();
  } catch (error) {
    console.error('Error adding role:', error);
    showToast(error.message || 'Не удалось добавить роль');
  }
}

// Показать модальное окно добавления правила
async function showAddRuleModal() {
  const modal = document.getElementById('addRuleModal');
  if (!modal) {
    showToast('Форма добавления правила в разработке');
    return;
  }
  
  // Загружаем роли и ресурсы для dropdown
  try {
    const [rolesData, resourcesData] = await Promise.all([
      authFetch(`${ADMIN_API_BASE}/admin/roles/`).catch(() => ({ roles: [] })),
      authFetch(`${ADMIN_API_BASE}/admin/resources/`).catch(() => ({ resources: [] }))
    ]);
    
    const roles = rolesData.roles || [];
    const resources = resourcesData.resources || [];
    
    const roleSelect = document.getElementById('addRuleRoleId');
    const resourceSelect = document.getElementById('addRuleResourceId');
    
    roleSelect.innerHTML = roles.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
    resourceSelect.innerHTML = resources.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
    
    // Сбрасываем чекбоксы на дефолтные значения
    document.getElementById('addRule_read').checked = true;
    document.getElementById('addRule_create').checked = true;
    document.getElementById('addRule_update').checked = true;
    document.getElementById('addRule_delete').checked = true;
    document.getElementById('addRule_read_all').checked = false;
    document.getElementById('addRule_update_all').checked = false;
    document.getElementById('addRule_delete_all').checked = false;
    
    modal.classList.add('show');
  } catch (error) {
    console.error('Error loading dropdowns:', error);
    showToast('Не удалось загрузить список ролей или ресурсов');
  }
}

function closeAddRuleModal() {
  document.getElementById('addRuleModal')?.classList.remove('show');
}

async function saveNewRule() {
  const roleId = document.getElementById('addRuleRoleId').value;
  const resourceId = document.getElementById('addRuleResourceId').value;
  
  if (!roleId || !resourceId) {
    showToast('Выберите роль и ресурс');
    return;
  }
  
  try {
    await authFetch(`${ADMIN_API_BASE}/admin/access-rules`, {
      method: 'POST',
      body: JSON.stringify({
        role_id: parseInt(roleId),
        resource_id: parseInt(resourceId),
        read_permission: document.getElementById('addRule_read').checked,
        create_permission: document.getElementById('addRule_create').checked,
        update_permission: document.getElementById('addRule_update').checked,
        delete_permission: document.getElementById('addRule_delete').checked,
        read_all_permission: document.getElementById('addRule_read_all').checked,
        update_all_permission: document.getElementById('addRule_update_all').checked,
        delete_all_permission: document.getElementById('addRule_delete_all').checked
      })
    });
    
    showToast('Правило создано');
    closeAddRuleModal();
    await loadRules();
  } catch (error) {
    console.error('Error adding rule:', error);
    showToast(error.message || 'Не удалось создать правило');
  }
}

// Показать модальное окно добавления книги
function showAddBookModal() {
  const modal = document.getElementById('addBookModal');
  if (!modal) {
    showToast('Форма добавления книги в разработке');
    return;
  }
  
  document.getElementById('addBookForm').reset();
  modal.classList.add('show');
}

function closeAddBookModal() {
  document.getElementById('addBookModal')?.classList.remove('show');
}

async function saveNewBook() {
  const title = document.getElementById('addBookTitle').value.trim();
  const author = document.getElementById('addBookAuthor').value.trim();
  const description = document.getElementById('addBookDescription').value.trim();
  const year = document.getElementById('addBookYear').value;
  const buyLink = document.getElementById('addBookBuyLink').value.trim();
  const readLink = document.getElementById('addBookReadLink').value.trim();
  const coverFile = document.getElementById('addBookCover').files[0];
  
  // Валидация обязательных полей
  if (!title || !description || !buyLink || !readLink) {
    showToast('Заполните обязательные поля');
    return;
  }
  
  try {
    
    const formData = new FormData();
    formData.append('title', title);
    formData.append('author', author);
    formData.append('description', description);
    if (year) formData.append('year', year);
    formData.append('buy_link', buyLink);
    formData.append('read_link', readLink);
    if (coverFile) formData.append('cover_file', coverFile);
    
    await authFetch(`${ADMIN_API_BASE}/books/`, {
      method: 'POST',
      body: formData
    });
    
    showToast('Книга добавлена');
    closeAddBookModal();
    
    // 🔧 Обновляем список книг
    if (typeof window.booksModule?.loadBooksList === 'function') {
      await window.booksModule.loadBooksList();
    }
    
  } catch (error) {
    console.error('Error adding book:', error);
    showToast(error.message || 'Не удалось добавить книгу');
  }
}


window.adminModule = {
  init: initAdminModule,
  showAdminPanel,
  loadUsers,
  loadRoles,
  loadRules,
  saveUserRoles,
  saveRole,
  saveRule,
  closeEditUserRolesModal,
  closeEditRoleModal,
  closeEditRuleModal,
  closeAddRoleModal,
  closeAddRuleModal,
  saveNewRole,
  saveNewRule,
  showAddBookModal,
  closeAddBookModal,
  saveNewBook
};