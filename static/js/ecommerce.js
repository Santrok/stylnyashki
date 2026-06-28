/**
 * Yandex Metrica eCommerce Tracking
 * Отслеживание добавления/удаления товаров из корзины и покупок
 */

/**
 * Основная функция для отправки событий в Метрику
 * @param {string} actionType - Тип действия (add, remove, purchase, detail)
 * @param {array} products - Массив товаров
 * @param {object} actionField - Данные действия (для покупок)
 */
function trackEcommerce(actionType, products, actionField = {}) {
    if (typeof window.dataLayer === 'undefined') {
        console.warn('dataLayer not initialized');
        return;
    }

    const ecommerceData = {
        ecommerce: {
            currencyCode: 'BYN',
            [actionType]: {
                actionField: actionField,
                products: products
            }
        }
    };

    window.dataLayer.push(ecommerceData);

}

/**
 * Добавление товара в корзину
 * @param {object} product - Объект товара
 * @param {number} product.id - ID товара
 * @param {string} product.name - Название товара
 * @param {number} product.price - Цена товара
 * @param {number} product.quantity - Количество
 * @param {string} product.variant - Размер/вариант (опционально)
 * @param {string} product.brand - Бренд (опционально)
 * @param {string} product.category - Категория (опционально)
 */
function trackAddToCart(product) {
    const productData = {
        id: String(product.id),
        name: product.name,
        price: parseFloat(product.price),
        quantity: product.quantity || 1
    };

    if (product.variant) productData.variant = product.variant;
    if (product.brand) productData.brand = product.brand;
    if (product.category) productData.category = product.category;

    trackEcommerce('add', [productData]);
}

/**
 * Удаление товара из корзины
 * @param {object} product - Объект товара
 */
function trackRemoveFromCart(product) {
    const productData = {
        id: String(product.id),
        name: product.name,
        price: parseFloat(product.price),
        quantity: product.quantity || 1
    };

    if (product.variant) productData.variant = product.variant;

    trackEcommerce('remove', [productData]);
}

/**
 * Отслеживание покупки
 * @param {string} orderId - Номер заказа
 * @param {number} revenue - Общая сумма
 * @param {array} products - Массив товаров в заказе
 * @param {string} coupon - Код купона (опционально)
 */
function trackPurchase(orderId, revenue, products, coupon = '') {
    const actionField = {
        id: orderId,
        revenue: parseFloat(revenue)
    };

    if (coupon) {
        actionField.coupon = coupon;
    }

    trackEcommerce('purchase', products, actionField);
}

/**
 * Отслеживание просмотра товара
 * @param {object} product - Объект товара
 */
function trackViewProduct(product) {
    const productData = {
        id: String(product.id),
        name: product.name,
        price: parseFloat(product.price)
    };

    if (product.brand) productData.brand = product.brand;
    if (product.category) productData.category = product.category;
    if (product.variant) productData.variant = product.variant;

    trackEcommerce('detail', [productData]);
}

/**
 * Отслеживание клика по товару в списке
 * @param {object} product - Объект товара
 * @param {string} list - Название списка (опционально)
 */
function trackProductClick(product, list = '') {
    const productData = {
        id: String(product.id),
        name: product.name,
        price: parseFloat(product.price)
    };

    if (list) productData.list = list;
    if (product.position) productData.position = product.position;

    trackEcommerce('click', [productData]);
}

/**
 * Отслеживание просмотра списка товаров
 * @param {array} products - Массив товаров
 * @param {string} listName - Название списка
 */
function trackProductImpressions(products, listName = 'Product List') {
    const productsData = products.map(product => ({
        id: String(product.id),
        name: product.name,
        price: parseFloat(product.price),
        list: listName,
        position: product.position || 1
    }));

    trackEcommerce('impressions', productsData);
}

/**
 * Helper: getCookie для CSRF токена
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * API: Добавить/удалить товар из корзины с отслеживанием
 * @param {number} productId - ID товара
 * @param {function} onSuccess - Callback при успехе
 */
async function toggleCartWithTracking(productId, onSuccess = null) {
    try {
        const response = await fetch('/api/cart/toggle/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ product_id: productId })
        });

        const data = await response.json();

        if (data.ok && data.action && data.product) {
            // Отправляем в Метрику
            if (data.action === 'add') {
                trackAddToCart(data.product);
            } else if (data.action === 'remove') {
                trackRemoveFromCart(data.product);
            }

            if (onSuccess) {
                onSuccess(data);
            }
        }

        return data;
    } catch (error) {
        console.error('Error toggling cart:', error);
        throw error;
    }
}

/**
 * API: Добавить товар в корзину с количеством и размером
 * @param {number} productId - ID товара
 * @param {number} qty - Количество
 * @param {number} sizeId - ID размера (опционально)
 * @param {function} onSuccess - Callback при успехе
 */
async function addToCartWithTracking(productId, qty = 1, sizeId = null, onSuccess = null) {
    try {
        const payload = {
            product_id: productId,
            qty: qty
        };
        if (sizeId) {
            payload.size_id = sizeId;
        }

        const response = await fetch('/api/cart/add/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (data.ok && data.item) {
            // Отправляем в Метрику
            const product = {
                id: data.item.product_id,
                name: data.item.product_name,
                price: data.item.price,
                quantity: data.item.quantity,
                variant: data.item.size_name || ''
            };
            trackAddToCart(product);

            if (onSuccess) {
                onSuccess(data);
            }
        }

        return data;
    } catch (error) {
        console.error('Error adding to cart:', error);
        throw error;
    }
}

/**
 * API: Удалить товар из корзины с отслеживанием
 * @param {number} itemId - ID позиции в корзине
 * @param {object} itemData - Данные товара для отслеживания
 * @param {function} onSuccess - Callback при успехе
 */
async function removeFromCartWithTracking(itemId, itemData, onSuccess = null) {
    try {
        const response = await fetch('/api/cart/remove/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ item_id: itemId })
        });

        const data = await response.json();

        if (data.ok) {
            // Отправляем в Метрику
            if (itemData) {
                trackRemoveFromCart(itemData);
            }

            if (onSuccess) {
                onSuccess(data);
            }
        }

        return data;
    } catch (error) {
        console.error('Error removing from cart:', error);
        throw error;
    }
}

/**
 * API: Оформить заказ с отслеживанием покупки
 * Требует создать соответствующий endpoint на backend
 * @param {object} orderData - Данные заказа
 * @param {function} onSuccess - Callback при успехе
 */
async function checkoutWithTracking(orderData, onSuccess = null) {
    try {
        const response = await fetch('/api/order/create/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(orderData)
        });

        const data = await response.json();

        if (data.ok && data.order_id) {
            // Отправляем в Метрику
            const products = (data.products || []).map(p => ({
                id: String(p.id),
                name: p.name,
                price: parseFloat(p.price),
                quantity: p.quantity
            }));

            trackPurchase(
                `ORDER#${data.order_id}`,
                parseFloat(data.total),
                products,
                data.coupon || ''
            );

            if (onSuccess) {
                onSuccess(data);
            }
        }

        return data;
    } catch (error) {
        console.error('Error during checkout:', error);
        throw error;
    }
}


