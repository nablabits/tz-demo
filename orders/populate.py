"""Populate a database with dummy data."""
from random import randint, choice
from datetime import date, timedelta
from orders.models import (
    Customer, Order, Item, CashFlowIO, Comment, Expense, Invoice,
    OrderItem, StatusShift, Timetable)

from django.contrib.auth.models import User
from django.utils import timezone

# Courtesy of http://listofrandomnames.com
NAMES = (
    'Golda Cashin',
    'Mayola Yoshida',
    'Angla Bigby',
    'Rashida Apperson',
    'Rolanda Gaetano',
    'Meaghan Candela ',
    'Judy Routon',
    'Taneka Vandorn',
    'Princess Heavrin',
    'Monserrate Wylie', )

# Courtesy of https://lipsum.com

WORDS = """
Vivamus ullamcorper leo pretium ultricies enim quam consectetur augue\
sed gravida magna ante quis tortor Vestibulum dictum metus non ligula\
tempor vitae commodo turpis iaculis Aliquam tincidunt faucibus totor eget\
faucibus Quisque pharetra velit Nunc vitae mollis Mauris fringilla\
eros nulla blandit ultrices justo ultrices sed Nunc ultricies augue vitae\
dolor accumsan molestie Aliquam ultricies ligula malesuada placerat\
odio quam accumsan sem sagittis sapien neque lectus Maecenas non\
turpis scelerisque consectetur eget varius ante Quisque laoreet\
tristique nibh vulputate Nulla tempor nisi vel tincidunt ultrices\
Quisque nec elit lorem Proin sit amet egestas magna vehicula ipsum Donec\
lobortis quam sed nibh aliquet vehicula quam sodales Quisque finibus\
sem quis condimentum Sed sodales eleifend vestibulum\
""".split(' ')


def multiword(w=2):
    """Create a string with some w words."""
    r = randint(0, len(WORDS))
    return ' '.join(WORDS[r: r + w]) if w > 1 else WORDS[w]


def populate():
    """Populate the database with activity simulating last 365 days."""
    # Start by dropping all the previous data
    main_tables = (
        Expense, Customer, Order, Item, StatusShift, Timetable, User)
    for table in main_tables:
        table.objects.all().delete()

    # Create a default user name
    user = User.objects.create_user(username='user', password='pass')

    # random numbers upper bound
    u = len(WORDS) - 1

    # Create some customers
    for name in NAMES:
        Customer.objects.create(
            name=name,
            address=multiword(),
            city=multiword(),
            phone=randint(20000, 2000000),
            email='{}@{}.com'.format(multiword(1), multiword(1)),
            cp=randint(1000, 99000),
            CIF=str(randint(10000, 99000)),
            notes=multiword(5),
            provider=randint(0, 1),
            )

    # Create some items
    for _ in range(10):
        Item.objects.create(
            name=WORDS[randint(0, u)],
            item_type=randint(0, 18),
            foreing=randint(0, 1),
            price=randint(10, 150),
            fabrics=randint(1, 3),
            stocked=300,
            )

    # Create daily activity for the last n days
    days = (date.today() - date(date.today().year, 1, 1)).days
    for n in range(days):
        print('.', end='')
        curr_datetime = timezone.now() - timedelta(days=days - n)
        order = Order.objects.create(
            inbox_date=curr_datetime,
            user=user,
            customer=choice(Customer.objects.filter(provider=False)),
            ref_name=multiword(),
            delivery=curr_datetime + timedelta(days=randint(7, 30)),
            status=randint(1, 6),
            waist=randint(60, 70),
            chest=randint(90, 120),
            hip=randint(90, 120),
            others=multiword(5), )

        for i in range(randint(2, 4)):
            item = OrderItem(
                element=choice(Item.objects.all()),
                reference=order,
                qty=randint(1, 3),
                price=randint(10, 100),
                stock=randint(0, 1),
                )
            item.clean()
            if randint(1, 15) > 1:
                item.crop = timedelta(seconds=1000 * randint(1, 3))
                item.sewing = timedelta(seconds=1000 * randint(1, 3))
                item.iron = timedelta(seconds=1000 * randint(1, 3))
            item.save()

        # Add a comment
        if randint(1, 15) > 1:
            Comment.objects.create(
                creation=curr_datetime,
                user=user,
                reference=order,
                comment=multiword(10))

        # Sell something
        active_orders = Order.live.all()
        sell_it = randint(1, 20) > 1  # p = 19/20
        if sell_it and active_orders.exists():
            order = active_orders.first()
            pay_method = choice(['C', 'T', 'V'])
            CashFlowIO.objects.create(
                creation=curr_datetime,
                order=order,
                amount=order.pending,
                pay_method=pay_method,
            )
            if order.status != '7':
                order.deliver()  # Creates status shift

            # Set status to 9 (invoiced)
            order.status = '9'
            order.save()
            i = Invoice(
                reference=order, issued_on=curr_datetime, amount=order.total,
                pay_method=pay_method)
            i.save(kill=True)

        # Update Item health
        [i.save() for i in Item.objects.all()]

        # Expend some money somewhere
        providers = Customer.objects.filter(provider=True)
        expense = Expense.objects.create(
            creation=curr_datetime,
            issuer=choice(providers),
            invoice_no=choice(WORDS),
            issued_on=curr_datetime,
            concept=multiword(2),
            amount=randint(180, 250),
            pay_method=choice(['C', 'T', 'V']),
            notes=multiword(5),)
        if randint(1, 15) > 1:
            expense.kill()

    # Deliver a couple of orders without selling
    [order.deliver() for order in Order.live.all()[:3]]
