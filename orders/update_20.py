"""Auto updates in the db for 2020 improvements."""

from django.db.models import Q

from .models import (
    Customer, Invoice, CashFlowIO, Order, StatusShift, Item, ExpenseCategory,
    Expense, )
from datetime import date, timedelta

# Update items health
print('Updating item health')
[i.save() for i in Item.objects.all()]

# Update the group info
print('Updating group info')
group = Customer.objects.filter(name__icontains='talde')
for g in group:
    g.group = True
    g.save()

# Update status
print('Updating status for orders')
invoices = Invoice.objects.all()
for i in invoices:
    i.reference.status = '9'
    i.reference.save()

for o in Order.objects.filter(delivery__lt=date(2019, 1, 1)):
    o.status = '9'
    o.save()

# Update the cashflow movements
print('Updating cash flow movements.')
[cf.delete() for cf in CashFlowIO.objects.all()]  # Start out clean
CashFlowIO().update_old()

"""
Update status shifts for orders

Saving orders created statuses for every order, so delete them to start out
clean.
"""
print('Cleaning up the StatusShift database to start out clean...')
[ss.delete(clear_all=True) for ss in StatusShift.objects.all()]

print('Adding status shift entries to delivered/invoiced orders')
for o in Order.objects.filter(status__in=['7', '9']):
    # Inbox status shift
    out = (o.delivery - o.inbox_date.date()) + o.inbox_date
    ss = StatusShift(
        order=o, date_in=o.inbox_date, date_out=out, status='1',
        notes='Entry automatically created with update 2020')
    ss.save(force_save=True)

    # Invoice/deliver status shift
    ss = StatusShift(
        order=o, date_in=out, date_out=out + timedelta(seconds=1),
        status=o.status, notes='Entry automatically created with update 2020')
    ss.save(force_save=True)

# now the rest of the entries that remain at status 1
print('Adding status shift entries to leftover...')
for o in Order.objects.exclude(status__in=['7', '9']):
        ss = StatusShift(order=o, date_in=o.inbox_date, status='1',
                         notes='Entry automatically created with update 2020')
        ss.save(force_save=True)

# Create some expense categories
print('Creating some expense categories')
[cat.delete() for cat in ExpenseCategory.objects.exclude(name='default')]
cat = (
    'People', 'rent', 'taxes', 'resources', 'supply_raw', 'supply_resell', )

[ExpenseCategory.objects.create(name=c) for c in cat]

print('Updating expenses to their category.')
q1 = Expense.objects.filter(
    Q(issuer__name__istartswith='SS') |
    Q(issuer__name__istartswith='TXARO') |
    Q(issuer__name__istartswith='IRATXE'), )

q2 = Expense.objects.filter(issuer__name__istartswith='MARIA BEGOÑA')
q3 = Expense.objects.filter(issuer__name__istartswith='BFA')
q4 = Expense.objects.filter(
    Q(issuer__name__istartswith='EUSKALTEL') |
    Q(issuer__name__istartswith='10DECENCE') |
    Q(issuer__name__istartswith='AXA') |
    Q(issuer__name__istartswith='CONSORCIO') |
    Q(issuer__name__istartswith='IBERDROLA'), )
q5 = Expense.objects.filter(
    Q(issuer__name__istartswith='DIVISION') |
    Q(issuer__name__istartswith='ENCAJERA') |
    Q(issuer__name__istartswith='GUTTERMAN') |
    Q(issuer__name__istartswith='INDUSTRIES') |
    Q(issuer__name__istartswith='JOSE') |
    Q(issuer__name__istartswith='JUAN') |
    Q(issuer__name__istartswith='MARUTX') |
    Q(issuer__name__istartswith='MAYORISTA') |
    Q(issuer__name__istartswith='RAFAEL') |
    Q(issuer__name__istartswith='SAFISA') |
    Q(issuer__name__istartswith='SANPERE') |
    Q(issuer__name__istartswith='STIL') |
    Q(issuer__name__istartswith='TEJIDOS') |
    Q(issuer__name__istartswith='TEXTIL'), )
q6 = Expense.objects.filter(
    Q(issuer__name__istartswith='AITOR') |
    Q(issuer__name__istartswith='LARDAGI') |
    Q(issuer__name__istartswith='LLORIA') |
    Q(issuer__name__istartswith='MARIA KRUG') |
    Q(issuer__name__istartswith='ZUARTEX'), )

for n, query in enumerate((q1, q2, q3, q4, q5, q6, )):
    for e in query:
        ec = ExpenseCategory.objects.get(name=cat[n])
        e.category = ec
        e.save()
