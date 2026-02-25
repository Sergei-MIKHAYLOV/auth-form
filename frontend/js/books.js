// js/books.js
// Модуль для работы со списком книг, поиска и отображения деталей

// ==================== ГЛОБАЛЬНАЯ КОНФИГУРАЦИЯ ====================
if (window.APP_CONFIG === undefined) {
  window.APP_CONFIG = {
    API_BASE: '',
    USE_MOCK_DATA: false,
    CSV_PATHS: {
      books: '/mock-data/books.csv',
      messages: '/mock-data/messages.csv'
    }
  };
}

const CONFIG = window.APP_CONFIG;
const PLACEHOLDER_COVER = 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22300%22%3E%3Crect fill=%22%23e5e5e5%22 width=%22100%25%22 height=%22100%25%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22%23999%22 font-size=%2214%22%3EНет обложки%3C/text%3E%3C/svg%3E';

// Кэш для книг
let booksCache = [];
let filteredBooks = [];
let currentBookId = null;

// 🔧 ГЛОБАЛЬНЫЙ ID текущего пользователя (устанавливается из main.js)
let currentUserId = null;

// 🔧 ГЛОБАЛЬНЫЕ роли текущего пользователя (устанавливаются из main.js)
let currentUserRoles = [];

// ==================== ИНИЦИАЛИЗАЦИЯ ====================

async function initBooksModule() {
  await loadBooksList();
  setupBookClickHandlers();
  setupActionButtons();
  setupSearch();
  
  if (filteredBooks.length > 0) {
    selectBook(filteredBooks[0].id);
  }
}

// ==================== ЗАГРУЗКА ДАННЫХ ====================

async function loadBooksList() {
  try {
    if (CONFIG.USE_MOCK_DATA) {
      booksCache = await loadBooksFromCSV();
    } else {
      const response = await fetch(`${CONFIG.API_BASE}/books/`);
      if (!response.ok) throw new Error('Failed to fetch books');
      const data = await response.json();
      booksCache = Array.isArray(data) ? data : (data.books || data.data || []);
    }
    filteredBooks = [...booksCache];
    renderBooksList(filteredBooks);
  } catch (error) {
    console.error('Error loading books:', error);
    booksCache = [];
    filteredBooks = [...booksCache];
    renderBooksList(filteredBooks);
    showToast('Не удалось загрузить список книг');
  }
}

async function loadBooksFromCSV() {
  const url = `${CONFIG.CSV_PATHS.books}?t=${Date.now()}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error('Failed to load books.csv');
  
  const csvText = await response.text();
  return parseBooksCSV(csvText);
}

function parseBooksCSV(csvText) {
  const lines = csvText.trim().split('\n');
  if (lines.length < 2) return [];
  
  const headers = parseCSVLineRobust(lines[0]);
  
  return lines.slice(1).map(line => {
    const values = parseCSVLineRobust(line);
    const book = {};
    
    headers.forEach((header, i) => {
      let value = values[i] || '';
      
      if (header === 'id' || header === 'year') {
        value = value ? parseInt(value, 10) : null;
      } else if (header === 'is_active') {
        const v = String(value).toLowerCase().trim();
        value = v === 'true' || v === '1' || v === 'yes';
      }
      
      book[header] = value;
    });
    
    return book;
  }).filter(book => book.id);
}

// ==================== РЕНДЕРИНГ ====================

function renderBooksList(books) {
  const container = document.getElementById('booksListContainer');
  if (!container) return;
  
  if (books.length === 0) {
    container.innerHTML = '<p class="no-books">Книги не найдены</p>';
    return;
  }
  
  const html = books
    .filter(book => book.is_active !== false)
    .map(book => createBookItemHTML(book))
    .join('');
  
  container.innerHTML = html;
  
  if (currentBookId) {
    highlightCurrentBook(currentBookId);
  }
}

function createBookItemHTML(book) {
    const bookNumber = String(book.id).padStart(2, '0');
    const isActive = book.id === currentBookId ? 'active' : '';
    const coverSrc = book.cover_url || `./img/book_${bookNumber}.jpg`;
  
  return `
    <div class="book-item ${isActive}" data-book-id="${book.id}">
    <img src="${coverSrc}"
    alt="${escapeHtml(book.title)}"
    onerror="this.src='${PLACEHOLDER_COVER}'">
      <div class="book-item-info">
        <p class="book-item-title">${escapeHtml(book.title)}</p>
        <p class="book-item-author">${escapeHtml(book.author || 'Неизвестный автор')}</p>
      </div>
    </div>
  `;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// 🔧 Публичный метод для установки ID текущего пользователя (вызывается из main.js)
window.setCurrentUserId = function(userId) {
  console.log('🔐 Setting currentUserId:', userId);
  currentUserId = userId;
};

// 🔧 Публичный метод для установки ролей текущего пользователя
window.setCurrentUserRoles = function(roles) {
  console.log('🎭 Setting currentUserRoles:', roles);
  currentUserRoles = Array.isArray(roles) ? roles : [];
};

// 🔧 Публичный метод для получения текущего ID (для отладки)
window.getCurrentUserId = function() {
  return currentUserId;
};

// 🔧 Проверка, может ли пользователь редактировать/удалять отзыв
function canEditReview(reviewOwnerId) {
  // Admin/moderator могут редактировать ЛЮБЫЕ отзывы
  if (currentUserRoles.some(r => r === 'admin' || r === 'moderator')) {
    return true;
  }
  // Обычный пользователь — только свои
  return currentUserId && (Number(reviewOwnerId) === Number(currentUserId));
}

function highlightCurrentBook(bookId) {
  document.querySelectorAll('.book-item').forEach(el => {
    el.classList.remove('active');
    if (parseInt(el.dataset.bookId) === bookId) {
      el.classList.add('active');
    }
  });
}

// ==================== ПОИСК С ПОДСКАЗКАМИ ====================

function renderSuggestions(books, query) {
    const container = document.getElementById('searchSuggestions');
    if (!container) return;
    if (books.length === 0) {
        container.innerHTML = '<div class="no-results">Такой книги пока нет на сайте</div>';
        container.classList.add('show');
        return;
    }
    const highlighted = query.toLowerCase();
    const html = books.slice(0, 10).map(book => {
        const bookNumber = String(book.id).padStart(2, '0');
        const coverSrc = book.cover_url || `./img/book_${bookNumber}.jpg`;
        const title = book.title.replace(
            new RegExp(`(${highlighted})`, 'gi'),
            '<strong>$1</strong>'
        );
        return `
        <div class="suggestion-item" data-book-id="${book.id}">
        <img src="${coverSrc}"
        alt="${book.title}"
        onerror="this.src='${PLACEHOLDER_COVER}'">
        <div class="suggestion-info">
        <div class="suggestion-title">${title}</div>
        <div class="suggestion-author">${book.author || 'Неизвестный автор'}</div>
        </div>
        </div>
        `;
    }).join('');
    container.innerHTML = html;
    container.classList.add('show');
}

function hideSuggestions() {
  const container = document.getElementById('searchSuggestions');
  if (container) {
    container.classList.remove('show');
  }
}

// 🔑 ЕДИНСТВЕННАЯ версия performSearch
function performSearch(query) {
  if (!query) {
    filteredBooks = [...booksCache];
    hideSuggestions();
  } else {
    const lowerQuery = query.toLowerCase();
    filteredBooks = booksCache.filter(book => {
      const titleMatch = book.title?.toLowerCase().includes(lowerQuery);
      const authorMatch = book.author?.toLowerCase().includes(lowerQuery);
      const descMatch = book.description?.toLowerCase().includes(lowerQuery);
      return (titleMatch || authorMatch || descMatch) && book.is_active !== false;
    });
    
    renderSuggestions(filteredBooks, query);
  }
  
  // 🔧 Левая панель ВСЕГДА показывает все книги, независимо от поиска
  renderBooksList(booksCache);
  
  if (filteredBooks.length > 0 && !currentBookId) {
    selectBook(filteredBooks[0].id);
  }
}

function setupSuggestionsHandlers() {
  const container = document.getElementById('searchSuggestions');
  const input = document.getElementById('searchInput');
  const clearBtn = document.getElementById('clearSearchBtn');
  if (!container || !input) return;
  
  container.addEventListener('click', (e) => {
    const item = e.target.closest('.suggestion-item');
    if (!item) return;
    
    const bookId = parseInt(item.dataset.bookId);
    input.value = '';
    if (clearBtn) {
      clearBtn.style.display = 'none';
    }
    hideSuggestions();
    selectBook(bookId);
  });
  
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-container')) {
      hideSuggestions();
    }
  });
  
  input.addEventListener('keydown', (e) => {
    const items = container.querySelectorAll('.suggestion-item');
    if (items.length === 0) return;
    
    const active = container.querySelector('.suggestion-item.active');
    let index = active ? Array.from(items).indexOf(active) : -1;
    
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (active) active.classList.remove('active');
      index = (index + 1) % items.length;
      items[index].classList.add('active');
      items[index].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (active) active.classList.remove('active');
      index = index <= 0 ? items.length - 1 : index - 1;
      items[index].classList.add('active');
      items[index].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter' && active) {
      e.preventDefault();
      const bookId = parseInt(active.dataset.bookId);
      input.value = '';
      if (clearBtn) {
        clearBtn.style.display = 'none';
      }
      hideSuggestions();
      selectBook(bookId);
    } else if (e.key === 'Escape') {
      hideSuggestions();
    }
  });
}

function setupSearch() {
  const searchInput = document.getElementById('searchInput');
  const clearBtn = document.getElementById('clearSearchBtn');
  
  if (!searchInput) return;
  
  // Поиск при вводе (live search)
  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.trim();
    performSearch(query);
    
    if (clearBtn) {
      clearBtn.style.display = query ? 'block' : 'none';
    }
  });
  
  // 🔧 Поиск по Enter — ИСПРАВЛЕНО
  searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      const query = searchInput.value.trim();
      if (query && filteredBooks.length > 0) {
        // 🔧 Выбираем первую найденную книгу
        selectBook(filteredBooks[0].id);
        // 🔧 Очищаем поле и скрываем крестик
        searchInput.value = '';
        if (clearBtn) {
          clearBtn.style.display = 'none';
        }
      } else if (query && filteredBooks.length === 0) {
        showToast('Такой книги пока нет на сайте');
      }
      hideSuggestions();
    }
  });
  
  // Очистка поиска
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      searchInput.value = '';
      clearBtn.style.display = 'none';
      filteredBooks = [...booksCache];
      renderBooksList(filteredBooks);
      hideSuggestions();
      searchInput.focus();
    });
  }
  
  setupSuggestionsHandlers();
}

// ==================== ВЫБОР КНИГИ ====================

async function selectBook(bookId) {
  const numericBookId = Number(bookId);
  const book = booksCache.find(b => b.id === numericBookId);
  if (!book) {
    console.error('Book not found:', bookId);
    return;
  }
  
  currentBookId = bookId;
  highlightCurrentBook(bookId);
  
  updateMainBookView(book);
  updateBookInfo(book);
  
  // 🔧 СБРОС ПРОКРУТКИ при выборе новой книги
  resetBookInfoScroll();
  
  await loadAndRenderReviews(bookId);
}

// 🔧 Функция сброса прокрутки правой колонки
function resetBookInfoScroll() {
  const outerScroll = document.querySelector('.book-info-outer-scroll');
  const reviewsScroll = document.querySelector('.reviews-scroll-container');
  
  if (outerScroll) {
    outerScroll.scrollTop = 0;
  }
  if (reviewsScroll) {
    reviewsScroll.scrollTop = 0;
  }
}

function updateMainBookView(book) {
    const coverImg = document.getElementById('mainBookCover');
    if (coverImg) {
        const coverSrc = book.cover_url || `./img/book_${String(book.id).padStart(2, '0')}.jpg`;
        coverImg.src = coverSrc;
        coverImg.alt = book.title;
        coverImg.onerror = function() { this.src = PLACEHOLDER_COVER; };
    }
  
  const readBtn = document.getElementById('readFragmentBtn');
  const buyBtn = document.getElementById('buyBookBtn');
  if (readBtn) readBtn.dataset.bookId = book.id;
  if (buyBtn) buyBtn.dataset.bookId = book.id;
}

function updateBookInfo(book) {
  const titleEl = document.getElementById('bookTitle');
  const authorEl = document.getElementById('bookAuthor');
  const descEl = document.getElementById('bookDescription');
  
  if (titleEl) titleEl.textContent = book.title;
  if (authorEl) authorEl.textContent = `автор ${book.author || 'Неизвестный автор'}`;
  if (descEl) descEl.textContent = book.description || 'Описание отсутствует';
}

// ==================== ОТЗЫВЫ ====================

async function loadAndRenderReviews(bookId) {
  try {
    let reviews = [];
    
    if (CONFIG.USE_MOCK_DATA) {
      reviews = await loadMessagesFromCSV(bookId);
    } else {
      const response = await fetch(`${CONFIG.API_BASE}/messages/?book_id=${bookId}`);
      if (response.ok) {
        const data = await response.json();
        reviews = Array.isArray(data) ? data : data.messages || [];
      }
    }
    
    renderReviews(reviews);
  } catch (error) {
    console.error('Error loading reviews:', error);
    renderReviews([]);
  }
}

async function loadMessagesFromCSV(bookId) {
  const url = `${CONFIG.CSV_PATHS.messages}?t=${Date.now()}`;
  
  console.log('🔍 Загрузка отзывов:', url);
  
  const response = await fetch(url);
  if (!response.ok) {
    console.error('❌ messages.csv не найден (404)');
    throw new Error('Failed to load messages.csv');
  }
  
  const csvText = await response.text();
  console.log('📄 Размер CSV:', csvText.length, 'символов');
  
  const allMessages = parseMessagesCSV(csvText);
  
  console.log(`📊 Всего сообщений в CSV: ${allMessages.length}`);
  console.log(`📊 Для книги #${bookId}:`, 
    allMessages.filter(m => m.book_id == bookId).length, 'шт.');
  console.log(`📊 Активных для книги #${bookId}:`, 
    allMessages.filter(m => m.book_id == bookId && m.is_active !== false).length, 'шт.');
  
  const result = allMessages
    .filter(msg => msg.book_id == bookId && msg.is_active !== false)
    .sort((a, b) => {
      // 🔧 Используем updated_at, если есть, иначе created_at
      const dateA = new Date(a.updated_at || a.created_at || 0);
      const dateB = new Date(b.updated_at || b.created_at || 0);
      return dateB - dateA;  // По убыванию (свежие сверху)
    });
      
  console.log(`✅ Отобразится отзывов: ${result.length}`);
  return result;
}

function parseMessagesCSV(csvText) {
  const lines = csvText.trim().split('\n');
  if (lines.length < 2) return [];
  
  const headers = parseCSVLineRobust(lines[0]);
  const results = [];
  
  for (let i = 1; i < lines.length; i++) {
    try {
      const line = lines[i].trim();
      if (!line) continue;
      
      const values = parseCSVLineRobust(line);
      if (values.length < headers.length) {
        console.warn(`⚠️ Строка ${i + 1}: недостаточно полей (${values.length}/${headers.length})`);
        continue;
      }
      
      const msg = {};
      headers.forEach((header, idx) => {
        let value = values[idx] || '';
        
        if (header === 'id' || header === 'owner_id' || header === 'book_id') {
          value = value ? parseInt(value, 10) : null;
        } else if (header === 'is_active') {
          const v = String(value).toLowerCase().trim();
          value = v === 'true' || v === '1' || v === 'yes';
        }
        
        msg[header] = value;
      });
      
      if (msg.id) {
        results.push(msg);
      } else {
        console.warn(`⚠️ Строка ${i + 1}: не удалось распарсить id`, values[0]);
      }
    } catch (err) {
      console.error(`❌ Ошибка парсинга строки ${i + 1}:`, err.message, lines[i].slice(0, 100));
    }
  }
  
  console.log(`✅ Распарсено сообщений: ${results.length} из ${lines.length - 1}`);
  return results;
}

function parseCSVLineRobust(line) {
  const result = [];
  let current = '';
  let inQuotes = false;
  
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    const nextChar = line[i + 1];
    
    if (char === '"') {
      if (nextChar === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      result.push(current);
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current);
  
  return result.map(v => v.trim());
}


function renderBookCard(book) {
  const bookId = String(book.id).padStart(2, '0');
  const coverUrl = book.cover_url || `./img/book_${bookId}.jpg`;
  
  return `
    <div class="book-card">
      <img src="${coverUrl}" alt="${escapeHtml(book.title)}">
      <div class="book-actions">
        <a href="${book.buy_link}" target="_blank" rel="noopener noreferrer" class="action-btn primary">
          Купить и скачать
        </a>
        <a href="${book.read_link}" target="_blank" rel="noopener noreferrer" class="action-btn">
          Читать фрагмент
        </a>
      </div>
      <h3 class="book-title">${escapeHtml(book.title)}</h3>
      <p class="book-author">${escapeHtml(book.author)}</p>
      <p class="book-description">${escapeHtml(book.description)}</p>
    </div>
  `;
}



function renderReviews(reviews) {
  const list = document.getElementById('reviewsList');
  const count = document.getElementById('reviewsCount');
  if (!list) return;
  
  // 🔧 Фильтруем только активные отзывы
  const activeReviews = reviews.filter(r => r.is_active !== false);
  
  if (count) count.textContent = `(${activeReviews.length})`;
  
  if (activeReviews.length === 0) {
    list.innerHTML = '<p class="no-reviews">Пока нет отзывов. Будьте первым!</p>';
    return;
  }
  
  const html = activeReviews.map(review => {
  const createdDate = review.created_at ? new Date(review.created_at).toLocaleDateString('ru-RU') : '';
  const updatedDate = review.updated_at ? new Date(review.updated_at).toLocaleDateString('ru-RU') : '';
  
  // 🔧 Показываем дату последнего изменения
  const displayDate = review.updated_at ? updatedDate : createdDate;
  const dateLabel = review.updated_at ? '(ред.)' : '';
  
  const owner = review.msg_owner || review.owner || {};
  const authorName = owner.name 
    || owner.username 
    || review.author_name 
    || review.user_name 
    || 'Аноним';
  
  const canEdit = canEditReview(review.owner_id);
  
  const actionsHtml = canEdit ? `
    <div class="review-actions">
      <button class="review-action-btn edit" 
              data-review-id="${review.id}" 
              data-review-content="${escapeHtml(review.content)}"
              title="Редактировать">
        <!-- Иконка карандаша -->
        <svg viewBox="0 0 24 24">
          <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
        </svg>
      </button>
      <button class="review-action-btn delete" 
              data-review-id="${review.id}" 
              title="Удалить">
        <!-- Иконка корзины -->
        <svg viewBox="0 0 24 24">
          <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
        </svg>
      </button>
    </div>
  ` : '';
  
  return `
    <div class="review-item" data-review-id="${review.id}">
      <div class="review-header">
        <span class="review-author">${escapeHtml(authorName)}</span>
        <span class="review-date">
        ${dateLabel ? `<small style="color: var(--color-text-light); margin-right: 4px;">${dateLabel}</small>` : ''}
        ${displayDate}
      </span>
      </div>
      <div class="review-content">${escapeHtml(review.content)}</div>
      ${actionsHtml}
    </div>
  `;
  }).join('');
  
  list.innerHTML = html;
  setupReviewActionHandlers();
}

// ==================== ОБРАБОТЧИКИ СОБЫТИЙ ====================

function setupBookClickHandlers() {
  const container = document.getElementById('booksListContainer');
  if (!container) return;
  
  container.addEventListener('click', (e) => {
    const bookItem = e.target.closest('.book-item');
    if (!bookItem) return;
    
    const bookId = parseInt(bookItem.dataset.bookId);
    selectBook(bookId);
  });
}

function setupActionButtons() {
  const readBtn = document.getElementById('readFragmentBtn');
  const buyBtn = document.getElementById('buyBookBtn');
  
  readBtn?.addEventListener('click', (e) => {
    const bookId = e.target.dataset.bookId;
    handleReadFragment(bookId);
  });
  
  buyBtn?.addEventListener('click', (e) => {
    const bookId = e.target.dataset.bookId;
    handleBuyBook(bookId);
  });
}

function handleReadFragment(bookId) {
  const book = booksCache.find(b => b.id == Number(bookId));
  if (!book || !book.read_link) {
    showToast('Ссылка на фрагмент недоступна');
    return;
  }
  window.open(book.read_link, '_blank', 'noopener,noreferrer');
}
function handleBuyBook(bookId) {
  const book = booksCache.find(b => b.id == Number(bookId));
  if (!book || !book.buy_link) {
    showToast('Ссылка на покупку недоступна');
    return;
  }
  window.open(book.buy_link, '_blank', 'noopener,noreferrer');
}

// 🔧 Обработчики кнопок редактирования/удаления отзывов
function setupReviewActionHandlers() {
  // Редактирование
  document.querySelectorAll('.review-action-btn.edit').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation(); // Чтобы не срабатывал клик по отзыву
      const reviewId = btn.dataset.reviewId;
      const content = btn.dataset.reviewContent;
      editReview(reviewId, content);
    });
  });
  
  // Удаление
  document.querySelectorAll('.review-action-btn.delete').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const reviewId = btn.dataset.reviewId;
      deleteReview(reviewId);
    });
  });
}

// 🔧 Функция редактирования отзыва (реальный API + модалка)
async function editReview(reviewId, currentContent) {
  showReviewFormModal('Редактировать отзыв', currentContent, async (newContent) => {
    try {
      const token = localStorage.getItem('authToken');
      
      const formData = new FormData();
      formData.append('content', newContent);
      
      const response = await fetch(`/messages/${reviewId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      
      if (response.ok) {
        showToast('Отзыв обновлён');
        if (currentBookId) {
          await loadAndRenderReviews(currentBookId);
        }
      } else {
        const error = await response.json();
        showToast(error.detail || 'Не удалось обновить отзыв');
      }
    } catch (error) {
      console.error('Edit review error:', error);
      showToast('Ошибка соединения с сервером');
    }
  });
}

// 🔧 Функция удаления отзыва (реальный API + модалка)
async function deleteReview(reviewId) {
  showReviewDeleteConfirmModal(
    'Удалить отзыв',
    'Вы уверены, что хотите удалить этот отзыв? Это действие нельзя отменить.',
    async () => {
      try {
        const token = localStorage.getItem('authToken');
        
        const response = await fetch(`/messages/${reviewId}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (response.ok) {
          showToast('Отзыв удалён');
          if (currentBookId) {
            await loadAndRenderReviews(currentBookId);
          }
        } else {
          const error = await response.json();
          showToast(error.detail || 'Не удалось удалить отзыв');
        }
      } catch (error) {
        console.error('Delete review error:', error);
        showToast('Ошибка соединения с сервером');
      }
    }
  );
}

// 🔧 Публичный метод для обновления кнопок редактирования (после логина)
window.refreshReviewButtons = function() {
  console.log('🔄 Refreshing review buttons, currentUserId:', currentUserId, 'roles:', currentUserRoles);
  
  // Перерисовываем текущие отзывы с новым currentUserId
  const bookId = currentBookId;
  if (bookId) {
    loadAndRenderReviews(bookId);
  }
};

// ==================== MOCK ДАННЫЕ (FALLBACK) ====================

function getMockBooks() {
  return [
    { id: 1, author: 'Александр и Евгения Гедеон', title: 'У оружия нет имени', description: 'Репликанты были созданы для войны...', year: 2019, is_active: true },
    { id: 2, author: 'Дем Михайлов', title: 'Низший', description: 'Постапокалиптический мир...', year: 2015, is_active: true },
    { id: 3, author: 'Антон Карелин', title: 'Одиссей Фокс', description: 'Космическая фантастика...', year: 2017, is_active: true },
    { id: 4, author: 'Андрей Красников', title: 'Вектор', description: 'Военная фантастика...', year: 2018, is_active: true },
    { id: 5, author: 'Дж. Р. Р. Толкин', title: 'Властелин колец', description: 'Эпическое фэнтези...', year: 1954, is_active: true }
  ];
}

// ==================== ЭКСПОРТ В GLOBAL SCOPE ====================

window.booksModule = {
  init: initBooksModule,
  selectBook,
  loadBooksList,
  renderBooksList,
  createBookItemHTML,
  performSearch,
  getFilteredBooks: () => filteredBooks,
  getCurrentBookId: () => currentBookId
};