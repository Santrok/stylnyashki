"""Tests for the Стильняшки store application."""

from decimal import Decimal
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User

from .models import Product, SizeOption, Cart, CartItem


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost'])
class PageRenderTests(TestCase):
    """Verify that all public server-rendered pages return HTTP 200."""

    def test_home(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_catalog(self):
        response = self.client.get(reverse('catalog'))
        self.assertEqual(response.status_code, 200)

    def test_cart(self):
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)

    def test_login(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_register(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_checkout_redirects_when_anonymous(self):
        response = self.client.get(reverse('checkout'))
        self.assertRedirects(response, '/login/?next=/checkout/', fetch_redirect_response=False)

    def test_account_redirects_when_anonymous(self):
        response = self.client.get(reverse('account'))
        self.assertRedirects(response, '/login/?next=/account/', fetch_redirect_response=False)


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost'])
class AuthTests(TestCase):
    """Test registration and login flows."""

    def test_register_creates_user_and_redirects(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'SecurePass123!',
            'password2': 'SecurePass123!',
        })
        self.assertRedirects(response, reverse('account'), fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_register_mismatched_passwords_shows_error(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'password1': 'pass1',
            'password2': 'pass2',
        })
        self.assertEqual(response.status_code, 200)

    def test_login_valid_credentials_redirects(self):
        User.objects.create_user('loginuser', password='TestPass123!')
        response = self.client.post(reverse('login'), {
            'username': 'loginuser',
            'password': 'TestPass123!',
        })
        self.assertRedirects(response, '/account/', fetch_redirect_response=False)

    def test_login_invalid_credentials_shows_error(self):
        response = self.client.post(reverse('login'), {
            'username': 'nobody',
            'password': 'wrong',
        })
        self.assertEqual(response.status_code, 200)

    def test_logout_redirects_to_home(self):
        User.objects.create_user('logoutuser', password='pass')
        self.client.login(username='logoutuser', password='pass')
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost'])
class ProductModelTests(TestCase):
    """Test Product model properties and SizeOption."""

    def setUp(self):
        self.product = Product.objects.create(
            name='Test Dress',
            brand='BrandX',
            category='Платья',
            season='Лето',
            price=Decimal('1000.00'),
            discount=20,
            is_active=True,
        )

    def test_discounted_price(self):
        self.assertEqual(self.product.discounted_price, Decimal('800.00'))

    def test_no_discount(self):
        p = Product.objects.create(name='No Discount', price=Decimal('500.00'))
        self.assertEqual(p.discounted_price, Decimal('500.00'))

    def test_str(self):
        self.assertEqual(str(self.product), 'Test Dress')

    def test_size_option_str(self):
        size = SizeOption.objects.create(value='M')
        self.assertEqual(str(size), 'M')


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost'])
class CartTests(TestCase):
    """Test cart add/remove functionality."""

    def setUp(self):
        self.product = Product.objects.create(
            name='Cart Item', price=Decimal('500.00'), is_active=True
        )

    def test_add_to_cart(self):
        response = self.client.post(reverse('cart_add', args=[self.product.id]))
        self.assertRedirects(response, reverse('cart'), fetch_redirect_response=False)

    def test_cart_total(self):
        cart = Cart.objects.create(session_key='test-session')
        item = CartItem.objects.create(cart=cart, product=self.product, quantity=3)
        self.assertEqual(cart.total, Decimal('1500.00'))

    def test_cart_item_subtotal(self):
        cart = Cart.objects.create(session_key='test-session')
        item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        self.assertEqual(item.subtotal, Decimal('1000.00'))


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost'])
class ApiTests(TestCase):
    """Test DRF API endpoints."""

    def setUp(self):
        self.product = Product.objects.create(
            name='API Product', brand='BrandZ', category='Блузки',
            price=Decimal('300.00'), is_active=True
        )

    def test_product_list(self):
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)

    def test_product_detail(self):
        response = self.client.get(f'/api/products/{self.product.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'API Product')

    def test_product_filter_by_category(self):
        Product.objects.create(name='Other', category='Брюки', price=100, is_active=True)
        response = self.client.get('/api/products/?category=Блузки')
        self.assertEqual(response.json()['count'], 1)

    def test_cart_api(self):
        response = self.client.get('/api/cart/')
        self.assertEqual(response.status_code, 200)

    def test_catalog_filter(self):
        response = self.client.get(reverse('catalog') + '?category=Блузки')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'API Product')
