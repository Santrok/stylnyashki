import re
from functools import partial
from itertools import groupby
from operator import attrgetter

from django import forms
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.models import User
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.forms.models import ModelChoiceIterator, ModelChoiceField

from .models import Address, Order, SizeOption, Category, Product

username_validator = UnicodeUsernameValidator()


class LoginForm(forms.Form):
    username = forms.CharField(label='Имя пользователя', max_length=150)
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        cleaned = super().clean()
        username = (cleaned.get('username') or '').strip()
        password = cleaned.get('password') or ''

        if not username or not password:
            raise ValidationError('Введите логин и пароль.')

        user = authenticate(self.request, username=username, password=password)
        if user is None:
            raise ValidationError('Неверный логин или пароль.')

        self.user = user
        return cleaned


class RegisterForm(forms.Form):
    username = forms.CharField(label='Имя пользователя', max_length=150)
    phone = forms.CharField(label='Телефон (BY)', required=False, max_length=32)
    email = forms.EmailField(label='E-mail', required=False)
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Повторите пароль', widget=forms.PasswordInput)
    check__input = forms.BooleanField(required=True)

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise ValidationError('Введите имя пользователя.')
        if User.objects.filter(username=username).exists():
            raise ValidationError('Пользователь с таким именем уже существует.')
        return username

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        if not phone:
            return ''

        # оставляем только цифры
        digits = re.sub(r'\D+', '', phone)

        # варианты:
        # +375XXYYYYYYY -> digits startswith 375 + 9 digits
        # 375XXYYYYYYY
        # 80XXYYYYYYY
        if digits.startswith('375'):
            rest = digits[3:]
        elif digits.startswith('80'):
            rest = digits[2:]
        else:
            # иногда вводят 29XXXXXXX — разрешим как локальный (9 цифр) и добавим +375
            rest = digits

        if len(rest) != 9:
            raise ValidationError('Введите белорусский номер: +375 (XX) XXX-XX-XX')

        # базовая проверка кода оператора/региона (BY)
        code = rest[:2]
        allowed_codes = {
            # мобильные
            '25', '29', '33', '44',
            # городские (часто встречающиеся)
            '17',  # Минск
            '15', '16', '21', '22', '23'  # регионы (грубо)
        }
        if code not in allowed_codes:
            raise ValidationError('Проверьте код номера (пример: +375 29 ...).')

        return f'+375{rest}'

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1') or ''
        p2 = cleaned.get('password2') or ''

        if p1 and p2 and p1 != p2:
            raise ValidationError('Пароли не совпадают.')

        # прогоняем через стандартные валидаторы Django
        if p1:
            # временный user объект нужен для UserAttributeSimilarityValidator
            tmp_user = User(username=cleaned.get('username') or '', email=cleaned.get('email') or '')
            try:
                password_validation.validate_password(p1, user=tmp_user)
            except ValidationError as e:
                # покажем как ошибки поля password1
                self.add_error('password1', e)

        return cleaned

    def save(self):
        username = self.cleaned_data['username']
        email = self.cleaned_data.get('email') or ''
        password = self.cleaned_data['password1']
        return User.objects.create_user(username=username, email=email, password=password)


def normalize_by_phone(phone: str) -> str:
    phone = (phone or "").strip()
    if not phone:
        return ""

    digits = re.sub(r"\D+", "", phone)

    if digits.startswith("375"):
        rest = digits[3:]
    elif digits.startswith("80"):
        rest = digits[2:]
    else:
        rest = digits

    if len(rest) != 9:
        raise ValidationError("Введите белорусский номер: +375 (XX) XXX-XX-XX")

    code = rest[:2]
    allowed_codes = {"25", "29", "33", "44", "17", "15", "16", "21", "22", "23"}
    if code not in allowed_codes:
        raise ValidationError("Проверьте код номера (пример: +375 29 ...).")

    return f"+375{rest}"


class AccountForm(forms.Form):
    username = forms.CharField(max_length=150, label="Username")
    first_name = forms.CharField(max_length=150, required=False, label="Имя")
    last_name = forms.CharField(max_length=150, required=False, label="Фамилия")
    email = forms.EmailField(required=False, label="E-mail")

    phone = forms.CharField(max_length=32, required=False, label="Телефон (BY)")
    city = forms.CharField(max_length=64, required=False, label="Город")
    instagram_username = forms.CharField(max_length=64, required=False, label="Instagram")

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise ValidationError("Введите username.")

        username_validator(username)

        qs = User.objects.filter(username=username).exclude(pk=self.user.pk)
        if qs.exists():
            raise ValidationError("Этот username уже занят.")
        return username

    def clean_phone(self):
        return normalize_by_phone(self.cleaned_data.get("phone") or "")

    def clean_instagram_username(self):
        val = (self.cleaned_data.get("instagram_username") or "").strip()
        if not val:
            return ""
        val = val.lstrip("@")
        # Instagram: латиница/цифры/._ и не более 30 символов (у них лимит 30)
        if not re.fullmatch(r"[A-Za-z0-9._]{1,30}", val):
            raise ValidationError("Instagram ник: только латиница/цифры/._ (до 30 символов).")
        return val

    def save(self):
        u = self.user
        u.username = self.cleaned_data["username"]
        u.first_name = self.cleaned_data.get("first_name", "")
        u.last_name = self.cleaned_data.get("last_name", "")
        u.email = self.cleaned_data.get("email", "")
        u.save()

        profile = getattr(u, "profile", None)
        if profile is None:
            # если signals не подключены — подстрахуемся
            from .models import Profile
            profile = Profile.objects.create(user=u)

        profile.phone = self.cleaned_data.get("phone", "")
        profile.city = self.cleaned_data.get("city", "")
        profile.instagram_username = self.cleaned_data.get("instagram_username", "")
        profile.save()

        return u


class PostalAddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            "last_name", "first_name", "middle_name", "phone",
            "postal_index", "city", "street", "house", "apartment",
        ]

    def clean_middle_name(self):
        val = (self.cleaned_data.get("middle_name") or "").strip()
        if not val:
            raise ValidationError("Введите отчество.")
        return val

    def clean_phone(self):
        return normalize_by_phone(self.cleaned_data.get("phone"))

    def clean_postal_index(self):
        val = (self.cleaned_data.get("postal_index") or "").strip()
        if not val:
            raise ValidationError("Введите почтовый индекс.")
        return val

    def clean_city(self):
        val = (self.cleaned_data.get("city") or "").strip()
        if not val:
            raise ValidationError("Введите город.")
        return val

    def clean_street(self):
        val = (self.cleaned_data.get("street") or "").strip()
        if not val:
            raise ValidationError("Введите улицу.")
        return val

    def clean_house(self):
        val = (self.cleaned_data.get("house") or "").strip()
        if not val:
            raise ValidationError("Введите дом.")
        return val


class EuropostAddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            "last_name", "first_name", "middle_name", "phone",
            "europost_branch_number",
        ]

    def clean_middle_name(self):
        val = (self.cleaned_data.get("middle_name") or "").strip()
        if not val:
            raise ValidationError("Введите отчество.")
        return val

    def clean_phone(self):
        return normalize_by_phone(self.cleaned_data.get("phone"))

    def clean_europost_branch_number(self):
        val = (self.cleaned_data.get("europost_branch_number") or "").strip()
        if not val:
            raise ValidationError("Введите номер отделения Европочты.")
        return val


class CheckoutForm(forms.Form):
    delivery_type = forms.ChoiceField(
        choices=Order.DeliveryType.choices,
        required=True,
        label="Тип доставки",
    )

    payment_method = forms.ChoiceField(
        choices=Order.PaymentMethod.choices,
        required=True,
        label="Способ оплаты",
    )

    # contacts
    first_name = forms.CharField(max_length=150, required=True, label="Имя")
    last_name = forms.CharField(max_length=150, required=True, label="Фамилия")
    middle_name = forms.CharField(max_length=150, required=True, label="Отчество")
    phone = forms.CharField(max_length=32, required=True, label="Телефон")
    instagram = forms.CharField(max_length=64, required=True, label="Instagram")
    email = forms.EmailField(required=True, label="Email")

    # post
    postal_index = forms.CharField(max_length=16, required=False, label="Почтовый индекс")
    city = forms.CharField(max_length=64, required=False, label="Город")
    street = forms.CharField(max_length=128, required=False, label="Улица")
    house = forms.CharField(max_length=32, required=False, label="Дом")
    apartment = forms.CharField(max_length=32, required=False, label="Квартира")

    # europost
    europost_branch_number = forms.CharField(max_length=32, required=False, label="Номер отделения Европочты")

    comment = forms.CharField(required=False, widget=forms.Textarea, label="Комментарий")

    def clean_phone(self):
        return normalize_by_phone(self.cleaned_data.get("phone"))

    def clean_instagram(self):
        val = (self.cleaned_data.get("instagram") or "").strip()
        if not val:
            raise ValidationError("Укажите Instagram для связи.")

        # допускаем ссылку/собачку/пробелы — приводим к username
        val = val.replace("https://instagram.com/", "").replace("https://www.instagram.com/", "")
        val = val.strip().lstrip("@").strip()
        val = re.sub(r"\s+", "", val)

        if not re.fullmatch(r"[A-Za-z0-9._]{1,30}", val):
            raise ValidationError("Некорректный Instagram username.")
        return val

    def clean(self):
        cleaned = super().clean()
        dt = cleaned.get("delivery_type")

        if dt == Order.DeliveryType.POST:
            required_fields = ["postal_index", "city", "street", "house"]
            for f in required_fields:
                if not (cleaned.get(f) or "").strip():
                    self.add_error(f, "Обязательное поле.")
        elif dt == Order.DeliveryType.EUROPOST:
            if not (cleaned.get("europost_branch_number") or "").strip():
                self.add_error("europost_branch_number", "Обязательное поле.")
        else:
            self.add_error("delivery_type", "Выберите способ доставки.")

        pm = cleaned.get("payment_method")
        pm_choices = {c[0] for c in Order.PaymentMethod.choices}
        if not pm or pm not in pm_choices:
            self.add_error("payment_method", "Выберите способ оплаты.")

        return cleaned



class GroupedModelChoiceIterator(ModelChoiceIterator):
    """
    Расширение базового класса и переопределение итератора для создания
    сгруппированных значений optgroup селектора выбора
    """
    def __init__(self, field, group_by):
        self.group_by = group_by
        super().__init__(field)

    def __iter__(self):
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)
        queryset = self.queryset
        if not queryset._prefetch_related_lookups:
            queryset = queryset.iterator()
        for group, objs in groupby(queryset, self.group_by):
            yield (group, [self.choice(obj) for obj in objs])


class GroupedModelChoiceField(ModelChoiceField):
    """
    Расширение базового класса для создания
    селектора выбора с использованием расширенного итератора
    """
    def __init__(self, *args, choices_group_by, **kwargs):
        if isinstance(choices_group_by, str):
            choices_group_by = attrgetter(choices_group_by)
        elif not callable(choices_group_by):
            raise TypeError(
                'choice_group_by должен быть либо строкой, либо вызываемым объектом, принимающим один аргумент')
        self.iterator = partial(GroupedModelChoiceIterator, group_by=choices_group_by)
        super().__init__(*args, **kwargs)


class ProductBulkForm(forms.ModelForm):
    sizes = forms.ModelChoiceField(
        queryset=SizeOption.objects.all(),
        required=False,
        widget=forms.Select(attrs={
            "id": "sizes",
            "class": "f__input"
        }), empty_label=None
    )

    category = GroupedModelChoiceField(queryset=Category.objects.filter(level=1).prefetch_related('parent'),
                                       choices_group_by='parent',
                                       label="Раздел",
                                       required=True,
                                       widget=forms.Select(attrs={'size': 1, "id": "category_id", "class": "f__input"}), empty_label=None)


    class Meta:
        model = Product
        fields = ["name", "brand", "category", "season", "price", "discount", "is_active", "status", "sizes"]
        widgets = {
            "name": forms.TextInput(attrs={"id": "name", "class": "f__input"}),
            "brand": forms.TextInput(attrs={"id": "brand", "class": "f__input"}),
            "season": forms.TextInput(attrs={"id": "season", "class": "f__input"}),
            "price": forms.NumberInput(attrs={"id": "price", "class": "f__input", "step": "0.01", "min": "0"}),
            "discount": forms.NumberInput(attrs={"id": "discount", "class": "f__input", "min": "0", "max": "100"}),
            "is_active": forms.CheckboxInput(attrs={"id": "is_active"}),
            "status": forms.Select(attrs={"id": "status", "class": "f__input"}),
        }
        labels = {
            "is_active": "Активен",
            "status": "Статус",
        }

class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'f__input', 'id': 'id_status'}),
        }