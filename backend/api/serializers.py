from rest_framework import serializers, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from drf_extra_fields.fields import Base64ImageField

from recipes.models import Recipe, Tag, Ingredient, RecipeIngredient, Favorite, ShoppingCart
from users.models import User
from .pagination import CustomPaginator

User = get_user_model()


class CustomUserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return request.user.subscriptions.filter(id=obj.id).exists()


class CustomCreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password',
        )
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class FollowSerializer(CustomUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(CustomUserSerializer.Meta):
        fields = CustomUserSerializer.Meta.fields + (
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = obj.recipes.all()
        limit = request.query_params.get('recipes_limit') if request else None
        if limit and limit.isdigit():
            recipes = recipes[:int(limit)]
        return RecipeShortSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')

    def to_representation(self, instance):
        return {
            'id': instance.ingredient.id,
            'name': instance.ingredient.name,
            'measurement_unit': instance.ingredient.measurement_unit,
            'amount': instance.amount,
        }


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeWriteSerializer(serializers.ModelSerializer):
    image = Base64ImageField()
    ingredients = RecipeIngredientWriteSerializer(
        many=True, source='recipe_ingredients'
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'text',
            'cooking_time',
            'tags',
            'ingredients',
        )

    def validate(self, data):
        ingredients = data.get('recipe_ingredients')
        tags = data.get('tags')
        image = data.get('image')

        if ingredients is None:
            raise serializers.ValidationError(
                {'ingredients': 'Обязательное поле.'}
            )
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Список ингредиентов не может быть пустым.'}
            )

        seen_ingredients = set()
        for item in ingredients:
            ing_id = (
                item['id'].id if isinstance(item['id'], Ingredient)
                else item['id']
            )
            if ing_id in seen_ingredients:
                raise serializers.ValidationError(
                    {'ingredients': 'Ингредиенты не должны повторяться.'}
                )
            seen_ingredients.add(ing_id)
            if item['amount'] < 1:
                raise serializers.ValidationError(
                    {'ingredients': 'Количество должно быть больше 0.'}
                )

        if tags is None:
            raise serializers.ValidationError({'tags': 'Обязательное поле.'})
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Список тегов не может быть пустым.'}
            )
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                {'tags': 'Теги не должны повторяться.'}
            )

        if not image:
            raise serializers.ValidationError({'image': 'Картинка обязательна.'})

        return data

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients_data = validated_data.pop('recipe_ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)

        for ingredient in ingredients_data:
            RecipeIngredient.objects.update_or_create(
                recipe=recipe,
                ingredient=ingredient['id'],
                defaults={'amount': ingredient['amount']}
            )
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        ingredients_data = validated_data.pop('recipe_ingredients', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tags is not None:
            instance.tags.set(tags)

        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            for ingredient in ingredients_data:
                RecipeIngredient.objects.update_or_create(
                    recipe=instance,
                    ingredient=ingredient['id'],
                    defaults={'amount': ingredient['amount']}
                )
        return instance


class RecipeReadSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    author = CustomUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True, source='recipe_ingredients'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'author',
            'name',
            'image',
            'text',
            'cooking_time',
            'tags',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
        )

    def get_image(self, obj):
        return obj.image.url if obj.image else ''

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and Favorite.objects.filter(user=user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and ShoppingCart.objects.filter(user=user, recipe=obj).exists()
    
class RecipeLinkSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    short_link = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'short_link')

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return ""

    def get_short_link(self, obj):
        request = self.context.get('request')
        if obj.short_code and request:
            return request.build_absolute_uri(f'/s/{obj.short_code}/')
        return ""