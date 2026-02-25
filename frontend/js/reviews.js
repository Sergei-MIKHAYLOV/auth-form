// js/reviews.js
// Модуль для работы с формой добавления отзыва

const USE_MOCK_DATA = false;

function initReviewsModule() {
  const addBtn = document.getElementById('addReviewBtn');
  if (!addBtn) return;
  
  addBtn.addEventListener('click', () => {
    const bookId = document.getElementById('buyBookBtn')?.dataset.bookId;
    if (!bookId) {
      showToast('Сначала выберите книгу');
      return;
    }
    
    const token = localStorage.getItem('authToken');
    if (!token) {
      showToast('Чтобы оставить отзыв, нужно войти в систему');
      return;
    }
    
    showReviewForm(bookId);
  });
}

function showReviewForm(bookId) {
  // 🔧 Заменяем prompt на модалку
  showReviewFormModal('Добавить отзыв', '', (content) => {
    submitReview(bookId, content);
  });
}

async function submitReview(bookId, content) {
  try {
    if (USE_MOCK_DATA) {
      showToast('Спасибо за ваш отзыв! (демо-режим)');
      await window.booksModule?.selectBook(Number(bookId));;
      return;
    }
    
    const token = localStorage.getItem('authToken');
    
    const formData = new FormData();
    formData.append('content', content);
    formData.append('book_id', bookId);
    
    const response = await fetch(`/messages/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    });
    
    if (!response.ok) {
      const error = await response.json();
      const errorMsg = typeof error.detail === 'string' 
        ? error.detail 
        : JSON.stringify(error.detail);
      throw new Error(errorMsg || 'Ошибка при отправке отзыва');
    }
    
    await window.booksModule?.selectBook(bookId);
    showToast('Спасибо за ваш отзыв!');
    
  } catch (error) {
    console.error('Submit review error:', error);
    showToast('Не удалось отправить отзыв: ' + error.message);
  }
}

window.reviewsModule = { init: initReviewsModule };