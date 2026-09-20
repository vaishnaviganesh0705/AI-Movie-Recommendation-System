# removed incorrect django import; use get_db dependency for DB sessions
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User

from ..schemas import (
    UserCreate,
    UserResponse,
    LoginRequest,
    Token,
)

from ..auth import (
    hash_password,
    verify_password,
    create_access_token,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse
)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):

    existing_user = (
        db.query(User)
        .filter(
            User.email == user_data.email
        )
        .first()
    )

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )


    if (
        user_data.password
        != user_data.confirmPassword
    ):

        raise HTTPException(
            status_code=400,
            detail="Passwords do not match"
        )


    hashed_password = hash_password(
        user_data.password
    )


    new_user = User(

        name=user_data.name,

        email=user_data.email,

        password=hashed_password,

        role="user"
    )


    db.add(new_user)

    db.commit()

    db.refresh(new_user)


    return new_user


@router.post("/login")
def login(
    user_data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        user_data.password,
        user.password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "user_id": user.id,
        "name": user.name,
        "email": user.email
    }

@router.get("/stats")
def stats(db: Session = Depends(get_db)):

    # Minimal local fallback for tmdb_get to avoid external dependency.
    def tmdb_get(path: str):
        # returns empty results if TMDB integration isn't available
        return {"results": []}

    trending = tmdb_get("/trending/movie/week")

    return {
       "total_users": db.query(User).count(),
        "total_music": 0,
        "total_podcasts": 0
    }