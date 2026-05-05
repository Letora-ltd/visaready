import os
import stripe
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.entities import User, SubscriptionRecord, ProcessedStripeEvent

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder")
webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")

class PaymentService:
    async def create_checkout_session(self, user_id: str, email: str):
        """Creates a Stripe Checkout Session for Premium subscription."""
        try:
            # Price ID should ideally be in env
            # For UK (£4.99/month), you'd create this in Stripe Dashboard
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'gbp',
                        'product_data': {
                            'name': 'Vixaa Premium Tracker',
                            'description': 'Instant alerts and multi-center tracking',
                        },
                        'unit_amount': 499, # £4.99
                        'recurring': {'interval': 'month'},
                    },
                    'quantity': 1,
                }],
                mode='subscription',
                success_url='https://vixaa.online/dashboard?payment=success',
                cancel_url='https://vixaa.online/dashboard?payment=cancel',
                customer_email=email,
                client_reference_id=user_id,
            )
            return session.url
        except Exception as e:
            logger.error(f"Error creating Stripe session: {e}")
            raise

    async def handle_webhook(self, payload: bytes, sig_header: str, db: AsyncSession):
        """Processes Stripe webhook events with deduplication and safety checks."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise e

        # 1. Deduplication (Sprint 3.5)
        event_id = event['id']
        check_stmt = select(ProcessedStripeEvent).where(ProcessedStripeEvent.event_id == event_id)
        if (await db.execute(check_stmt)).scalars().first():
            logger.info(f"⏭️ Skipping duplicate Stripe event: {event_id}")
            return

        # 2. Safety Check (Live vs Test Mode)
        # You can log this or enforce specific behavior
        if not event['livemode']:
            logger.info(f"🧪 Processing Stripe TEST event: {event_id}")

        # 3. Handle Events
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = session['client_reference_id']
            await self._activate_premium(user_id, db)
            
        elif event['type'] == 'invoice.payment_succeeded':
            # Renewal success - extend expiry
            invoice = event['data']['object']
            customer_email = invoice.get('customer_email')
            if customer_email:
                await self._renew_premium(customer_email, db)

        elif event['type'] == 'invoice.payment_failed':
            # Renewal failed - notify and prepare for downgrade
            invoice = event['data']['object']
            customer_email = invoice.get('customer_email')
            if customer_email:
                await self._handle_payment_failure(customer_email, db)

        # 4. Mark event as processed
        db.add(ProcessedStripeEvent(event_id=event_id))
        await db.commit()

    async def _activate_premium(self, user_id: str, db: AsyncSession):
        """Updates user to Premium with a 2-day grace period (Sprint 3.5)."""
        try:
            stmt = select(User).where(User.id == user_id)
            res = await db.execute(stmt)
            user = res.scalars().first()
            
            if user:
                # 30 days + 2 days grace period
                expiry = datetime.now() + timedelta(days=32) 
                user.subscription_type = 'premium'
                user.subscription_expiry = expiry
                
                record = SubscriptionRecord(
                    user_id=user.id,
                    plan='premium',
                    status='active',
                    end_date=expiry
                )
                db.add(record)
                # Note: commit is handled in handle_webhook
                
                logger.info(f"💎 PREMIUM ACTIVATED: User {user_id}")
                
                if user.telegram_chat_id:
                    from .telegram_service import telegram_service
                    await telegram_service.send_message(
                        user.telegram_chat_id, 
                        "💎 <b>PREMIUM ACTIVATED!</b>\n\n"
                        "Instant alerts enabled. You have a 2-day grace period on all renewals. 🚀"
                    )
        except Exception as e:
            logger.error(f"Error activating premium: {e}")

    async def _renew_premium(self, email: str, db: AsyncSession):
        """Extends subscription on successful renewal."""
        stmt = select(User).where(User.email == email)
        user = (await db.execute(stmt)).scalars().first()
        if user:
            user.subscription_type = 'premium'
            user.subscription_expiry = datetime.now() + timedelta(days=32)
            logger.info(f"🔄 PREMIUM RENEWED: {email}")

    async def _handle_payment_failure(self, email: str, db: AsyncSession):
        """Notifies user of payment failure."""
        stmt = select(User).where(User.email == email)
        user = (await db.execute(stmt)).scalars().first()
        if user and user.telegram_chat_id:
            from .telegram_service import telegram_service
            await telegram_service.send_message(
                user.telegram_chat_id,
                "⚠️ <b>PAYMENT FAILED</b>\n\n"
                "Your premium renewal failed. We've added a 2-day grace period, but please update your payment method to keep instant alerts active."
            )
            logger.warning(f"❌ PAYMENT FAILURE: {email}")

# Singleton
payment_service = PaymentService()
