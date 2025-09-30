from django.contrib.auth import get_user_model
import uuid
from django.db import models
from colorfield.fields import ColorField
from django.core.validators import MinValueValidator

User = get_user_model()


class Tag(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Название тега',
    )
    slug = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name='Слаг',
    )
    color = ColorField(
        default='#FF0000',
        format='hex',
        verbose_name='Цвет',
    )

    class Meta:
        ordering = ('id',)
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name='Ингредиент',
    )
    measurement_unit = models.CharField(
        max_length=50,
        verbose_name='Единица измерения',
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        unique_together = (
            'name',
            'measurement_unit'
        )

    def __str__(self):
        return f'{self.name} ({self.measurement_unit})'


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор',
    )
    tags = models.ManyToManyField(
        Tag,
        through='RecipeTag',
        related_name='recipes',
        verbose_name='Теги',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингредиенты',
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Название'
    )
    text = models.TextField(
        verbose_name='Описание'
    )
    image = models.ImageField(
        upload_to='recipes',
        verbose_name='Картинка'
    )
    cooking_time = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(
                1, 'Минимальное время — 1 мин'
            )
        ],
        verbose_name='Время приготовления',
    )
    created = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )

    short_code = models.CharField(
        max_length=20,
        blank=True,
        default=""
    )


    class Meta:
        ordering = ('-created',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
    )
    amount = models.PositiveIntegerField(
        validators=[MinValueValidator(1, 'Минимум 1')],
        verbose_name='Количество',
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=('ingredient', 'recipe'),
                name='unique_ingredient_in_recipe',
            )
        ]

    def __str__(self):
        return f'{self.ingredient.name} — {self.amount} {self.ingredient.measurement_unit}'
    

class RecipeTag(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_tags'
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name='tag_recipes'
    )

    class Meta:
        verbose_name = 'Тег рецепта'
        verbose_name_plural = 'Теги рецептов'
        constraints = [
            models.UniqueConstraint(
                fields=('recipe', 'tag'),
                name='unique_recipe_tag'
            )
        ]

    def __str__(self):
        return f'{self.recipe.name} — {self.tag.name}'


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_shopping_cart',
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_shopping_cart'
            )
        ]


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorites',
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_favorite'
            )
        ]