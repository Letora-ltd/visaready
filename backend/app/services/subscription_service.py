from datetime import datetime
from ..models.entities import User

def is_premium(user: User) -> bool:
    """
    Checks if a user has an active premium subscription.
    """
    if not user:
        return False
    
    if user.subscription_type != 'premium':
        return False
        
    if not user.subscription_expiry:
        return False
        
    return user.subscription_expiry > datetime.utcnow()
