from fastapi import FastAPI, HTTPException, status
from .schemas import User

app = FastAPI()
users: list[User] = []

@app.get("/health")
def get_health():
    return {"status": "ok"}

#return all users 
@app.get("/api/users")
def get_users():
    return users

#Get user by id
@app.get("/api/users/{user_id}")
def get_user(user_id: int):
    for u in users: 
        if u.user_id == user_id: 
            return u 
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@app.post("/api/users", status_code=status.HTTP_201_CREATED)
def add_user(user: User):
    if any(u.user_id == user.user_id for u in users):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="user_id already exists")
    if any(u.student_id == user.student_id for u in users): #If an existing student ID exists, don't add user
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="student_id already exists")
    users.append(user)
    return user

@app.put("/api/users/{user_id}", status_code=status.HTTP_202_ACCEPTED)
def update_user(user_id: int, user: User):
    for i, u in enumerate(users): #I as the index and u as the user object
        if u.user_id == user_id: 
            users[i] = user  #Replace old user with new entered user
            return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int):
    for i,e in enumerate(users):
        if e.user_id == user_id:
            users.pop(i)
            return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")