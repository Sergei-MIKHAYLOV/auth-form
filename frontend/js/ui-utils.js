// === Утилиты UI ===

function showToast(message) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// 🔧 НОВАЯ ФУНКЦИЯ: Модальное окно подтверждения
function showConfirmModal(title, text, onConfirm) {
  const modalEl = document.createElement('div');
  modalEl.className = 'confirm-modal-overlay';
  modalEl.innerHTML = `
    <div class="confirm-modal">
      <h3 class="confirm-modal-title">${title}</h3>
      <p class="confirm-modal-text">${text}</p>
      <div class="confirm-modal-buttons">
        <button class="btn-secondary" id="confirmCancel">Отмена</button>
        <button class="btn-danger" id="confirmOk">Подтвердить</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(modalEl);
  
  // Показываем модалку
  setTimeout(() => modalEl.classList.add('show'), 10);
  
  // Обработчики кнопок
  modalEl.querySelector('#confirmCancel').onclick = () => {
    modalEl.classList.remove('show');
    setTimeout(() => modalEl.remove(), 300);
  };
  
  modalEl.querySelector('#confirmOk').onclick = () => {
    modalEl.classList.remove('show');
    setTimeout(() => modalEl.remove(), 300);
    if (onConfirm) onConfirm();
  };
  
  // Закрытие по клику вне модалки
  modalEl.addEventListener('click', (e) => {
    if (e.target === modalEl) {
      modalEl.classList.remove('show');
      setTimeout(() => modalEl.remove(), 300);
    }
  });
}

function extractErrorMessage(errResponse) {
  if (!errResponse) return 'Неизвестная ошибка';

  if (Array.isArray(errResponse.detail)) {
    const firstErr = errResponse.detail[0];
    if (firstErr.loc?.includes('email') || firstErr.msg?.toLowerCase().includes('email')) {
      return 'Пожалуйста, введите корректный email';
    }
    return firstErr.msg || 'Ошибка валидации данных';
  }

  if (typeof errResponse.detail === 'string') {
    return errResponse.detail;
  }

  return 'Произошла ошибка при обработке запроса';
}

function showEmailChangeConfirm(originalEmail, onConfirm) {
  const modalEl = document.createElement('div');
  modalEl.className = 'confirm-modal-overlay';
  modalEl.innerHTML = `
    <div class="confirm-modal">
      <h3 class="confirm-modal-title">Подтверждение изменения email</h3>
      <p class="confirm-modal-text">
        После смены email потребуется повторный вход на сайт.<br>
        Вы действительно хотите изменить email?
      </p>
      <div class="confirm-modal-buttons">
        <button id="confirmNo" class="btn-secondary">Отмена</button>
        <button id="confirmYes" class="btn-danger">Да</button>
      </div>
    </div>
  `;
  document.body.appendChild(modalEl);

  modalEl.addEventListener('click', (e) => {
    e.stopPropagation();
  });

  modalEl.querySelector('#confirmNo').onclick = () => {
    document.body.removeChild(modalEl);
  };

  modalEl.querySelector('#confirmYes').onclick = () => {
    document.body.removeChild(modalEl);
    if (onConfirm) onConfirm();
  };
}

// === Утилиты UI ===

function showToast(message) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// 🔧 НОВАЯ ФУНКЦИЯ: Модальное окно для добавления/редактирования отзыва
function showReviewFormModal(title, initialValue = '', onSubmit, onCancel) {
  const modalEl = document.createElement('div');
  modalEl.className = 'confirm-modal-overlay';
  modalEl.innerHTML = `
    <div class="confirm-modal">
      <h3 class="confirm-modal-title">${title}</h3>
      <textarea class="review-textarea" rows="5" placeholder="Ваш отзыв...">${escapeHtml(initialValue)}</textarea>
      <div class="confirm-modal-buttons">
        <button class="btn-secondary" id="reviewCancel">Отмена</button>
        <button class="btn-primary" id="reviewSubmit" disabled>Отправить</button>
      </div>
    </div>
  `;
  document.body.appendChild(modalEl);

  // Показать модалку
  setTimeout(() => {
    modalEl.classList.add('show');
    // Фокус на textarea
    const textarea = modalEl.querySelector('.review-textarea');
    textarea.focus();
    // Установить курсор в конец
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
  }, 10);

  const textarea = modalEl.querySelector('.review-textarea');
  const submitBtn = modalEl.querySelector('#reviewSubmit');
  const cancelBtn = modalEl.querySelector('#reviewCancel');

  // Валидация: минимум 10 символов
  const validate = () => {
    const content = textarea.value.trim();
    submitBtn.disabled = content.length < 10;
  };
  textarea.addEventListener('input', validate);
  validate(); // начальная проверка

  // Отправка
  submitBtn.onclick = () => {
    const content = textarea.value.trim();
    if (content.length >= 10) {
      modalEl.classList.remove('show');
      setTimeout(() => {
        modalEl.remove();
        document.removeEventListener('keydown', handleEscape);
        if (onSubmit) onSubmit(content);
      }, 300);
    }
  };

  // Отмена
  cancelBtn.onclick = () => {
    modalEl.classList.remove('show');
    setTimeout(() => {
      modalEl.remove();
      document.removeEventListener('keydown', handleEscape);
      if (onCancel) onCancel();
    }, 300);
  };

  // Закрытие по клику вне модалки
  modalEl.addEventListener('click', (e) => {
    if (e.target === modalEl) {
      modalEl.classList.remove('show');
      setTimeout(() => {
        modalEl.remove();
        document.removeEventListener('keydown', handleEscape);
        if (onCancel) onCancel();
      }, 300);
    }
  });

  // Закрытие по Escape
  const handleEscape = (e) => {
    if (e.key === 'Escape') {
      modalEl.classList.remove('show');
      setTimeout(() => {
        modalEl.remove();
        document.removeEventListener('keydown', handleEscape);
        if (onCancel) onCancel();
      }, 300);
    }
  };
  document.addEventListener('keydown', handleEscape);
}

// 🔧 НОВАЯ ФУНКЦИЯ: Модальное окно подтверждения удаления отзыва
function showReviewDeleteConfirmModal(title, message, onConfirm, onCancel) {
  const modalEl = document.createElement('div');
  modalEl.className = 'confirm-modal-overlay';
  modalEl.innerHTML = `
    <div class="confirm-modal">
      <h3 class="confirm-modal-title">${title}</h3>
      <p class="confirm-modal-text">${message}</p>
      <div class="confirm-modal-buttons">
        <button class="btn-secondary" id="deleteCancel">Отмена</button>
        <button class="btn-danger" id="deleteConfirm">Удалить</button>
      </div>
    </div>
  `;
  document.body.appendChild(modalEl);

  setTimeout(() => modalEl.classList.add('show'), 10);

  const confirmBtn = modalEl.querySelector('#deleteConfirm');
  const cancelBtn = modalEl.querySelector('#deleteCancel');

  confirmBtn.onclick = () => {
    modalEl.classList.remove('show');
    setTimeout(() => {
      modalEl.remove();
      document.removeEventListener('keydown', handleEscape);
      if (onConfirm) onConfirm();
    }, 300);
  };

  cancelBtn.onclick = () => {
    modalEl.classList.remove('show');
    setTimeout(() => {
      modalEl.remove();
      document.removeEventListener('keydown', handleEscape);
      if (onCancel) onCancel();
    }, 300);
  };

  modalEl.addEventListener('click', (e) => {
    if (e.target === modalEl) {
      modalEl.classList.remove('show');
      setTimeout(() => {
        modalEl.remove();
        document.removeEventListener('keydown', handleEscape);
        if (onCancel) onCancel();
      }, 300);
    }
  });

  // Закрытие по Escape
  const handleEscape = (e) => {
    if (e.key === 'Escape') {
      modalEl.classList.remove('show');
      setTimeout(() => {
        modalEl.remove();
        document.removeEventListener('keydown', handleEscape);
        if (onCancel) onCancel();
      }, 300);
    }
  };
  document.addEventListener('keydown', handleEscape);
}

function extractErrorMessage(errResponse) {
  if (!errResponse) return 'Неизвестная ошибка';

  if (Array.isArray(errResponse.detail)) {
    const firstErr = errResponse.detail[0];
    if (firstErr.loc?.includes('email') || firstErr.msg?.toLowerCase().includes('email')) {
      return 'Пожалуйста, введите корректный email';
    }
    return firstErr.msg || 'Ошибка валидации данных';
  }

  if (typeof errResponse.detail === 'string') {
    return errResponse.detail;
  }

  return 'Произошла ошибка при обработке запроса';
}

function showEmailChangeConfirm(originalEmail, onConfirm) {
  const modalEl = document.createElement('div');
  modalEl.className = 'confirm-modal-overlay';
  modalEl.innerHTML = `
    <div class="confirm-modal">
      <h3 class="confirm-modal-title">Подтверждение изменения email</h3>
      <p class="confirm-modal-text">
        После смены email потребуется повторный вход на сайт.<br>
        Вы действительно хотите изменить email?
      </p>
      <div class="confirm-modal-buttons">
        <button id="confirmNo" class="btn-secondary">Отмена</button>
        <button id="confirmYes" class="btn-danger">Да</button>
      </div>
    </div>
  `;
  document.body.appendChild(modalEl);

  modalEl.addEventListener('click', (e) => {
    e.stopPropagation();
  });

  modalEl.querySelector('#confirmNo').onclick = () => {
    document.body.removeChild(modalEl);
  };

  modalEl.querySelector('#confirmYes').onclick = () => {
    document.body.removeChild(modalEl);
    if (onConfirm) onConfirm();
  };
}