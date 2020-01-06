"""Create some combos automatically as items.

            ptz     ftz     ctz     dtz     cts     dts
Tz          x       x       x       x
Jata        x       x       x                       x
Sollube     x       x               x       x
Pagasarri   x       x       x               x       x

This approach is sightly different from the initial combos approach, since we
are about to create several *Traje de niña* items and when crunching the
numbers at the end of the year, we'll estimate the weight of each element
inside the item.
"""

from orders.models import Item

# auto created items in previous runs
[i.delete() for i in Item.objects.filter(notes__startswith='#auto;')]

rel_data = {
    'Jata': '#auto; delantal toston',
    'Sollube': '#auto; camisa toston',
    'Pagasarri': '#auto; delantal y camisa toston',
}

# Iterate over sizes
for s in (0, 2, 4, 6, 8, 10, 12):
    for k, v in rel_data.items():
        i = Item.objects.create(
            name=k, item_type='12', size=s, notes=v, fabrics=0, stocked=50, )
