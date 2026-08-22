from fastapi import APIRouter, HTTPException

from recommendation.user_recommender import recommend_for_user

router = APIRouter(
    prefix="/api/ai",
    tags=["AI"]
)


@router.get("/recommendations/{user_id}")
def get_recommendations(user_id: int):

    recommendations = recommend_for_user(user_id)

    if recommendations is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return {
        "user_id": user_id,
        "count": len(recommendations),
        "recommendations": recommendations
    }