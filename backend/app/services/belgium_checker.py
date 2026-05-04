from datetime import datetime, timedelta
import random

async def fetch_belgium_slots():
    """
    Simulates fetching visa slots for Belgium.
    In a real scenario, this would call an external API or scrape a website.
    """
    # Mock data
    centers = ["New Delhi", "Mumbai", "Bangalore"]
    visa_types = ["Schengen Short Stay", "Long Stay Student"]
    
    slots = []
    # Simulate finding 0-3 new slots
    num_slots = random.randint(0, 3)
    
    for _ in range(num_slots):
        slot_date = datetime.now() + timedelta(days=random.randint(10, 60))
        slots.append({
            "country": "Belgium",
            "center": random.choice(centers),
            "visa_type": random.choice(visa_types),
            "slot_date": slot_date,
            "slot_time": f"{random.randint(9, 16)}:00",
        })
    
    return slots
