# ============================================================
# admin_panel/reseller.py
# ============================================================
# Reseller-specific commands. Resellers are admins with a
# limited scope: they can see their referrals, commissions,
# and a copy of their referral link.
# ============================================================

from core.router import mother_router
from core.permission_manager import get_role, ROLE_RESELLER
from reseller.affiliate_manager import (
    make_ref_code, count_referrals, list_referrals,
)
from wallet.wallet_manager import get_balance


def setup():

    @mother_router.command("reseller")
    def _reseller_panel(ctx):
        if get_role(ctx.user_id) != ROLE_RESELLER:
            ctx.reply("⛔ این بخش فقط برای نمایندگان است.")
            return
        ref_code = make_ref_code(ctx.db_user_id)
        ctx.reply(
            "🧑‍💼 پنل نمایندگی شما\n\n"
            "🔗 کد دعوت: <code>{code}</code>\n"
            "🪪 نمونه لینک: /start {code}\n"
            "👥 تعداد دعوت‌شدگان: {n}\n"
            "💰 موجودی شما: {bal:,} ریال\n\n"
            "/referrals برای مشاهده فهرست".format(
                code=ref_code,
                n=count_referrals(ctx.db_user_id),
                bal=get_balance(ctx.db_user_id),
            ),
            parse_mode="HTML",
        )

    @mother_router.command("referrals")
    def _referrals(ctx):
        if get_role(ctx.user_id) != ROLE_RESELLER:
            return
        rows = list_referrals(ctx.db_user_id, limit=20)
        if not rows:
            ctx.reply("هنوز کسی با کد شما عضو نشده.")
            return
        text = "👥 دعوت‌شدگان شما:\n\n" + "\n".join(
            "- {} (id={}) @ {}".format(
                r.get("first_name") or "-", r["bale_user_id"], r["created_at"]
            ) for r in rows
        )
        ctx.reply(text)
