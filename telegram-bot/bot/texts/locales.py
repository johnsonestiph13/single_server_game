# telegram-bot/bot/texts/locales.py
# Estif Bingo 24/7 - Localization Module
# Contains English and Amharic translations for all bot messages

from typing import Dict, Optional
from bot.texts.emojis import get_emoji

# ==================== ENGLISH TEXTS ====================

ENGLISH_TEXTS: Dict[str, str] = {
    # Welcome & Start
    'welcome': f"{get_emoji('game')} *Welcome to Estif Bingo 24/7!* {get_emoji('game')}\n\n"
               f"Experience the thrill of real-time multiplayer bingo!\n\n"
               f"🎯 *Features:*\n"
               f"• Real-time multiplayer games\n"
               f"• 1000+ unique cartelas\n"
               f"• Secure deposits and withdrawals\n"
               f"• Instant payouts\n"
               f"• 24/7 customer support\n\n"
               f"Use the menu below to get started! 🚀",
    
    'already_registered': f"{get_emoji('info')} You are already registered!\n\n"
                          f"Use /play to start playing or /balance to check your funds.",
    
    'register_prompt': f"{get_emoji('phone')} *Registration Required*\n\n"
                       f"To play and win real prizes, please share your phone number.\n\n"
                       f"🔒 Your number is encrypted and stored securely.\n\n"
                       f"Click the button below to share your contact:",
    
    # Deposit
    'deposit_select': f"{get_emoji('deposit')} *Select Deposit Method*\n\n"
                      f"Choose your preferred payment method:\n\n"
                      f"Account Holder: *Estif Bingo 24/7*",
    
    'deposit_selected': f"{get_emoji('info')} *CBE Selected*\n\n"
                        f"Send the amount to:\n"
                        f"Account: `1000123456789`\n"
                        f"Account Holder: *Estif Bingo 24/7*\n\n"
                        f"After sending, send us the transaction ID and screenshot.",
    
    'deposit_sent': f"{get_emoji('success')} *Deposit Request Sent!*\n\n"
                    f"Your deposit request has been submitted.\n"
                    f"Admin will review and approve it shortly.\n\n"
                    f"You will be notified once approved.",
    
    # Withdrawal
    'withdraw_prompt': f"{get_emoji('cashout')} *Withdrawal Request*\n\n"
                       f"Enter the amount you want to withdraw:\n"
                       f"Minimum: *50 ETB*\n"
                       f"Maximum: *10000 ETB*",
    
    'withdraw_method': f"{get_emoji('bank')} *Select Withdrawal Method*\n\n"
                       f"Choose how you want to receive your funds:",
    
    'withdraw_sent': f"{get_emoji('success')} *Withdrawal Request Sent!*\n\n"
                     f"Your withdrawal request has been submitted.\n"
                     f"Admin will review and process it within 24-48 hours.",
    
    # Transfer
    'transfer_prompt': f"{get_emoji('transfer')} *Balance Transfer*\n\n"
                       f"Enter the recipient's phone number:",
    
    'transfer_amount': f"{get_emoji('money')} *Transfer Amount*\n\n"
                       f"Enter the amount to transfer:\n"
                       f"Minimum: *10 ETB*\n"
                       f"Maximum: *5000 ETB*\n"
                       f"Fee: *0%*",
    
    'transfer_success': f"{get_emoji('success')} *Transfer Successful!*\n\n"
                        f"Sent: *0 ETB*\n"
                        f"Fee: *0 ETB*\n"
                        f"Total deducted: *0 ETB*\n"
                        f"To: *User*\n\n"
                        f"New balance: *0 ETB*",
    
    # Balance
    'balance_display': f"{get_emoji('balance')} *Your Balance*\n\n"
                       f"💰 Current Balance: *0 ETB*\n\n"
                       f"Use /deposit to add funds or /cashout to withdraw.",
    
    # Game
    'play_prompt': f"{get_emoji('game')} *Ready to Play?*\n\n"
                   f"Click the button below to launch the game!\n\n"
                   f"🎯 *Game Info:*\n"
                   f"• Cartela price: *10 ETB*\n"
                   f"• Max cartelas: *4*\n"
                   f"• Selection time: *50s*\n"
                   f"• Win rate: *80%*",
    
    'game_rules': f"{get_emoji('info')} *Game Rules*\n\n"
                  f"🎯 *How to Win:*\n"
                  f"• Complete a horizontal line\n"
                  f"• Complete a vertical line\n"
                  f"• Complete a diagonal line\n\n"
                  f"💰 *Prizes:*\n"
                  f"• 80% of total bets goes to winners\n"
                  f"• Prize split equally among winners\n\n"
                  f"⚡ *Real-time:* All players see the same numbers!",
    
    # Invite
    'invite_message': f"{get_emoji('invite')} *Invite Friends!*\n\n"
                      f"Share this link with your friends:\n"
                      f"`https://t.me/YourBot`\n\n"
                      f"When they register, you both get rewards! 🎁",
    
    # Contact
    'contact': f"{get_emoji('support')} *Contact Support*\n\n"
               f"Choose an option below to get help:\n\n"
               f"📢 *Channel:* Updates and announcements\n"
               f"👥 *Group:* Community support\n"
               f"👑 *Admin:* Direct message to support",
    
    # Bonus
    'welcome_bonus': f"{get_emoji('gift')} *Welcome Bonus!*\n\n"
                     f"You received *30 ETB* welcome bonus!\n\n"
                     f"Use /play to start playing! 🎮",
    
    'daily_bonus': f"{get_emoji('calendar')} *Daily Bonus!*\n\n"
                   f"You received *5 ETB* daily bonus!\n\n"
                   f"Come back tomorrow for more!",
    
    'bonus_already_claimed': f"{get_emoji('info')} *Bonus Already Claimed*\n\n"
                             f"You have already claimed your welcome bonus.\n\n"
                             f"Use /play to start playing!",
    
    # Admin
    'admin_only': f"{get_emoji('error')} *Admin Access Required*\n\n"
                  f"This command is only available to administrators.",
    
    # Errors
    'error_general': f"{get_emoji('error')} *An error occurred*\n\n"
                     f"Please try again later. If the problem persists, contact support.",
    
    'error_insufficient_balance': f"{get_emoji('error')} *Insufficient Balance*\n\n"
                                  f"Your balance: *0 ETB*\n"
                                  f"Required: *10 ETB*\n\n"
                                  f"Use /deposit to add funds.",
    
    'error_invalid_amount': f"{get_emoji('error')} *Invalid Amount*\n\n"
                            f"Please enter a valid amount.\n"
                            f"Minimum: *10 ETB*\n"
                            f"Maximum: *10000 ETB*",
    
    'error_invalid_phone': f"{get_emoji('error')} *Invalid Phone Number*\n\n"
                           f"Please enter a valid phone number.\n"
                           f"Example: `0912345678`",
    
    'error_user_not_found': f"{get_emoji('error')} *User Not Found*\n\n"
                            f"No user found with that information.\n\n"
                            f"Make sure the user is registered.",
    
    'error_self_transfer': f"{get_emoji('error')} *Self-Transfer Not Allowed*\n\n"
                           f"You cannot transfer funds to yourself.",
    
    # Success
    'success_registration': f"{get_emoji('success')} *Registration Successful!*\n\n"
                            f"Your account has been created.\n"
                            f"Welcome to Estif Bingo 24/7! 🎉",
    
    'success_deposit': f"{get_emoji('success')} *Deposit Successful!*\n\n"
                       f"*0 ETB* has been added to your balance.\n"
                       f"New balance: *0 ETB*",
    
    'success_withdrawal': f"{get_emoji('success')} *Withdrawal Successful!*\n\n"
                          f"*0 ETB* has been sent to your account.\n"
                          f"New balance: *0 ETB*",
    
    # Buttons
    'btn_play': f"{get_emoji('game')} Play",
    'btn_deposit': f"{get_emoji('deposit')} Deposit",
    'btn_cashout': f"{get_emoji('cashout')} Cashout",
    'btn_balance': f"{get_emoji('balance')} Balance",
    'btn_transfer': f"{get_emoji('transfer')} Transfer",
    'btn_invite': f"{get_emoji('invite')} Invite",
    'btn_contact': f"{get_emoji('support')} Contact",
    'btn_bonus': f"{get_emoji('bonus')} Bonus",
    'btn_back': f"{get_emoji('back')} Back",
    'btn_cancel': f"{get_emoji('cancel')} Cancel",
    'btn_confirm': f"{get_emoji('confirm')} Confirm",
}


# ==================== AMHARIC TEXTS ====================

AMHARIC_TEXTS: Dict[str, str] = {
    # Welcome & Start
    'welcome': f"{get_emoji('game')} *እንኳን ወደ እስቲፍ ቢንጎ 24/7 በደህና መጡ!* {get_emoji('game')}\n\n"
               f"የሪል ታይም መልቲፕሌየር ቢንጎ ደስታን ይለማመዱ!\n\n"
               f"🎯 *ባህሪያት:*\n"
               f"• የሪል ታይም መልቲፕሌየር ጨዋታዎች\n"
               f"• ከ1000 በላይ ልዩ ካርቴላዎች\n"
               f"• ደህንነቱ የተጠበቀ ተቀማጭ እና መውጫ\n"
               f"• ፈጣን ክፍያ\n"
               f"• 24/7 የደንበኛ ድጋፍ\n\n"
               f"ለመጀመር ከታች ያለውን ምናሌ ይጠቀሙ! 🚀",
    
    'already_registered': f"{get_emoji('info')} ቀድመው ተመዝግበዋል!\n\n"
                          f"/play በመጠቀም መጫወት ወይም ቀሪ ሒሳብዎን ለማየት /balance ይጠቀሙ።",
    
    'register_prompt': f"{get_emoji('phone')} *ምዝገባ ያስፈልጋል*\n\n"
                       f"ለመጫወት እና ሽልማቶችን ለማሸነፍ እባክዎ ስልክ ቁጥርዎን ያጋሩ።\n\n"
                       f"🔒 ቁጥርዎ በምስጠራ ደህንነቱ በተጠበቀ ሁኔታ ይቀመጣል።\n\n"
                       f"እውቂያዎን ለማጋራት ከታች ያለውን ቁልፍ ይጫኑ:",
    
    # Deposit
    'deposit_select': f"{get_emoji('deposit')} *የተቀማጭ ዘዴ ይምረጡ*\n\n"
                      f"የሚመርጡትን የክፍያ ዘዴ ይምረጡ:\n\n"
                      f"የሂሳብ ባለቤት: *እስቲፍ ቢንጎ 24/7*",
    
    'deposit_selected': f"{get_emoji('info')} *CBE ተመርጧል*\n\n"
                        f"ገንዘቡን ወደዚህ ላኩ:\n"
                        f"አካውንት: `1000123456789`\n"
                        f"የሂሳብ ባለቤት: *እስቲፍ ቢንጎ 24/7*\n\n"
                        f"ከላኩ በኋላ የግብይት መለያውን እና ስክሪን ሾቱን ላኩልን።",
    
    'deposit_sent': f"{get_emoji('success')} *የተቀማጭ ጥያቄ ተልኳል!*\n\n"
                    f"የተቀማጭ ጥያቄዎ ተልኳል።\n"
                    f"አስተዳዳሪዎች በቅርቡ ይገመግሙታል።\n\n"
                    f"ሲፀድቅ ይነገሩዎታል።",
    
    # Withdrawal
    'withdraw_prompt': f"{get_emoji('cashout')} *የመውጫ ጥያቄ*\n\n"
                       f"ማውጣት የሚፈልጉትን ገንዘብ ያስገቡ:\n"
                       f"ዝቅተኛ: *50 ETB*\n"
                       f"ከፍተኛ: *10000 ETB*",
    
    'withdraw_method': f"{get_emoji('bank')} *የመውጫ ዘዴ ይምረጡ*\n\n"
                       f"ገንዘብዎን እንዴት መቀበል እንደሚፈልጉ ይምረጡ:",
    
    'withdraw_sent': f"{get_emoji('success')} *የመውጫ ጥያቄ ተልኳል!*\n\n"
                     f"የመውጫ ጥያቄዎ ተልኳል።\n"
                     f"አስተዳዳሪዎች በ24-48 ሰአታት ውስጥ ይገመግሙታል።",
    
    # Transfer
    'transfer_prompt': f"{get_emoji('transfer')} *የሂሳብ ዝውውር*\n\n"
                       f"የሚቀበለውን ሰው ስልክ ቁጥር ያስገቡ:",
    
    'transfer_amount': f"{get_emoji('money')} *የዝውውር መጠን*\n\n"
                       f"ለማዛወር የሚፈልጉትን ገንዘብ ያስገቡ:\n"
                       f"ዝቅተኛ: *10 ETB*\n"
                       f"ከፍተኛ: *5000 ETB*\n"
                       f"ክፍያ: *0%*",
    
    'transfer_success': f"{get_emoji('success')} *ዝውውር ተሳክቷል!*\n\n"
                        f"ተልኳል: *0 ETB*\n"
                        f"ክፍያ: *0 ETB*\n"
                        f"ጠቅላላ ተቀንሷል: *0 ETB*\n"
                        f"ለ: *ተጠቃሚ*\n\n"
                        f"አዲስ ቀሪ ሒሳብ: *0 ETB*",
    
    # Balance
    'balance_display': f"{get_emoji('balance')} *ቀሪ ሒሳብዎ*\n\n"
                       f"💰 የአሁኑ ቀሪ ሒሳብ: *0 ETB*\n\n"
                       f"ገንዘብ ለመጨመር /deposit ወይም ለማውጣት /cashout ይጠቀሙ።",
    
    # Game
    'play_prompt': f"{get_emoji('game')} *ለመጫወት ዝግጁ?*\n\n"
                   f"ጨዋታውን ለመክፈት ከታች ያለውን ቁልፍ ይጫኑ!\n\n"
                   f"🎯 *የጨዋታ መረጃ:*\n"
                   f"• የካርቴላ ዋጋ: *10 ETB*\n"
                   f"• ከፍተኛ ካርቴላዎች: *4*\n"
                   f"• የመምረጫ ጊዜ: *50 ሰከንድ*\n"
                   f"• የማሸነፍ መጠን: *80%*",
    
    'game_rules': f"{get_emoji('info')} *የጨዋታ ህጎች*\n\n"
                  f"🎯 *እንዴት ማሸነፍ ይቻላል:*\n"
                  f"• አግድም መስመር ሙሉ ማድረግ\n"
                  f"• ቀጥ ያለ መስመር ሙሉ ማድረግ\n"
                  f"• ሰያፍ መስመር ሙሉ ማድረግ\n\n"
                  f"💰 *ሽልማቶች:*\n"
                  f"• ከጠቅላላ ውርርድ 80% ለአሸናፊዎች ይሰጣል\n"
                  f"• ሽልማት በአሸናፊዎች መካከል እኩል ይከፈላል\n\n"
                  f"⚡ *የሪል ታይም:* ሁሉም ተጫዋቾች አንድ አይነት ቁጥሮች ያያሉ!",
    
    # Invite
    'invite_message': f"{get_emoji('invite')} *ጓደኞችን ይጋብዙ!*\n\n"
                      f"ይህን አገናኝ ከጓደኞችዎ ጋር ያጋሩ:\n"
                      f"`https://t.me/YourBot`\n\n"
                      f"እነሱ ሲመዘገቡ ሁለታችሁም ሽልማት ታገኛላችሁ! 🎁",
    
    # Contact
    'contact': f"{get_emoji('support')} *ድጋፍ ያግኙ*\n\n"
               f"እርዳታ ለማግኘት ከታች ካሉት አማራጮች ይምረጡ:\n\n"
               f"📢 *ቻናል:* ማሻሻያዎች እና ማስታወቂያዎች\n"
               f"👥 *ቡድን:* የማህበረሰብ ድጋፍ\n"
               f"👑 *አስተዳዳሪ:* በቀጥታ ወደ ድጋፍ",
    
    # Bonus
    'welcome_bonus': f"{get_emoji('gift')} *እንኳን ደህና መጣችሁ ሽልማት!*\n\n"
                     f"*30 ETB* የእንኳን ደህና መጣችሁ ሽልማት ተቀብለዋል!\n\n"
                     f"መጫወት ለመጀመር /play ይጠቀሙ! 🎮",
    
    'daily_bonus': f"{get_emoji('calendar')} *የዕለት ሽልማት!*\n\n"
                   f"*5 ETB* የዕለት ሽልማት ተቀብለዋል!\n\n"
                   f"ነገ ተመልሰው ይጎብኙ!",
    
    'bonus_already_claimed': f"{get_emoji('info')} *ሽልማት አስቀድሞ ተጠይቋል*\n\n"
                             f"የእንኳን ደህና መጣችሁ ሽልማትዎን አስቀድመው ጠይቀዋል።\n\n"
                             f"መጫወት ለመጀመር /play ይጠቀሙ!",
    
    # Admin
    'admin_only': f"{get_emoji('error')} *የአስተዳዳሪ ፈቃድ ያስፈልጋል*\n\n"
                  f"ይህ ትእዛዝ ለአስተዳዳሪዎች ብቻ ነው።",
    
    # Errors
    'error_general': f"{get_emoji('error')} *ስህተት ተከስቷል*\n\n"
                     f"እባክዎ ቆይተው እንደገና ይሞክሩ። ችግሩ ከቀጠለ ድጋፍ ያግኙ።",
    
    'error_insufficient_balance': f"{get_emoji('error')} *በቂ ገንዘብ የለም*\n\n"
                                  f"ቀሪ ሒሳብዎ: *0 ETB*\n"
                                  f"የሚጠበቀው: *10 ETB*\n\n"
                                  f"ገንዘብ ለመጨመር /deposit ይጠቀሙ።",
    
    'error_invalid_amount': f"{get_emoji('error')} *የማይሰራ መጠን*\n\n"
                            f"እባክዎ ትክክለኛ መጠን ያስገቡ።\n"
                            f"ዝቅተኛ: *10 ETB*\n"
                            f"ከፍተኛ: *10000 ETB*",
    
    'error_invalid_phone': f"{get_emoji('error')} *የማይሰራ ስልክ ቁጥር*\n\n"
                           f"እባክዎ ትክክለኛ ስልክ ቁጥር ያስገቡ።\n"
                           f"ምሳሌ: `0912345678`",
    
    'error_user_not_found': f"{get_emoji('error')} *ተጠቃሚ አልተገኘም*\n\n"
                            f"ከዚያ መረጃ ጋር ምንም ተጠቃሚ አልተገኘም።\n\n"
                            f"ተጠቃሚው መመዝገቡን ያረጋግጡ።",
    
    'error_self_transfer': f"{get_emoji('error')} *ራስን ማዛወር አይፈቀድም*\n\n"
                           f"ገንዘብ ወደ ራስዎ ማዛወር አይችሉም።",
    
    # Success
    'success_registration': f"{get_emoji('success')} *ምዝገባ ተሳክቷል!*\n\n"
                            f"አካውንትዎ ተፈጥሯል።\n"
                            f"እንኳን ወደ እስቲፍ ቢንጎ 24/7 በደህና መጡ! 🎉",
    
    'success_deposit': f"{get_emoji('success')} *ተቀማጭ ገንዘብ ተሳክቷል!*\n\n"
                       f"*0 ETB* ወደ ቀሪ ሒሳብዎ ተጨምሯል።\n"
                       f"አዲስ ቀሪ ሒሳብ: *0 ETB*",
    
    'success_withdrawal': f"{get_emoji('success')} *መውጫ ገንዘብ ተሳክቷል!*\n\n"
                          f"*0 ETB* ወደ አካውንትዎ ተልኳል።\n"
                          f"አዲስ ቀሪ ሒሳብ: *0 ETB*",
    
    # Buttons
    'btn_play': f"{get_emoji('game')} ጫወት",
    'btn_deposit': f"{get_emoji('deposit')} ገንዘብ ጨምር",
    'btn_cashout': f"{get_emoji('cashout')} ገንዘብ አውጣ",
    'btn_balance': f"{get_emoji('balance')} ቀሪ ሒሳብ",
    'btn_transfer': f"{get_emoji('transfer')} አዛውር",
    'btn_invite': f"{get_emoji('invite')} ጋብዝ",
    'btn_contact': f"{get_emoji('support')} አግኙን",
    'btn_bonus': f"{get_emoji('bonus')} ሽልማት",
    'btn_back': f"{get_emoji('back')} ተመለስ",
    'btn_cancel': f"{get_emoji('cancel')} ሰርዝ",
    'btn_confirm': f"{get_emoji('confirm')} አረጋግጥ",
}


# ==================== TEXT FUNCTIONS ====================

TEXTS: Dict[str, Dict[str, str]] = {
    'en': ENGLISH_TEXTS,
    'am': AMHARIC_TEXTS,
}


def get_text(key: str, lang: str = 'en', **kwargs) -> str:
    """
    Get localized text by key.
    
    Args:
        key: Text key
        lang: Language code ('en' or 'am')
        **kwargs: Format parameters
    
    Returns:
        str: Localized and formatted text
    """
    lang_dict = TEXTS.get(lang, TEXTS['en'])
    text = lang_dict.get(key, key)
    
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    
    return text


def get_language_name(lang: str) -> str:
    """Get language name in its own language."""
    if lang == 'am':
        return 'አማርኛ'
    return 'English'


# ==================== EXPORTS ====================

__all__ = [
    'ENGLISH_TEXTS',
    'AMHARIC_TEXTS',
    'TEXTS',
    'get_text',
    'get_language_name',
]