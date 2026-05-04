from datetime import datetime, timezone
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
        
    # Ensure both are timezone aware for comparison
    expiry = user.subscription_expiry
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
        
    return expiry > datetime.now(timezone.utc)
