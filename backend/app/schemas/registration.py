from pydantic import BaseModel


class RegistrationRequest(BaseModel):
    academy_name: str
    academy_phone: str
    administrator_name: str
    administrator_email: str
    administrator_password: str
