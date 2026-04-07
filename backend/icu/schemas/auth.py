from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RequestOtpBody(BaseModel):
    email: EmailStr


class RequestOtpResponse(BaseModel):
    status: str = "sent"
    dev_code: str | None = Field(
        default=None,
        description="Only in development when ICU_DEV_LOG_OTP=true",
    )


class VerifyOtpBody(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    device_id: str | None = Field(default=None, max_length=64)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uin: int
    email: str
    display_name: str | None


class PresenceResponse(BaseModel):
    uin: int
    online: bool


class VerifyOtpResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic


class RefreshBody(BaseModel):
    refresh_token: str
    device_id: str | None = Field(default=None, max_length=64)


class LogoutBody(BaseModel):
    refresh_token: str
