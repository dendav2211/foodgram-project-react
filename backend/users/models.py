from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db.models import (
    CASCADE,
    BooleanField,
    CharField,
    EmailField,
    ForeignKey,
    ManyToManyField,
    Model,
    OneToOneField,
)

from .managers import UserManager

SHOPPING_CART_RECIPE_ALREADY_EXISTS_ERROR = (
    'Данный рецепт уже есть в вашем списке покупок!'
)

MAX_LENGTH = 150


class User(AbstractBaseUser, PermissionsMixin):
    email = EmailField('Почта', max_length=254, unique=True)
    username = CharField('Никнейм', max_length=MAX_LENGTH)
    first_name = CharField('Имя', max_length=MAX_LENGTH)
    last_name = CharField('Фамилия', max_length=MAX_LENGTH)
    password = CharField('Пароль', max_length=MAX_LENGTH)
    is_superuser = BooleanField('Администратор', default=False)
    is_blocked = BooleanField('Заблокирован', default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = UserManager()

    def generate_shopping_cart_data(self):
        recipes = self.shopping_cart.recipes.prefetch_related('ingredients')
        return (
            recipes.order_by('ingredients__ingredient__name')
            .values('ingredients__ingredient__name',
                    'ingredients__ingredient__measurement_unit')
            .annotate(total=Sum('ingredients__amount'))
        )

    class Meta:
        ordering = ('-pk',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username

    @property
    def is_staff(self):
        return self.is_superuser


class Subscribe(Model):
    user = ForeignKey(
        User,
        on_delete=CASCADE,
        related_name='subscriber',
        verbose_name='Подписчик'
    )
    author = ForeignKey(
        User,
        on_delete=CASCADE,
        related_name='subscribing',
        verbose_name='Автор'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f'{self.user} -> {self.author}'

    def clean(self):
        if self.user == self.author:
            raise ValidationError('Пользователь не может подписаться на самого себя!')


class ShoppingCart(Model):
    user = OneToOneField(
        User,
        on_delete=CASCADE,
        related_name='shopping_cart',
        verbose_name='Пользователь',
        unique=True,
    )
    recipes = ManyToManyField(
        'recipes.Recipe',
        related_name='in_shopping_cart',
        verbose_name='Рецепты',
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'

    def __str__(self):
        return f'{self.user}'
