import razorpay
import logging
from ..core.config import settings

class PaymentService:
    def __init__(self):
        self.client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))

    def create_order(self, amount_in_paisa: int, receipt: str):
        """
        Creates a Razorpay order.
        """
        try:
            order_data = {
                'amount': amount_in_paisa,
                'currency': 'INR',
                'receipt': receipt,
                'payment_capture': 1 # Auto capture
            }
            return self.client.order.create(data=order_data)
        except Exception as e:
            logging.error(f"Razorpay Order Creation Failed: {e}")
            return None

    def verify_signature(self, body: str, signature: str):
        """
        Verifies the webhook signature.
        """
        try:
            return self.client.utility.verify_webhook_signature(
                body, 
                signature, 
                settings.razorpay_key_secret
            )
        except Exception as e:
            logging.error(f"Razorpay Signature Verification Failed: {e}")
            return False

payment_service = PaymentService()
