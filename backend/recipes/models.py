from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db.models import (
    CASCADE,
    SET_NULL,
    CharField,
    ForeignKey,
    ImageField,
    ManyToManyField,
    Model,
    PositiveIntegerField,
    SlugField,
    TextField,
    UniqueConstraint
)
from django.urls import reverse

from foodgram.constants import COOKING_TIME_MIN_VALUE, INGREDIENT_MIN_AMOUNT

User = get_user_model()

COOKING_TIME_MIN_ERROR = (
    'Время приготовления не может быть меньше одной минуты!'
)
INGREDIENT_MIN_AMOUNT_ERROR = (
    'Количество ингредиентов не может быть меньше {min_value}!'
)

FIELD_NAME = 'Название'
COLOR_HEX = 'Цвет в HEX'
UNIT = 'Единица измерения'
SLUG = 'Слаг'
MAX_LENGTH = 200
MAX_LENGTH_HEX = 6


class Ingredient(Model):
    name = CharField(FIELD_NAME, max_length=MAX_LENGTH)
    measurement_unit = CharField(UNIT, max_length=MAX_LENGTH)

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)

    def __str__(self):
        return f'{self.name}'


class Tag(Model):
    name = CharField(FIELD_NAME, max_length=MAX_LENGTH)
    color = CharField(COLOR_HEX, max_length=MAX_LENGTH_HEX)
    slug = SlugField(SLUG, max_length=MAX_LENGTH)

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return f'{self.name}'

    def get_absolute_url(self):
        return reverse('tag', args=[self.slug])


class Recipe(Model):
    name = CharField(FIELD_NAME, max_length=MAX_LENGTH)
    text = TextField('Описание')
    ingredients = ManyToManyField(
        'CountOfIngredient',
        verbose_name='Ингредиенты'
    )
    tags = ManyToManyField(
        Tag,
        verbose_name='Теги'
    )
    image = ImageField('Картинка')
    cooking_time = PositiveIntegerField(
        'Время приготовления',
        validators=(MinValueValidator(
            COOKING_TIME_MIN_VALUE,
            message=COOKING_TIME_MIN_ERROR,
        ),)
    )
    author = ForeignKey(
        User,
        on_delete=SET_NULL,
        null=True,
        verbose_name='Автор',
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pk',)

    def __str__(self):
        return f'{self.name} ({self.author})'

    def get_absoulute_url(self):
        return reverse('recipe', args=[self.pk])


class CountOfIngredient(Model):
    ingredient = ForeignKey(
        Ingredient,
        on_delete=CASCADE,
        related_name='count_in_recipes',
        verbose_name='Ингредиент',
    )
    amount = PositiveIntegerField(
        'Количество',
        validators=(MinValueValidator(
            INGREDIENT_MIN_AMOUNT,
            message=INGREDIENT_MIN_AMOUNT_ERROR.format(
                min_value=INGREDIENT_MIN_AMOUNT
            )
        ),)
    )

    class Meta:
        verbose_name = 'Количество ингредиента'
        verbose_name_plural = 'Количество ингредиентов'
        constraints = (
            UniqueConstraint(
                fields=('ingredient', 'amount',),
                name='unique_ingredient_amount',
            ),
        )

    def __str__(self):
        return (
            f'{self.ingredient.name} - {self.amount}'
            f' ({self.ingredient.measurement_unit})'
        )


class Favorite(Model):
    user = ForeignKey(
        User,
        on_delete=CASCADE,
        verbose_name='Пользователь',
    )
    recipe = ForeignKey(
        Recipe,
        on_delete=CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        default_related_name = 'favorites'
        constraints = (
            UniqueConstraint(
                fields=('user', 'recipe',),
                name='unique_user_recipe',
            ),
        )

    def __str__(self):
        return f'{self.user} -> {self.recipe}'
