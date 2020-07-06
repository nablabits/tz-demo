# Local installation
---

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

* Finally navigate to https://127.0.0.1:8000 and, once populated the db, login with *user* & *pass*
