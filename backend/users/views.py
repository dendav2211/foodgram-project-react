from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from djoser.views import TokenCreateView, UserViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
)
from rest_framework.viewsets import GenericViewSet

from foodgram.constants import ERRORS_KEY
from api.pagination import LimitPageNumberPagination
from recipes.models import Recipe
from api.serializers.nested import RecipeShortReadSerializer
from .models import ShoppingCart, Subscribe, User
from .serializers import SubscriptionSerializer

FILE_NAME = 'shopping_cart.txt'

SUBSCRIBE_CANNOT_CREATE_TO_YOURSELF = 'Нельзя подписаться на самого себя!'
SUBSCRIBE_CANNOT_CREATE_TWICE = 'Нельзя подписаться дважды!'
SUBSCRIBE_CANNOT_DELETE = (
    'Нельзя отписаться от данного пользователя,'
    ' если вы не подписаны на него!'
)

USER_BLOCKED = 'Данный аккаунт временно заблокирован!'
USER_NOT_FOUND = 'Пользователь не найден!'

SHOPPING_CART_DOES_NOT_EXIST = 'Список покупок не существует!'
SHOPPING_CART_RECIPE_CANNOT_ADD_TWICE = 'Рецепт уже добавлен!'
SHOPPING_CART_RECIPE_CANNOT_DELETE = (
    'Нельзя удалить рецепт из списка покупок, которого нет'
    ' в списке покупок!'
)


class TokenCreateWithCheckBlockStatusView(TokenCreateView):
    def _action(self, serializer):
        if serializer.user.is_blocked:
            return Response(
                {ERRORS_KEY: USER_BLOCKED},
                status=HTTP_400_BAD_REQUEST,
            )
        return super()._action(serializer)


class UserSubscribeViewSet(UserViewSet):
    pagination_class = LimitPageNumberPagination
    lookup_url_kwarg = 'user_id'

    def get_subscription_serializer(self, *args, **kwargs):
        kwargs.setdefault('context', self.get_serializer_context())
        return SubscriptionSerializer(*args, **kwargs)

    @action(detail=False, permission_classes=(IsAuthenticated,))
    def subscriptions(self, request):
        queryset = request.user.subscribing.all()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_subscription_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_subscription_serializer(queryset, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    @action(
        methods=['delete'],
        detail=True,
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, user_id=None):
        author = get_object_or_404(User, pk=user_id)
        subscription = get_object_or_404(
            Subscribe,
            user=request.user,
            author=author
        )

        if request.method == 'DELETE':
            subscription.delete()
            return Response(status=HTTP_204_NO_CONTENT)

        return Response(status=HTTP_400_BAD_REQUEST)


class ShoppingCartViewSet(GenericViewSet):
    NAME = 'ingredients__ingredient__name'
    MEASUREMENT_UNIT = 'ingredients__ingredient__measurement_unit'
    permission_classes = (IsAuthenticated,)
    serializer_class = RecipeShortReadSerializer
    queryset = ShoppingCart.objects.all()
    http_method_names = ('get', 'delete',)

    def generate_shopping_cart_data(self, request):
        recipes = request.user.shopping_cart.recipes.prefetch_related(
            'ingredients')
        return (
            recipes.order_by(self.NAME)
            .values(self.NAME, self.MEASUREMENT_UNIT)
            .annotate(total=Sum('ingredients__amount'))
        )

    def generate_ingredients_content(self, ingredients):
        content = "\r\n".join(
            f"{ingredient[self.NAME]} ({ingredient[self.MEASUREMENT_UNIT]})"
            f"— {ingredient['total']}"
            for ingredient in ingredients
        )
        return content

    @action(detail=False)
    def download_shopping_cart(self, request):
        try:
            ingredients = request.user.generate_shopping_cart_data()
        except ShoppingCart.DoesNotExist:
            return Response(
                {ERRORS_KEY: SHOPPING_CART_DOES_NOT_EXIST},
                status=HTTP_400_BAD_REQUEST
            )
        content = self.generate_ingredients_content(ingredients)
        response = HttpResponse(content,
                                content_type='text/plain;charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename={FILE_NAME}'
        return response

    @action(methods=['post'], detail=True)
    def add_to_shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        shopping_cart, _ = ShoppingCart.objects.get_or_create(
            user=request.user)

        if shopping_cart.recipes.filter(pk=recipe.pk).exists():
            return Response(
                {ERRORS_KEY: SHOPPING_CART_RECIPE_CANNOT_ADD_TWICE},
                status=HTTP_400_BAD_REQUEST,
                )
        shopping_cart.recipes.add(recipe)
        serializer = self.get_serializer(recipe)
        return Response(serializer.data, status=HTTP_201_CREATED)

    @action(methods=['delete'], detail=True)
    def remove_from_shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        shopping_cart, _ = ShoppingCart.objects.get_or_create(
            user=request.user)

        if not shopping_cart.recipes.filter(pk=recipe.pk).exists():
            return Response(
                {ERRORS_KEY: SHOPPING_CART_RECIPE_CANNOT_DELETE},
                status=HTTP_400_BAD_REQUEST,
                )
        shopping_cart.recipes.remove(recipe)
        return Response(status=HTTP_204_NO_CONTENT)
