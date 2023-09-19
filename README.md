## Микросервис бэкэнда Твитов.

Для запуска необходимо изменить переменные окружения `prod.env.template` или `dev.env.template`
на `prod.env` или `dev.env`. Аналогично для `pg.env.template`. В эти файлы уже добавлены тестовые данные. 
Далее просто ввести команду `docker-compose up --build -d`.

### Endpoints:
- /api/docs: GET
- /api/redoc: GET
- /api/users/me: GET 
- /api/users/{user_id}: GET 
- /api/users/{user_id}/follow: POST, DELETE
- /api/tweets: GET, POST
- /api/tweets/{tweet_id}: DELETE
- /api/tweets/{tweet_id}/like: POST, DELETE
- /api/media: POST 

Для проверки взаимодействия с фронтэндом нужно добавить в базу данных пользователя с именем `test`
и токен с api_key `test`. Далее открыть `localhost:1200`