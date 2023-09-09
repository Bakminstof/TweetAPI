from random import choice
from typing import List

from fastapi import status
from httpx import AsyncClient, Response

from models.schemas import Tweet, User
from tests.common import bad_request, method_not_allowed, unauthorised


class TestGetTweets:
    URL = "/api/tweets"
    _METHOD = "GET"

    async def test_valid(
        self,
        client: AsyncClient,
        tweets: List[Tweet],
        users: List[User],
    ) -> None:
        user = choice(users)
        params = {"api-key": user.token.api_key}

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL,
            params=params,
        )
        response_json = response.json()

        expected_data = [
            {
                "id": tweet.id,
                "content": tweet.content,
                "attachments": [att.id for att in tweet.attachments],
                "author": {
                    "id": tweet.author.id,
                    "name": tweet.author.name,
                },
                "likes": [
                    {
                        "user_id": like.liker.id,
                        "name": like.liker.name,
                    }
                    for like in tweet.likers
                ],
            }
            for tweet in tweets
        ]

        assert response.status_code == status.HTTP_200_OK
        assert response_json["result"] is True

        for tweet in response_json["tweets"]:
            assert tweet in expected_data

    async def test_unauthorised(
        self,
        client: AsyncClient,
    ) -> None:
        result = await unauthorised(
            method=self._METHOD,
            url=self.URL,
            client=client,
        )
        assert result == "Query params missing `api-key`"

    async def test_bad_api_key(
        self,
        client: AsyncClient,
    ) -> None:
        params = {"api-key": -1}
        result = await unauthorised(
            method=self._METHOD,
            url=self.URL,
            client=client,
            params=params,
        )
        assert result == "Invalid api-key"

    async def test_not_allowed_method(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        user = choice(users)
        params = {"api-key": user.token.api_key}

        result = await method_not_allowed(
            not_allowed_method="PUT",
            url=self.URL,
            client=client,
            params=params,
        )
        assert result == "Method Not Allowed"


class TestCreateTweet:
    URL = "/api/tweets"
    _METHOD = "POST"

    async def test_valid(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        user = choice(users)
        params = {"api-key": user.token.api_key}

        data = {"tweet_data": "TestTweetData", "tweet_media_ids": []}

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL,
            params=params,
            json=data,
        )
        response_json = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert response_json["result"] is True

    async def test_missing_required_field(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        user = choice(users)
        params = {"api-key": user.token.api_key}

        data = {"tweet_media_ids": []}

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL,
            params=params,
            json=data,
        )
        response_json = response.json()

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response_json["result"] is False

    async def test_unauthorised(
        self,
        client: AsyncClient,
    ) -> None:
        result = await unauthorised(
            method=self._METHOD,
            url=self.URL,
            client=client,
        )
        assert result == "Query params missing `api-key`"

    async def test_bad_api_key(
        self,
        client: AsyncClient,
    ) -> None:
        params = {"api-key": -1}
        result = await unauthorised(
            method=self._METHOD,
            url=self.URL,
            client=client,
            params=params,
        )
        assert result == "Invalid api-key"

    async def test_not_allowed_method(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        user = choice(users)
        params = {"api-key": user.token.api_key}

        result = await method_not_allowed(
            not_allowed_method="DELETE",
            url=self.URL,
            client=client,
            params=params,
        )
        assert result == "Method Not Allowed"


class TestDeleteTweet:
    URL = "/api/tweets/{tweet_id}"
    _METHOD = "DELETE"

    async def test_valid(
        self,
        client: AsyncClient,
        users: List[User],
        tweets: List[Tweet],
    ) -> None:
        user = choice(users)
        params = {"api-key": user.token.api_key}

        tweet_id: int = 0

        for tweet in tweets:
            if tweet.author_id == user.id:
                tweet_id = tweet.id
                break

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            params=params,
        )

        response_json = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert response_json["result"] is True

    async def test_wrong_owner(
        self,
        client: AsyncClient,
        users: List[User],
        tweets: List[Tweet],
    ) -> None:
        user = choice(users)
        params = {"api-key": user.token.api_key}

        tweet_id: int = 0

        for tweet in tweets:
            if tweet.author_id != user.id:
                tweet_id = tweet.id
                break

        result = await bad_request(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            client=client,
            status_code=status.HTTP_403_FORBIDDEN,
            params=params,
        )

        assert result == "Wrong owner"

    async def test_invalid_tweet_id(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        user = choice(users)
        params = {"api-key": user.token.api_key}

        tweet_id: int = -1

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            params=params,
        )

        response_json = response.json()

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response_json["result"] is False

    async def test_unauthorised(
        self,
        client: AsyncClient,
        tweets: List[Tweet],
    ) -> None:
        tweet_id = choice(tweets).id

        result = await unauthorised(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            client=client,
        )
        assert result == "Query params missing `api-key`"

    async def test_bad_api_key(
        self,
        client: AsyncClient,
        tweets: List[Tweet],
    ) -> None:
        params = {"api-key": 0}

        tweet_id = choice(tweets).id

        result = await unauthorised(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            client=client,
            params=params,
        )
        assert result == "Invalid api-key"

    async def test_not_allowed_method(
        self,
        client: AsyncClient,
        users: List[User],
        tweets: List[Tweet],
    ) -> None:
        user = choice(users)
        tweet_id = choice(tweets).id

        params = {"api-key": user.token.api_key}

        result = await method_not_allowed(
            not_allowed_method="PUT",
            url=self.URL.format(tweet_id=tweet_id),
            client=client,
            params=params,
        )
        assert result == "Method Not Allowed"


class TestLikeTweet:
    URL = "/api/tweets/{tweet_id}/likes"
    _METHOD = "POST"

    async def test_valid(
        self,
        client: AsyncClient,
        users: List[User],
        tweets: List[Tweet],
    ) -> None:
        user = choice(users)
        params = {"api-key": user.token.api_key}

        tweet_id = choice(tweets).id

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            params=params,
        )

        response_json = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert response_json["result"] is True

    async def test_valid_complex(
        self,
        client: AsyncClient,
        users: List[User],
        tweets: List[Tweet],
    ) -> None:
        # Like tweet
        user = choice(users)
        params = {"api-key": user.token.api_key}

        tweet_id = choice(tweets).id

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            params=params,
        )

        response_json = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert response_json["result"] is True

        # Check liked tweet
        url = "/api/tweets"

        tweet_response: Response = await client.request(
            method="GET",
            url=url,
            params=params,
        )

        tweet_response_json = tweet_response.json()

        assert tweet_response.status_code == status.HTTP_200_OK
        assert tweet_response_json["result"] is True

        for tweet in tweet_response_json["tweets"]:
            if tweet["id"] == tweet_id:
                assert tweet["likes"][0]["user_id"] == user.id
                assert tweet["likes"][0]["name"] == user.name

    async def test_invalid_tweet_id(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        user = choice(users)
        params = {"api-key": user.token.api_key}

        tweet_id: int = -1

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            params=params,
        )

        response_json = response.json()

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response_json["result"] is False

    async def test_double_like(
        self,
        client: AsyncClient,
        users: List[User],
        tweets: List[Tweet],
    ) -> None:
        user = choice(users)
        params = {"api-key": user.token.api_key}

        tweet_id = choice(tweets).id

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            params=params,
        )

        response_json = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert response_json["result"] is True

        # Another like
        another_response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            params=params,
        )

        another_response_json = another_response.json()

        assert another_response.status_code == status.HTTP_400_BAD_REQUEST
        assert another_response_json["result"] is False
        assert another_response_json["error_message"] == "Tweet already liked"

    async def test_unauthorised(
        self,
        client: AsyncClient,
        tweets: List[Tweet],
    ) -> None:
        tweet_id = choice(tweets).id

        result = await unauthorised(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            client=client,
        )
        assert result == "Query params missing `api-key`"

    async def test_bad_api_key(
        self,
        client: AsyncClient,
        tweets: List[Tweet],
    ) -> None:
        params = {"api-key": 0}

        tweet_id = choice(tweets).id

        result = await unauthorised(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            client=client,
            params=params,
        )
        assert result == "Invalid api-key"

    async def test_not_allowed_method(
        self,
        client: AsyncClient,
        users: List[User],
        tweets: List[Tweet],
    ) -> None:
        user = choice(users)
        tweet_id = choice(tweets).id

        params = {"api-key": user.token.api_key}

        result = await method_not_allowed(
            not_allowed_method="PUT",
            url=self.URL.format(tweet_id=tweet_id),
            client=client,
            params=params,
        )
        assert result == "Method Not Allowed"


class TestDislikeTweet:
    URL = "/api/tweets/{tweet_id}/likes"
    _METHOD = "DELETE"

    async def test_valid(
        self,
        client: AsyncClient,
        users: List[User],
        tweets: List[Tweet],
    ) -> None:
        # Like tweet
        user = choice(users)
        params = {"api-key": user.token.api_key}

        tweet_id = choice(tweets).id

        response: Response = await client.request(
            method="POST",
            url=self.URL.format(tweet_id=tweet_id),
            params=params,
        )

        response_json = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert response_json["result"] is True

        # Dislike tweet
        dislike_response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            params=params,
        )

        dislike_response_json = response.json()

        assert dislike_response.status_code == status.HTTP_200_OK
        assert dislike_response_json["result"] is True

    async def test_valid_complex(
        self,
        client: AsyncClient,
        users: List[User],
        tweets: List[Tweet],
    ) -> None:
        # Like tweet
        user = choice(users)
        params = {"api-key": user.token.api_key}

        tweet_id = choice(tweets).id

        response: Response = await client.request(
            method="POST",
            url=self.URL.format(tweet_id=tweet_id),
            params=params,
        )

        response_json = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert response_json["result"] is True

        # Dislike tweet
        dislike_response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            params=params,
        )

        dislike_response_json = response.json()

        assert dislike_response.status_code == status.HTTP_200_OK
        assert dislike_response_json["result"] is True

        # Check liked tweet
        url = "/api/tweets"

        tweet_response: Response = await client.request(
            method="GET",
            url=url,
            params=params,
        )

        tweet_response_json = tweet_response.json()

        assert tweet_response.status_code == status.HTTP_200_OK
        assert tweet_response_json["result"] is True

        for tweet in tweet_response_json["tweets"]:
            if tweet["id"] == tweet_id:
                assert tweet["likes"] == []

    async def test_invalid_tweet_id(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        user = choice(users)
        params = {"api-key": user.token.api_key}

        tweet_id: int = -1

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            params=params,
        )

        response_json = response.json()

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response_json["result"] is False

    async def test_double_dislike(
        self,
        client: AsyncClient,
        users: List[User],
        tweets: List[Tweet],
    ) -> None:
        # Like tweet
        user = choice(users)
        params = {"api-key": user.token.api_key}

        tweet_id = choice(tweets).id

        response: Response = await client.request(
            method="POST",
            url=self.URL.format(tweet_id=tweet_id),
            params=params,
        )

        response_json = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert response_json["result"] is True

        # Dislike tweet
        dislike_response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            params=params,
        )

        dislike_response_json = response.json()

        assert dislike_response.status_code == status.HTTP_200_OK
        assert dislike_response_json["result"] is True

        # Another dislike tweet
        another_dislike_response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            params=params,
        )

        another_dislike_response_json = another_dislike_response.json()

        assert another_dislike_response.status_code == status.HTTP_400_BAD_REQUEST
        assert another_dislike_response_json["result"] is False
        assert another_dislike_response_json["error_message"] == "This tweet not liked"

    async def test_unauthorised(
        self,
        client: AsyncClient,
        tweets: List[Tweet],
    ) -> None:
        tweet_id = choice(tweets).id

        result = await unauthorised(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            client=client,
        )
        assert result == "Query params missing `api-key`"

    async def test_bad_api_key(
        self,
        client: AsyncClient,
        tweets: List[Tweet],
    ) -> None:
        params = {"api-key": 0}

        tweet_id = choice(tweets).id

        result = await unauthorised(
            method=self._METHOD,
            url=self.URL.format(tweet_id=tweet_id),
            client=client,
            params=params,
        )
        assert result == "Invalid api-key"

    async def test_not_allowed_method(
        self,
        client: AsyncClient,
        users: List[User],
        tweets: List[Tweet],
    ) -> None:
        user = choice(users)
        tweet_id = choice(tweets).id

        params = {"api-key": user.token.api_key}

        result = await method_not_allowed(
            not_allowed_method="PUT",
            url=self.URL.format(tweet_id=tweet_id),
            client=client,
            params=params,
        )
        assert result == "Method Not Allowed"
