"""These are the common settings for the app orders."""

# The name for the app
APP_NAME = "Trapu Zarrak app"
VERSION = 'v71'

# Available types of clothes
ITEM_TYPE = (
    ('0', 'No definido'),
    ('1', 'Falda'),
    ('2', 'Pantalón'),
    ('3', 'Camisa'),
    ('4', 'Pañuelo'),
    ('5', 'Delantal'),
    ('6', 'Corpiño'),
    ('7', 'Chaleco'),
    ('8', 'Gerriko'),
    ('9', 'Bata'),
    ('10', 'Pololo'),
    ('11', 'Azpikogona'),
    ('12', 'Traje de niña'),
    ('13', 'Toquilla'),
    ('14', 'Bluson'),
    ('15', 'Jakea'),
    ('16', 'Medias'),
    ('17', 'Bordado'),
    ('18', 'Txapela'),
    ('19', 'Varios')
)

ITEM_CLASSES = (
    ('S', 'Standard'),
    ('M', 'Medium'),
    ('P', 'Premium')
)

PAYMENT_METHODS = (
    ('C', 'Metálico'),
    ('V', 'Tarjeta'),
    ('T', 'Transferencia')
)

GOAL = 240

WEEK_COLORS = dict(this='#28a745', next='#1dddff', in_two='#74f5de')

RELAX_ICONS = ('curling', 'shuttlecock', 'table-tennis', 'coffee-togo',
               'umbrella-beach', 'clipboard-check', )

# Contact settings
CONTACT_EMAIL = 'denda@trapuzarrak.eus'
CONTACT_PHONE = '+34688725891'
