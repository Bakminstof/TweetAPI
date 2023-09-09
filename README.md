## Микросервис бэкэнда Твитов.

Для запуска необходимо ввести команду: `docker-compose up --build -d` 


### Endpoints:
- /api/users/me: GET 
- /api/users/{user_id}: GET 
- /api/users/{user_id}/follow: POST, DELETE
- /api/tweets: GET, POST
- /api/tweets/{tweet_id}: DELETE
- /api/tweets/{tweet_id}/like: POST, DELETE
- /api/media: POST 

https://gitlab.skillbox.ru/andrei_abramov_3/python_advanced_diploma.git