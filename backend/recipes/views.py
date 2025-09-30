from django.shortcuts import redirect

from recipes.models import Recipe


def redirect_short_link(request, short_code):
    """Перенаправление по короткой ссылке на рецепт."""
    try:
        recipe = Recipe.objects.get(short_code=short_code)
        return redirect(f'/recipes/{recipe.pk}/')
    except Recipe.DoesNotExist:
        return redirect('/404/')