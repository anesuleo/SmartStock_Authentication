from pydantic import BaseModel, EmailStr, constr, conint, Field

class User(BaseModel):
    user_id: int
    type:int
    name: constr(min_length=2, max_length=50)
    email: EmailStr
