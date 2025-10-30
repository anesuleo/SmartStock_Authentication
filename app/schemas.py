from pydantic import BaseModel, EmailStr, constr, conint, Field

class User(BaseModel):
    user_id: int
    name: constr(min_length=2, max_length=50)
    student_id: str = Field(pattern=r"^S\d{7}$") ##Set pattern to start with S and allow exactly 7 digits after
    email: EmailStr
    age: conint(gt=18)