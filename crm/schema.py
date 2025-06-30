import re
import graphene

from django.db import transaction
from crm.models import Customer, Product, Order
from crm.types import CustomerType, ProductType, OrderType

class CreateCustomer(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String()

    customer = graphene.Field(CustomerType)
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, name, email, phone=None):
        if Customer.objects.filter(email=email).exists():
            return CreateCustomer(success=False, message="Email already exists.")
        
        # Validate phone format
        if phone and not re.match(r"^\+?\d{1,15}$", phone):
            return CreateCustomer(success=False, message="Invalid phone format.")
        
        customer = Customer.objects.create(name=name, email=email, phone=phone)
        return CreateCustomer(customer=customer, success=True, message="Customer created successfully.")

class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        customers = graphene.List(graphene.JSONString)

    success_customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    def mutate(self, info, customers):
        success_customers = []
        errors = []
        with transaction.atomic():
            for customer_data in customers:
                try:
                    # Validate email uniqueness
                    if Customer.objects.filter(email=customer_data.get("email")).exists():
                        raise Exception(f"Email {customer_data.get('email')} already exists.")
                    
                    # Validate phone format
                    phone = customer_data.get("phone")
                    if phone and not re.match(r"^\+?\d{1,15}$", phone):
                        raise Exception(f"Invalid phone format for {customer_data.get('name')}.")
                    
                    customer = Customer.objects.create(**customer_data)
                    success_customers.append(customer)
                except Exception as e:
                    errors.append(str(e))
        return BulkCreateCustomers(success_customers=success_customers, errors=errors)

class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.Int(required=True)
        product_ids = graphene.List(graphene.Int, required=True)
        order_date = graphene.DateTime()

    order = graphene.Field(OrderType)

    def mutate(self, info, customer_id, product_ids, order_date=None):
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            raise Exception("Invalid customer ID.")

        products = Product.objects.filter(id__in=product_ids)
        if not products.exists():
            raise Exception("Invalid product IDs.")
        
        # Ensure at least one product is selected
        if not product_ids:
            raise Exception("At least one product must be selected.")

        total_amount = sum(product.price for product in products)
        order = Order.objects.create(customer=customer, total_amount=total_amount, order_date=order_date)
        order.products.set(products)
        return CreateOrder(order=order)