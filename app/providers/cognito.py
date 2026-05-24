from dataclasses import dataclass

import boto3

from app.core.config import settings


@dataclass
class CognitoTokenSet:
    access_token: str
    id_token: str
    refresh_token: str | None
    expires_in: int
    token_type: str = "Bearer"


class CognitoProvider:
    def __init__(self) -> None:
        self.client = boto3.client("cognito-idp", region_name=settings.aws_region)

    def sign_up(self, email: str, password: str, name: str | None = None) -> dict:
        attributes = [{"Name": "email", "Value": email}]
        if name:
            attributes.append({"Name": "name", "Value": name})
        return self.client.sign_up(
            ClientId=settings.cognito_client_id,
            Username=email,
            Password=password,
            UserAttributes=attributes,
        )

    def confirm_sign_up(self, email: str, confirmation_code: str) -> None:
        self.client.confirm_sign_up(
            ClientId=settings.cognito_client_id,
            Username=email,
            ConfirmationCode=confirmation_code,
        )

    def login(self, email: str, password: str) -> CognitoTokenSet:
        response = self.client.initiate_auth(
            ClientId=settings.cognito_client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
        )
        auth = response["AuthenticationResult"]
        return CognitoTokenSet(
            access_token=auth["AccessToken"],
            id_token=auth["IdToken"],
            refresh_token=auth.get("RefreshToken"),
            expires_in=auth["ExpiresIn"],
            token_type=auth.get("TokenType", "Bearer"),
        )

    def refresh(self, refresh_token: str) -> CognitoTokenSet:
        response = self.client.initiate_auth(
            ClientId=settings.cognito_client_id,
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={"REFRESH_TOKEN": refresh_token},
        )
        auth = response["AuthenticationResult"]
        return CognitoTokenSet(
            access_token=auth["AccessToken"],
            id_token=auth["IdToken"],
            refresh_token=None,
            expires_in=auth["ExpiresIn"],
            token_type=auth.get("TokenType", "Bearer"),
        )

    def logout(self, access_token: str) -> None:
        self.client.global_sign_out(AccessToken=access_token)

