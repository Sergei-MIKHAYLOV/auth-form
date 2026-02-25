// js/auth.js
// Управление аутентификацией

function getToken() {
  return localStorage.getItem('authToken');
}

async function saveToken(token) {
  localStorage.setItem('authToken', token);
  originalProfileData = null;
  
  // 🔧 Загружаем профиль и сохраняем роли
  const user = await fetchUserProfile();
  if (user && user.roles) {
    localStorage.setItem('userRoles', JSON.stringify(user.roles));
  }
  
  updateUI();
}

function clearToken() {
  if (!localStorage.getItem('authToken')) return;
  
  localStorage.removeItem('authToken');
  localStorage.removeItem('userRoles');  // 🔧 Очищаем роли
  originalProfileData = null;
  
  if (typeof window.setCurrentUserId === 'function') {
    window.setCurrentUserId(null);
  }
  if (typeof window.setCurrentUserRoles === 'function') {
    window.setCurrentUserRoles([]);
  }
  
  updateUI();
  
  if (typeof window.refreshReviewButtons === 'function' && 
      typeof currentBookId !== 'undefined' && currentBookId) {
    window.refreshReviewButtons();
  }
}

async function fetchUserProfile() {
  const token = getToken();
  if (!token) return null;
  try {
    const res = await fetch('/me', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      const data = await res.json();
      return data.user || null;  // 🔧 Явно возвращаем user
    }
    throw new Error('Invalid token');
  } catch {
    clearToken();
    return null;
  }
}

// 🔧 Упрощённая проверка на админа
async function isAdmin() {
  const user = await fetchUserProfile();
  if (!user) return false;
  return Array.isArray(user.roles) && user.roles.includes('admin');
}

// Экспорт через window
window.authModule = {
  getToken,
  saveToken,
  clearToken,
  fetchUserProfile,
  isAdmin
};