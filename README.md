Тестовый скрипт для расчета скоринговых данных.

Требования: Python 3.8 и выше.

Установка:

> git clone https://gitlab.com/otus7160838/scoringapi.git
> cd scoringapi
> python install -r requirements.txt

Тестирование:
> python test.py 

Запуск приложения:

> python api.py

Для расчета данных, необходимо отправить json запрос, например:

> curl -X POST -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "h&f", "method": "online_score\", "token": "", "arguments": {}}' http://127.0.0.1:8080/method

Поддерживаются два метода:

* online_score
  - first_name
  - second_name
  - phone
  - email
  - birthday
  - gender

* clients_interests
  - client_ids
  - date