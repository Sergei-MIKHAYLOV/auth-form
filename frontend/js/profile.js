// === Работа с профилем пользователя ===

let originalProfileData = null;

function openEditProfile(user) {
  originalProfileData = { ...user };

  const formHTML = `
    <label class="form-label optional">
      <span>Фамилия</span>
      <input name="family_name" value="${user.family_name || ''}">
    </label>
    <label class="form-label">
      <span>Имя</span>
      <input name="name" value="${user.name || ''}" required>
    </label>
    <label class="form-label optional">
      <span>Отчество</span>
      <input name="patronymic" value="${user.patronymic || ''}">
    </label>
    <label class="form-label optional">
      <span>Email</span>
      <input name="email" value="${user.email || ''}">
    </label>
    <label class="form-label optional">
      <span>Пароль</span>
      <input name="password1" placeholder="< новый пароль >">
    </label>
    <label class="form-label optional">
      <span>Повтор пароля</span>
      <input name="password2" placeholder="< повтор пароля >">
    </label>
  `;

  document.getElementById('profileData').innerHTML = formHTML;

  document.getElementById('editProfileBtn').textContent = 'Сохранить';
  document.getElementById('editProfileBtn').onclick = saveProfile;
  document.getElementById('deleteAccountBtn').textContent = 'Отмена';
  document.getElementById('deleteAccountBtn').onclick = cancelEdit;
  document.getElementById('deleteAccountBtn').style.background = '#9E9E9E';
}

async function saveProfile() {
  const inputs = document.querySelectorAll('#profileData input:not([disabled])');
  const formData = new FormData();
  let currentEmail = '';
  const originalEmail = originalProfileData.email;
  let name = '';

  inputs.forEach(input => {
    const value = input.value.trim();
    formData.append(input.name, value);
    if (input.name === 'name') name = value;
    if (input.name === 'email') currentEmail = value;
  });

  // Валидация обязательных полей
  if (!currentEmail) {
    showToast('Поле "email" является обязательным');
    return;
  }
  if (!name) {
    showToast('Поле "Имя" является обязательным');
    return;
  }

  const emailChanged = currentEmail !== originalEmail;

if (emailChanged) {
  // Проверка через /validate-email
  try {
    // 🔧 ИСПОЛЬЗУЕМ другое имя переменной, чтобы не перекрывать основную formData
    const emailFormData = new FormData();
    emailFormData.append('email', currentEmail);
    
    const validateRes = await fetch('/validate-email', {
      method: 'POST',
      body: emailFormData  // ← Используем emailFormData
    });

    if (!validateRes.ok) {
      const err = await validateRes.json();
      showToast(extractErrorMessage(err));
      return;
    }

    showEmailChangeConfirm(originalEmail, () => {
      sendProfileUpdate(formData);  // ← Передаём основную formData
    });
  } catch (e) {
    showToast('Не удалось проверить email');
  }
  return;
}

  sendProfileUpdate(formData);
}

async function sendProfileUpdate(formData) {
  try {
    const token = getToken();
    const res = await fetch('/me', {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });

    if (res.ok) {
      const data = await res.json();
      showToast('Профиль обновлён!');

      // 🔧 ИСПРАВЛЕНО: данные пользователя в data.user
      const updatedUser = data.user || data;
      const emailChanged = updatedUser.email !== originalProfileData.email;

      if (emailChanged) {
        clearToken();
        showToast('Выполнен выход из аккаунта. Пожалуйста, войдите снова.');
        const profilePanel = document.getElementById('profilePanel');
        profilePanel.style.left = '-300px';
        setTimeout(() => profilePanel.style.display = 'none', 300);
        return;
      }

      originalProfileData = updatedUser;
      updateProfilePanel(updatedUser);
      restoreProfileButtons();
    } else {
      const err = await res.json();
      showToast(extractErrorMessage(err));
    }
  } catch (e) {
    showToast('Не удалось подключиться к серверу');
  }
}

function cancelEdit() {
  updateProfilePanel(originalProfileData);
  restoreProfileButtons();
}

function restoreProfileButtons() {
  document.getElementById('editProfileBtn').textContent = 'Редактировать данные';
  document.getElementById('editProfileBtn').onclick = () => openEditProfile(originalProfileData);
  document.getElementById('deleteAccountBtn').textContent = 'Удалить аккаунт';
  document.getElementById('deleteAccountBtn').onclick = confirmDelete;
  document.getElementById('deleteAccountBtn').style.background = '#f44336';
}

function confirmDelete() {
  // 🔧 Заменяем alert на модальное окно
  showConfirmModal(
    'Удаление аккаунта',
    'Вы уверены, что хотите заблокировать свой аккаунт? В этом случае вы больше не сможете отправлять, редактировать или удалять свои сообщения.',
    async () => {
      try {
        const token = getToken();
        const res = await fetch('/me', {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (res.ok) {
          clearToken();
          showToast('Ваш аккаунт заблокирован');
          profilePanel.style.left = '-300px';
          setTimeout(() => profilePanel.style.display = 'none', 300);
        } else {
          const err = await res.json();
          showToast(extractErrorMessage(err));
        }
      } catch (e) {
        showToast('Не удалось подключиться к серверу');
      }
    }
  );
}

function updateProfilePanel(user) {
  // 🔧 ИСПРАВЛЕНО: корректное получение имени
  const fullName = [user.family_name, user.name, user.patronymic]
    .filter(Boolean)
    .join(' ') || 'Пользователь';
  
  const email = user.email || '—';
  
  document.getElementById('profileData').innerHTML = `
    <p><strong>Email:</strong> ${email}</p>
    <p><strong>ФИО:</strong> ${fullName}</p>
  `;
}