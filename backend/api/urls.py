from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import RecipeViewSet, TagViewSet, IngredientViewSet, CustomUserViewset

router = DefaultRouter()
router.register('tags', TagViewSet, basename='tags')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('recipes', RecipeViewSet, basename='recipes')
router.register('users', CustomUserViewset, basename='users')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]