from fastapi import APIRouter

router = APIRouter(prefix="/user")

@router.get("/")
def test():
    return {"message": "user route working"}