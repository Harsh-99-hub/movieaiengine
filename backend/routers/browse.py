from fastapi import APIRouter

router = APIRouter(prefix="/browse")

@router.get("/")
def browse():
    return {"message": "browse working"}