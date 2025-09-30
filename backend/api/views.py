from django.http import HttpResponse
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import(
    AllowAny,
    IsAuthenticated, 
    IsAuthenticatedOrReadOnly
)
from rest_framework.response import Response
from djoser.views import UserViewSet
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from users import models
from .filters import RecipeFilter

from .serializers import (
    FollowSerializer,
    TagSerializer,
    IngredientSerializer,
    RecipeWriteSerializer,
    RecipeReadSerializer,
    RecipeShortSerializer,
    CustomUserSerializer
)
from users.models import User
from recipes.models import (
    Recipe, RecipeIngredient, Tag, Ingredient, Favorite, ShoppingCart
)
from .pagination import CustomPaginator
from .permissions import IsAuthorOrReadOnly

class CustomUserViewset(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = CustomPaginator

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'create'):
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def subscribe(self, request, pk=None):
        """Подписка / отписка на автора"""
        author = get_object_or_404(User, pk=pk)

        if author == request.user:
            return Response(
                {'errors': 'Нельзя подписаться на себя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == 'POST':
            if request.user.subscriptions.filter(pk=author.pk).exists():
                return Response(
                    {'errors': 'Уже подписаны'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.user.subscriptions.add(author)
            serializer = FollowSerializer(author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # DELETE
        if not request.user.subscriptions.filter(pk=author.pk).exists():
            return Response(
                {'errors': 'Вы не подписаны'},
                status=status.HTTP_400_BAD_REQUEST
            )
        request.user.subscriptions.remove(author)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        """Список авторов, на которых подписан пользователь"""
        authors = request.user.subscriptions.all()
        page = self.paginate_queryset(authors)
        serializer = FollowSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = CustomPaginator
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'get_link']:
            return [AllowAny()]
        return [IsAuthenticated(), IsAuthorOrReadOnly()]

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        recipe = serializer.save(author=self.request.user)
        read_serializer = RecipeReadSerializer(recipe, context={'request': self.request})
        self.response = Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if hasattr(self, 'response'):
            return self.response
        return response

    def perform_update(self, serializer):
        recipe = serializer.save()
        read_serializer = RecipeReadSerializer(recipe, context={'request': self.request})
        self.response = Response(read_serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if hasattr(self, 'response'):
            return self.response
        return response

    def perform_destroy(self, instance):
        instance.delete()

    @action(detail=True, methods=['get'], url_path='get-link', permission_classes=[AllowAny])
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        serializer = RecipeLinkSerializer(recipe, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            if ShoppingCart.objects.filter(user=request.user, recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже в корзине'}, status=status.HTTP_400_BAD_REQUEST)
            ShoppingCart.objects.create(user=request.user, recipe=recipe)
            serializer = RecipeShortSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)


        cart_item = ShoppingCart.objects.filter(user=request.user, recipe=recipe)
        if not cart_item.exists():
            return Response({'errors': 'Этого рецепта нет в корзине'}, status=status.HTTP_400_BAD_REQUEST)
        cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        ingredients = (
            RecipeIngredient.objects
            .filter(recipe__cart_items__user=request.user)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(total_amount=models.Sum('amount'))
        )

        lines = [
            f"{item['ingredient__name']} ({item['ingredient__measurement_unit']}) — {item['total_amount']}"
            for item in ingredients
        ]

        response = HttpResponse('\n'.join(lines), content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="shopping_cart.txt"'
        return response
    
    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            if Favorite.objects.filter(user=request.user, recipe=recipe).exists():
                return Response({'errors': 'Рецепт уже в избранном'}, status=status.HTTP_400_BAD_REQUEST)
            Favorite.objects.create(user=request.user, recipe=recipe)
            serializer = RecipeShortSerializer(recipe, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # DELETE
        favorite_item = Favorite.objects.filter(user=request.user, recipe=recipe)
        if not favorite_item.exists():
            return Response({'errors': 'Рецепта нет в избранном'}, status=status.HTTP_400_BAD_REQUEST)
        favorite_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)