# TZ app

This app is one of my long-term projects starting back in 2018. The purpose is to manage a local business mainly focussed on tailor made basque clothes. 
These are some of the main features:
* Live progress of the business health: incomes, expenses, target & tracked times on production.
* Kanban view of active orders with status tracker across stages
* Prepaids management.
* Production queue management.
* Stock tracking. 
* Bank balance for those in-cash payments.
* Time tracker for employees

### Live demo
Check out a live demo hosted in heroku (takes a couple of minutes to wake up, be patitent): https://tzmockup.herokuapp.com/  

Alternatively you can install in a local environment, see below.

---

Sadly the language of this app is full in Spanish since it's the language their users speak.   


## Local installation


+ Clone the repo  
`$ git clone git@github.com:nablabits/tz-demo.git`

* Create a postgres database. For this example, I'll use *tz_demo*
for the database name and *tz_admin* for the username:  
`$ createdb -h localhost -p 5432 -U tz_admin tz_demo`

  This command prompts for *tz_admin* password
* Clone `.env_template` and rename as `.env`. Fill this file with the data,
  just, SECRET_KEY, DB_NAME, DB_USER & DB_PASSWORD  

* Create a virtual environment and install necessary packages  
  ```
  $ python3 -m venv venv`  
  $ source venv/bin/activate
  $ pip install --upgrade pip
  $ pip install -r requirements.txt
  ```

* If everything was ok apply migrations & run the server
  ```
  $ python manage.py migrate
  $ python manage.py runserver
  ```
* Populate the db (before there was a button in the login but it was deprecated)
  ```
  $ python manage.py shell
  >>> from orders.populate import populate
  >>> populate()
  ```

* Finally navigate to https://127.0.0.1:8000 and login with *user* & *pass*
