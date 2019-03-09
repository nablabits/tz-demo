"""Define serializers for the models to create an API view for jupyter."""
from rest_framework import serializers
from . import models


class CustomerSerializer(serializers.ModelSerializer):
    """Define the serializer for the customer model."""

    class Meta:
        model = models.Customer
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    """Define the serializer for the order model."""

    class Meta:
        model = models.Order
        fields = '__all__'


class ItemSerializer(serializers.ModelSerializer):
    """Define the serializer for the item model."""

    class Meta:
        model = models.Item
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    """Define the serializer for the order item model."""

    class Meta:
        model = models.OrderItem
        fields = '__all__'


class InvoiceSerializer(serializers.ModelSerializer):
    """Define the serializer for the item model."""

    class Meta:
        model = models.Invoice
        fields = '__all__'


class ExpenseSerializer(serializers.ModelSerializer):
    """Define the serializer for the order item model."""

    class Meta:
        model = models.Expense
        fields = '__all__'


class BankMovementSerializer(serializers.ModelSerializer):
    """Define the serializer for the order item model."""

    class Meta:
        model = models.BankMovement
        fields = '__all__'
