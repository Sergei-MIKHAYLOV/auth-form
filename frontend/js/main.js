// js/main.js
// Точка входа для инициализации модулей

// Инициализация приложения
const modal = document.getElementById('authModal');
const profilePanel = document.getElementById('profilePanel');
const adminPanelBtn = document.getElementById('adminPanelBtn');

// ==================== UI: ОБНОВЛЕНИЕ ИНТЕРФЕЙСА ====================

// js/main.js, функция updateUI

async function updateUI() {
  const token = getToken();
  const authBtn = document.getElementById('authBtn');
  const userPanel = document.getElementById('userPanel');
  const adminPanelBtn = document.getElementById('adminPanelBtn');
  const addBookBtn = document.getElementById('addBookBtn');
  
  if (token) {
    const user = await fetchUserProfile();
    if (user) {

      if (typeof window.setCurrentUserId === 'function') {
        window.setCurrentUserId(user.id);
      }
      if (typeof window.setCurrentUserRoles === 'function') {
        window.setCurrentUserRoles(user.roles || []);
      }


      const fullName = [user.family_name, user.name, user.patronymic]
        .filter(Boolean)
        .join(' ')
        .trim() || user.name || 'Пользователь';
      
      document.getElementById('userName').textContent = fullName;
      userPanel.style.display = 'flex';
      
      authBtn.textContent = 'Выйти';
      authBtn.onclick = () => {
        clearToken();
        showToast('Вы вышли из аккаунта');
        updateUI();
      };

      if (adminPanelBtn) {
        const storedRoles = JSON.parse(localStorage.getItem('userRoles') || '[]');
        const userIsAdminOrMod = storedRoles.some(r => ['admin', 'moderator'].includes(r));
        adminPanelBtn.style.display = userIsAdminOrMod ? 'block' : 'none';
        
        console.log('🎭 Stored roles:', storedRoles);
        console.log('👑 Admin button display:', adminPanelBtn.style.display);
      }

      if (addBookBtn) {
        const canCreateBook = user.permissions?.books?.create === true;
        addBookBtn.style.display = canCreateBook ? 'block' : 'none';
      }

      
      if (typeof window.refreshReviewButtons === 'function') {
        setTimeout(() => {
          window.refreshReviewButtons();
          console.log('🔄 Reviews refreshed after updateUI');
        }, 50);
      }
      
      return;
    }
  }
  
  // Гость
  userPanel.style.display = 'none';
  if (adminPanelBtn) {
    adminPanelBtn.style.display = 'none';
  }

  if (addBookBtn) {
    addBookBtn.style.display = 'none';
}
  
  authBtn.textContent = 'Вход / Регистрация';
  authBtn.onclick = () => {
    modal.style.display = 'flex';
    setTimeout(() => {
      document.querySelector('.tab-btn[data-tab="login"]').click();
    }, 10);
  };
}


document.getElementById('addBookBtn')?.addEventListener('click', () => {
  if (window.adminModule?.showAddBookModal) {
    window.adminModule.showAddBookModal();
  }
});


// ==================== ОБРАБОТЧИКИ ФОРМ АВТОРИЗАЦИИ ====================

document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  
  try {
    const res = await fetch('/login', { method: 'POST', body: fd });
    if (res.ok) {
      const data = await res.json();
      modal.style.display = 'none';
      e.target.reset();
      saveToken(data.access_token); 
      showToast('Успешный вход!');
      
      // 🔧 НОВОЕ: Обновить кнопки редактирования отзывов
      // if (typeof window.refreshReviewButtons === 'function') {
      //   window.refreshReviewButtons();
      // }
    } else {
      const err = await res.json();
      showToast(extractErrorMessage(err));
    }
  } catch {
    showToast('Не удалось подключиться к серверу');
  }
});

document.getElementById('registerForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  
  if (fd.get('password1') !== fd.get('password2')) {
    showToast('Пароли не совпадают');
    return;
  }
  
  try {
    const res = await fetch('/register', { method: 'POST', body: fd });
    if (res.ok) {
      const data = await res.json();
      modal.style.display = 'none';
      e.target.reset();
      saveToken(data.access_token);
      showToast('Регистрация успешна.');
    } else {
      const err = await res.json();
      showToast(extractErrorMessage(err));
    }
  } catch {
    showToast('Не удалось подключиться к серверу');
  }
});

// ==================== ПЕРЕКЛЮЧЕНИЕ ВКЛАДОК МОДАЛКИ ====================

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`${btn.dataset.tab}Form`).classList.add('active');
  });
});

// ==================== ЗАКРЫТИЕ МОДАЛОК ====================

// Клик по оверлею авторизации
modal.addEventListener('click', (e) => {
  if (e.target === modal) modal.style.display = 'none';
});

// Клик по панели пользователя
document.getElementById('userPanel').addEventListener('click', async () => {
  const user = await fetchUserProfile();
  if (!user) return;

  updateProfilePanel(user);
  originalProfileData = user;
  restoreProfileButtons(); 

  profilePanel.style.display = 'block';
  setTimeout(() => profilePanel.style.left = '0px', 10);
});

// Клик вне панели профиля
document.addEventListener('click', (e) => {
  const isOpen = window.getComputedStyle(profilePanel).left === '0px';
  const clickedInside = e.target.closest('#profilePanel') || e.target.closest('#userPanel');
  
  if (isOpen && !clickedInside) {
    restoreProfileButtons();
    profilePanel.style.left = '-300px';
    setTimeout(() => profilePanel.style.display = 'none', 300);
  }
});

// ==================== ИНИЦИАЛИЗАЦИЯ ПРИ ЗАГРУЗКЕ ====================

document.addEventListener('DOMContentLoaded', async () => {
  console.log('🚀 Приложение загружается...');
  
  // 1. Обновляем UI (авторизация) — здесь УЖЕ установлены currentUserId и роли
  await updateUI();
  
  
  // 🔧 Вместо этого — просто проверить, видна ли кнопка (она уже настроена в updateUI)
  if (adminPanelBtn) {
    console.log('👑 Admin button state:', adminPanelBtn.style.display);
  }
  
  // 2. Инициализируем модуль книг (теперь currentUserId уже установлен!)
  if (typeof window.booksModule?.init === 'function') {
    await window.booksModule.init();
    console.log('✅ Модуль книг загружен');
  }
  
  // 3. Инициализируем модуль отзывов
  if (typeof window.reviewsModule?.init === 'function') {
    window.reviewsModule.init();
    console.log('✅ Модуль отзывов загружен');
  }
  
  // 4. Инициализируем админ-панель
  if (typeof window.adminModule?.init === 'function') {
    window.adminModule.init();
    console.log('✅ Админ-панель инициализирована');
  }
  
  // 5. Обработчик кнопки админ-панели
  adminPanelBtn?.addEventListener('click', () => {
    if (window.adminModule?.showAdminPanel) {
      window.adminModule.showAdminPanel();
    }
  });
  
  console.log('🎉 Приложение готово к работе');
});