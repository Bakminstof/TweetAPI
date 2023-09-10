from random import choice
from typing import List

from fastapi import status
from httpx import AsyncClient, Response

from controllers import UserController
from models.schemas import User
from tests.common import method_not_allowed, unauthorised

user_controller: UserController = UserController()


class TestMeDetail:
    URL = "/api/users/me"
    _METHOD = "GET"

    async def test_valid(
        self,
        client: AsyncClient,
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

        expected_data = {
            "result": True,
            "user": user_controller.user_to_dict(user),
        }

        assert response.status_code is status.HTTP_200_OK
        assert response_json["result"] is True
        assert response_json == expected_data

    async def test_unauthorised(
        self,
        users: List[User],
        client: AsyncClient,
    ) -> None:
        user = choice(users)

        result = await unauthorised(
            method=self._METHOD,
            url=self.URL.format(user_id=user.id),
            client=client,
        )
        assert result == "Missing `api-key` header"

    async def test_bad_api_key(
        self,
        users: List[User],
        client: AsyncClient,
    ) -> None:
        user = choice(users)
        params = {"api-key": -1}

        result = await unauthorised(
            method=self._METHOD,
            url=self.URL.format(user_id=user.id),
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

        result = await method_not_allowed(
            not_allowed_method="PUT",
            url=self.URL.format(user_id=user.id),
            client=client,
        )
        assert result == "Method Not Allowed"


class TestUserDetail:
    URL = "/api/users/{user_id}"
    _METHOD = "GET"

    async def test_valid(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        user = choice(users)
        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(user_id=user.id),
        )
        response_json = response.json()

        expected_data = {
            "result": True,
            "user": user_controller.user_to_dict(user),
        }

        assert response.status_code is status.HTTP_200_OK
        assert response_json["result"] is True
        assert response_json == expected_data

    async def test_invalid_user_id(self, client: AsyncClient) -> None:
        user_id = "?*"

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(user_id=user_id),
        )
        response_json = response.json()

        assert response.status_code is status.HTTP_404_NOT_FOUND
        assert response_json["result"] is False

    async def test_not_allowed_method(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        user = choice(users)

        result = await method_not_allowed(
            not_allowed_method="PUT",
            url=self.URL.format(user_id=user.id),
            client=client,
        )
        assert result == "Method Not Allowed"


class TestFollowUser:
    URL = "/api/users/{user_id}/follow"
    _METHOD = "POST"

    async def test_valid(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        current_user = users[0]
        target_user = users[1]

        params = {"api-key": current_user.token.api_key}

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(user_id=target_user.id),
            params=params,
        )
        response_json = response.json()

        assert response.status_code is status.HTTP_201_CREATED
        assert response_json["result"] is True

    async def test_valid_complex(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        # Follow
        current_user = users[0]
        target_user = users[1]

        params = {"api-key": current_user.token.api_key}
        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(user_id=target_user.id),
            params=params,
        )
        response_json = response.json()

        assert response.status_code is status.HTTP_201_CREATED
        assert response_json["result"] is True

        # Check target user followers
        user_url = f"/api/users/{target_user.id}"
        user_response: Response = await client.request(
            method="GET",
            url=user_url,
        )

        user_response_json = user_response.json()

        expected_followers = [{"id": current_user.id, "name": current_user.name}]

        assert user_response.status_code == status.HTTP_200_OK
        assert user_response_json["result"] is True
        assert user_response_json["user"]["followers"] == expected_followers

        # Check my following
        me_url = "/api/users/me"
        me_response: Response = await client.request(
            method="GET",
            url=me_url,
            params=params,
        )

        me_response_json = me_response.json()

        expected_following = [{"id": target_user.id, "name": target_user.name}]

        assert user_response.status_code == status.HTTP_200_OK
        assert me_response_json["result"] is True
        assert me_response_json["user"]["following"] == expected_following

    async def test_invalid_user_id(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        user = choice(users)
        user_id = "?"

        params = {"api-key": user.token.api_key}

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(user_id=user_id),
            params=params,
        )
        response_json = response.json()

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response_json["result"] is False

    async def test_follow_myself(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        user = choice(users)
        params = {"api-key": user.token.api_key}

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(user_id=user.id),
            params=params,
        )
        response_json = response.json()

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response_json["error_message"] == f"It's your user ID `{user.id}`"
        assert response_json["result"] is False

    async def test_double_follow(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        # Follow
        current_user = users[0]
        target_user = users[1]

        params = {"api-key": current_user.token.api_key}

        response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(user_id=target_user.id),
            params=params,
        )
        response_json = response.json()

        assert response.status_code is status.HTTP_201_CREATED
        assert response_json["result"] is True

        # Another one follow
        user_response: Response = await client.request(
            method="POST",
            url=self.URL.format(user_id=target_user.id),
            params=params,
        )

        user_response_json = user_response.json()

        assert user_response.status_code == status.HTTP_400_BAD_REQUEST
        assert user_response_json["result"] is False
        assert (
            user_response_json["error_message"]
            == f"You already followed user with user_id `{target_user.id}`"
        )

    async def test_unauthorised(
        self,
        users: List[User],
        client: AsyncClient,
    ) -> None:
        user = choice(users)

        result = await unauthorised(
            method=self._METHOD,
            url=self.URL.format(user_id=user.id),
            client=client,
        )
        assert result == "Missing `api-key` header"

    async def test_bad_api_key(
        self,
        users: List[User],
        client: AsyncClient,
    ) -> None:
        user = choice(users)
        params = {"api-key": -1}

        result = await unauthorised(
            method=self._METHOD,
            url=self.URL.format(user_id=user.id),
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

        result = await method_not_allowed(
            not_allowed_method="PUT",
            url=self.URL.format(user_id=user.id),
            client=client,
        )
        assert result == "Method Not Allowed"


class TestUnFollowUser:
    URL = "/api/users/{user_id}/follow"
    _METHOD = "DELETE"

    async def test_valid(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        # Follow
        current_user = users[0]
        target_user = users[1]

        params = {"api-key": current_user.token.api_key}

        response: Response = await client.request(
            method="POST",
            url=self.URL.format(user_id=target_user.id),
            params=params,
        )
        response_json = response.json()

        assert response.status_code is status.HTTP_201_CREATED
        assert response_json["result"] is True

        # Unfollow
        delete_response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(user_id=target_user.id),
            params=params,
        )
        delete_response_json = delete_response.json()

        assert delete_response.status_code is status.HTTP_200_OK
        assert delete_response_json["result"] is True

    async def test_valid_complex(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        # Follow
        current_user = users[0]
        target_user = users[1]

        params = {"api-key": current_user.token.api_key}
        response: Response = await client.request(
            method="POST",
            url=self.URL.format(user_id=target_user.id),
            params=params,
        )
        response_json = response.json()

        assert response.status_code is status.HTTP_201_CREATED
        assert response_json["result"] is True

        # Unfollow
        delete_response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(user_id=target_user.id),
            params=params,
        )
        delete_response_json = delete_response.json()

        assert delete_response.status_code is status.HTTP_200_OK
        assert delete_response_json["result"] is True

        # Check target user followers
        url = f"/api/users/{target_user.id}"
        user_response: Response = await client.request(method="GET", url=url)

        user_response_json = user_response.json()

        expected_followers = []

        assert user_response.status_code == status.HTTP_200_OK
        assert user_response_json["result"] is True
        assert user_response_json["user"]["followers"] == expected_followers

        # Check following myself
        me_url = "/api/users/me"
        me_response: Response = await client.request(
            method="GET",
            url=me_url,
            params=params,
        )

        me_response_json = me_response.json()

        expected_following = []

        assert user_response.status_code == status.HTTP_200_OK
        assert me_response_json["result"] is True
        assert me_response_json["user"]["following"] == expected_following

    async def test_invalid_user_id(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        user = choice(users)
        user_id = "?"

        params = {"api-key": user.token.api_key}

        response: Response = await client.request(
            self._METHOD,
            self.URL.format(user_id=user_id),
            params=params,
        )
        response_json = response.json()

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response_json["result"] is False

    async def test_unfollow_myself(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        user = choice(users)
        params = {"api-key": user.token.api_key}

        response: Response = await client.request(
            self._METHOD,
            self.URL.format(user_id=user.id),
            params=params,
        )
        response_json = response.json()

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response_json["error_message"] == f"It's your user ID `{user.id}`"
        assert response_json["result"] is False

    async def test_double_unfollow(
        self,
        client: AsyncClient,
        users: List[User],
    ) -> None:
        current_user = users[0]
        target_user = users[1]

        params = {"api-key": current_user.token.api_key}

        # Follow
        response: Response = await client.request(
            method="POST",
            url=self.URL.format(user_id=target_user.id),
            params=params,
        )
        response_json = response.json()

        assert response.status_code is status.HTTP_201_CREATED
        assert response_json["result"] is True

        # Unfollow
        delete_response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(user_id=target_user.id),
            params=params,
        )
        delete_response_json = response.json()

        assert delete_response.status_code is status.HTTP_200_OK
        assert delete_response_json["result"] is True

        # Another one unfollow
        another_delete_response: Response = await client.request(
            method=self._METHOD,
            url=self.URL.format(user_id=target_user.id),
            params=params,
        )

        another_delete_response_json = another_delete_response.json()

        assert another_delete_response.status_code == status.HTTP_400_BAD_REQUEST
        assert another_delete_response_json["result"] is False
        assert (
            another_delete_response_json["error_message"]
            == f"You are not followed user with user_id `{target_user.id}`"
        )

    async def test_unauthorised(
        self,
        users: List[User],
        client: AsyncClient,
    ) -> None:
        user = choice(users)

        result = await unauthorised(
            method=self._METHOD,
            url=self.URL.format(user_id=user.id),
            client=client,
        )
        assert result == "Missing `api-key` header"

    async def test_bad_api_key(
        self,
        users: List[User],
        client: AsyncClient,
    ) -> None:
        user = choice(users)
        params = {"api-key": -1}

        result = await unauthorised(
            method=self._METHOD,
            url=self.URL.format(user_id=user.id),
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

        result = await method_not_allowed(
            not_allowed_method="PUT",
            url=self.URL.format(user_id=user.id),
            client=client,
        )
        assert result == "Method Not Allowed"
