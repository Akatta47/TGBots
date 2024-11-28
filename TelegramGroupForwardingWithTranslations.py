from telegram import Update, PhotoSize
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler
import telegram.ext.filters as filters
from telegram.error import TelegramError, BadRequest
import logging
import time
from deep_translator import GoogleTranslator
import re
from collections import deque
from telegram.constants import ParseMode
import traceback


# Define a regex pattern for finding emojis
emoji_pattern = re.compile("["
                           u"\U0001F600-\U0001F64F"  # emoticons
                           u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                           u"\U0001F680-\U0001F6FF"  # transport & map symbols
                           u"\U0001F700-\U0001F77F"  # alchemical symbols
                           u"\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
                           u"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
                           u"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
                           u"\U0001FA00-\U0001FA6F"  # Chess Symbols
                           u"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
                           u"\U00002702-\U000027B0"  # Dingbats
                           "]+", flags=re.UNICODE)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

# Your bot token you got from BotFather
TOKEN = 'Telegram Bot Token'

# The chat ID of the group from which to forward messages with a specific #
SOURCE_GROUP_ID = "group_id"  # Replace with the topic group chat ID

# A dict mapping chat_id to its desired language for translation

TRANSLATION_TARGETS = {
    "group_id":"it"
    "group_id":"es"
    "group_id":"en"
}

HUDIHEART = "group_id"


MULTIGROUP_TRANSLATION_TARGETS = {
    "group_id":"it"
    "group_id":"es"
    "group_id":"en"
    
}


MULTIGROUP_TRANSLATION_TARGETS_FLAGS = {
    "group_id":"it"
    "group_id":"es"
    "group_id":"en"
}



SPAMWORDS =['mining','bot']

message_timestamps = deque()


source_to_destination_msg_id_map = {}
destination_to_source_msg_id_map = {}
same_group_message_di_map = {}

logger = logging.getLogger(__name__)

WHITELIST = []  # Replace with actual IDs/usernames
BLACKLIST=['Telegram', 'telegram']

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check messages for the #HUDINOW hashtag or are sent from the news channel, translate them, and forward if from the specified group."""
    message = update.effective_message
    bot_user = await context.bot.get_me()
    usrandgroup = ""

    if update.effective_user is not None:
        sender_usr = update.effective_user.username
    else:
        sender_usr = ''
        
    if message.text:
        if not message.text.startswith('/'):

            if (message.photo and message.caption and '#HUDINOW' in message.caption and message.chat_id == SOURCE_GROUP_ID and sender_usr in WHITELIST and sender_usr not in BLACKLIST) or (message.text and '#HUDINOW' in message.text and message.chat_id == SOURCE_GROUP_ID and sender_usr in WHITELIST and sender_usr not in BLACKLIST):
                await hudinow(update, context, sender_usr, usrandgroup)

            if message.chat_id in MULTIGROUP_TRANSLATION_TARGETS:
                if update.edited_message is not None:
                    await handle_edited_message(update, context, sender_usr)
                else: 
                    if message.from_user.id != bot_user.id:
                        await multigroup(update, context, sender_usr)

    

async def hudinow(update: Update, context: ContextTypes.DEFAULT_TYPE, sender_usr, usrandgroup):
    message = update.effective_message
    if message.photo and message.caption:
        # Translate and forward the message for each group according to its specified language
        for group_id, lang in TRANSLATION_TARGETS.items():
            try:
                # Remove the hashtag for translation
                text_to_translate = message.caption.replace('#HUDINOW', '')
                translated_caption = translate_text(
                    text_to_translate, lang, sender_usr, True, usrandgroup)

                # Send photo with translated caption
                # Highest resolution photo
                photo_file_id = message.photo[-1].file_id
                await rate_limit()
                await context.bot.send_photo(
                    chat_id=group_id,
                    photo=photo_file_id,
                    caption=translated_caption
                )

            except TelegramError as e:
                logger.error(
                    f"An error occurred while forwarding a photo to group {group_id}: {e.message}")
            except Exception as e:
                tb_str = traceback.format_exc()
                logger.error(
                    f"An error occurred during text translation: {type(e).__name__}, {str(e)}\nTraceback:\n{tb_str}")

    # Check if the message is text containing #HUDINOW
    if message.text:
        # Translate and forward the message for each group according to its specified language
        for group_id, lang in TRANSLATION_TARGETS.items():
            try:
                # Remove the hashtag for translation
                text_to_translate = message.text.replace('#HUDINOW', '')
                translated_text_with_emojis = translate_text(
                    text_to_translate, lang, sender_usr, True, usrandgroup)
                await rate_limit()
                await context.bot.send_message(chat_id=group_id, text=translated_text_with_emojis)

            except TelegramError as e:
                logger.error(
                    f"An error occurred while forwarding a message to group {group_id}: {e.message}")
            except Exception as e:
                logger.error(
                    f"An error occurred during text translation: {type(e).__name__}, {str(e)}")


async def multigroup(update: Update, context: ContextTypes.DEFAULT_TYPE, sender_usr) -> None:
    message = update.effective_message

    is_admin, custom_title, spam, user_displayed_name = await adminandspam(update, context)
    if not spam:

        if message.photo:
            await sendphoto(update, context,sender_usr)

        # Check if the message is text containing #HUDINOW
        if message.text:
            # Translate and forward the message for each group according to its specified language
            await sendmessage(update, context,sender_usr)

        if message.sticker:
            await sendsticker(update, context,sender_usr)


async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE, sender_usr) -> None:
    edited_message = update.effective_message
    chat_id = update.effective_chat.id
    original_message_id = edited_message.message_id
    custom_title = ""
    spam = False
    
    if edited_message is not None:
        user = edited_message.from_user
        user_displayed_name = user.first_name
        
        if user.last_name:  # If the user has a last name, append it.
            user_displayed_name += " " + user.last_name

        # Placeholder variable for admin status
        is_admin = False

        try:
            # Retrieve a list of all administrators in the chat
            chat_administrators = await context.bot.get_chat_administrators(edited_message.chat_id)
            # Find the admin that matches the message sender and get their custom title
            for admin in chat_administrators:
                if admin.user.id == user.id and admin.custom_title is not None:
                    custom_title = admin.custom_title
                    is_admin = True
                    break
        except Exception as e:
            logger.error(
                f"Failed to get chat administrators or custom title: {e}")
    
        try:
            # Remove the hashtag for translation
            if custom_title != "" and custom_title is not None:
                usrandgroup = getflag(chat_id) + " <b>" + user_displayed_name + '('+sender_usr+')' + ' | '+custom_title+'</b>'+"\n"
            elif sender_usr is not None:
                usrandgroup = getflag(chat_id) + " <b>" + user_displayed_name + '('+sender_usr+')' + '</b>'+"\n"
            else:
                usrandgroup = getflag(chat_id) + " <b>" + user_displayed_name + '('+"hidden"+')' + '</b>'+"\n"
            await rate_limit()
        

            for group_id, lang in MULTIGROUP_TRANSLATION_TARGETS.items():
                if update.effective_chat.id != group_id:
                    if (chat_id, original_message_id, group_id) in source_to_destination_msg_id_map:
                        # Get the corresponding chat_id and message_id in the destination chat
                        dest_chat_id, destination_message_id = source_to_destination_msg_id_map[(
                        chat_id, original_message_id, group_id)]
                        lang = MULTIGROUP_TRANSLATION_TARGETS[dest_chat_id]
                        if edited_message.photo:
                            sent_message = await context.bot.edit_message_caption(chat_id=dest_chat_id, message_id=destination_message_id, caption=translate_text(edited_message.caption, lang, "", False, usrandgroup),
                            parse_mode=ParseMode.HTML)
                        elif edited_message.text:   
                            sent_message = await context.bot.edit_message_text(chat_id=dest_chat_id, message_id=destination_message_id, text=translate_text(edited_message.text, lang, "", False, usrandgroup),
                            parse_mode=ParseMode.HTML)

                        # Use a tuple of (chat_id, message_id, destination_group_id) to uniquely identify each forward event
                        source_to_destination_msg_id_map[(chat_id, edited_message.message_id, group_id)] = (group_id, sent_message.message_id)

                        # For the reverse mapping, since sent_message.message_id is already unique within the group, you can use it as it is
                        destination_to_source_msg_id_map[(group_id, sent_message.message_id)] = (chat_id, edited_message.message_id)
                        same_group_message_di_map[(chat_id, edited_message.message_id)] = (chat_id, edited_message.message_id)

        except Exception as e:
            tb_str = traceback.format_exc()
            logger.error(
            f"An error occurred during text translation: {type(e).__name__}, {str(e)}\nTraceback:\n{tb_str}")
            logger.error(f"Failed to edit message: {e}")


async def sendmessage(update: Update, context: ContextTypes.DEFAULT_TYPE, sender_usr) -> None:
    message = update.effective_message
    chat_id = update.effective_chat.id
    tag = False
    is_admin, custom_title, spam, user_displayed_name = await adminandspam(update, context)
    
    if not spam:
    
        try:
            # Remove the hashtag for translation
            if custom_title != "" and custom_title is not None:
                usrandgroup = getflag(chat_id) + " <b>" + user_displayed_name + '('+sender_usr+')' + ' | '+custom_title+'</b>'+"\n"
            elif sender_usr is not None:
                usrandgroup = getflag(chat_id) + " <b>" + user_displayed_name + '('+sender_usr+')' + '</b>'+"\n"
            else:
                usrandgroup = getflag(chat_id) + " <b>" + user_displayed_name + '('+"hidden"+')' + '</b>'+"\n"
            await rate_limit()
        
                
            text_to_translate = message.text
            await rate_limit()

            if message.chat_id != HUDIHEART:
                group_id = HUDIHEART
                if update.message.reply_to_message is not None :
                    reply_to_message = update.message.reply_to_message
                    # For a reply in the destination group, find the original message and reply there
                    if reply_to_message and ((reply_to_message.chat_id, reply_to_message.message_id) in destination_to_source_msg_id_map or (reply_to_message.chat_id, reply_to_message.message_id) in same_group_message_di_map):
                        
                        if (reply_to_message.chat_id, reply_to_message.message_id) in destination_to_source_msg_id_map:

                            original_chat_id, original_message_id = destination_to_source_msg_id_map[(reply_to_message.chat_id, reply_to_message.message_id)]
                            translated_text_with_emojis = translate_text(text_to_translate, getlang(original_chat_id), sender_usr, tag, usrandgroup)
                            
                            sent_message = await context.bot.send_message(chat_id=original_chat_id, text=translated_text_with_emojis, parse_mode=ParseMode.HTML, reply_to_message_id=original_message_id)
                            # Store the (chat_id, message_id) tuple mapping from source to destination
                            source_to_destination_msg_id_map[(chat_id, message.message_id, original_chat_id)] = (original_chat_id, sent_message.message_id)

                            # Store the reverse mapping as well
                            destination_to_source_msg_id_map[(original_chat_id, sent_message.message_id)] = (
                            chat_id, message.message_id)
                        else:
                            original_chat_id, original_message_id = same_group_message_di_map[(
                            reply_to_message.chat_id, reply_to_message.message_id)]
                            dest_message_id = source_to_destination_msg_id_map[(
                                original_chat_id, original_message_id, HUDIHEART)][1]
                            translated_text_with_emojis = translate_text(text_to_translate, 'en', sender_usr, tag, usrandgroup)
                            sent_message = await context.bot.send_message(chat_id=HUDIHEART, text=translated_text_with_emojis, parse_mode=ParseMode.HTML, reply_to_message_id=dest_message_id,)

                            # Store the (chat_id, message_id) tuple mapping from source to destination
                            source_to_destination_msg_id_map[(chat_id, message.message_id, HUDIHEART)] = (
                            HUDIHEART, sent_message.message_id)
                            # Store the reverse mapping as well
                            destination_to_source_msg_id_map[(HUDIHEART, sent_message.message_id)] = (
                            chat_id, message.message_id)
                else:        
                    translated_text_with_emojis = translate_text(text_to_translate, 'en', sender_usr, tag, usrandgroup)
                    sent_message = await context.bot.send_message(chat_id=HUDIHEART, text=translated_text_with_emojis, parse_mode=ParseMode.HTML)
                    # Use a tuple of (chat_id, message_id, destination_group_id) to uniquely identify each forward event
                    source_to_destination_msg_id_map[(chat_id, message.message_id, HUDIHEART)] = (HUDIHEART, sent_message.message_id)

                    # For the reverse mapping, since sent_message.message_id is already unique within the group, you can use it as it is
                    destination_to_source_msg_id_map[(HUDIHEART, sent_message.message_id)] = (chat_id, message.message_id)
                    same_group_message_di_map[(chat_id, message.message_id)] = (chat_id, message.message_id)
                    
            else: 
                
                if update.message.reply_to_message is not None :
                    reply_to_message = update.message.reply_to_message
                    if reply_to_message and ((reply_to_message.chat_id, reply_to_message.message_id) in destination_to_source_msg_id_map or (reply_to_message.chat_id, reply_to_message.message_id) in same_group_message_di_map):
                        
                        if (reply_to_message.chat_id, reply_to_message.message_id) in destination_to_source_msg_id_map:

                            original_chat_id, original_message_id = destination_to_source_msg_id_map[(reply_to_message.chat_id, reply_to_message.message_id)]
                            translated_text_with_emojis = translate_text(text_to_translate, getlang(original_chat_id), sender_usr, tag, usrandgroup)
                            
                            sent_message = await context.bot.send_message(chat_id=original_chat_id, text=translated_text_with_emojis, parse_mode=ParseMode.HTML, reply_to_message_id=original_message_id)
                            # Store the (chat_id, message_id) tuple mapping from source to destination
                            source_to_destination_msg_id_map[(chat_id, message.message_id, original_chat_id)] = (original_chat_id, sent_message.message_id)

                            # Store the reverse mapping as well
                            destination_to_source_msg_id_map[(original_chat_id, sent_message.message_id)] = (
                            chat_id, message.message_id)
                            
                        else:
                            original_chat_id, original_message_id = same_group_message_di_map[(
                            reply_to_message.chat_id, reply_to_message.message_id)]
                            
                            for dest_group_id, lang2 in MULTIGROUP_TRANSLATION_TARGETS.items():
                            # Exclude the group where the reply was made
                                if dest_group_id != chat_id and dest_group_id != original_chat_id:
                                    # Find the corresponding forwarded message ID in the other destination groups
                                    dest_message_id = source_to_destination_msg_id_map[(
                                        original_chat_id, original_message_id, dest_group_id)][1]
                                    translated_text_with_emojis = translate_text(text_to_translate, lang2, sender_usr, tag, usrandgroup)
                                    sent_message = await context.bot.send_message(chat_id=dest_group_id, text=translated_text_with_emojis, parse_mode=ParseMode.HTML, reply_to_message_id=dest_message_id,)

                                    # Store the (chat_id, message_id) tuple mapping from source to destination
                                    source_to_destination_msg_id_map[(chat_id, message.message_id, dest_group_id)] = (
                                    dest_group_id, sent_message.message_id)
                                    # Store the reverse mapping as well
                                    destination_to_source_msg_id_map[(dest_group_id, sent_message.message_id)] = (
                                    chat_id, message.message_id)
                else:
                    for group_id, lang in MULTIGROUP_TRANSLATION_TARGETS.items():
                        if update.effective_chat.id != group_id:
                            translated_text_with_emojis = translate_text(text_to_translate, lang, sender_usr, tag, usrandgroup)
                            sent_message = await context.bot.send_message(chat_id=group_id, text=translated_text_with_emojis, parse_mode=ParseMode.HTML)
                            # Use a tuple of (chat_id, message_id, destination_group_id) to uniquely identify each forward event
                            source_to_destination_msg_id_map[(chat_id, message.message_id, group_id)] = (group_id, sent_message.message_id)

                            # For the reverse mapping, since sent_message.message_id is already unique within the group, you can use it as it is
                            destination_to_source_msg_id_map[(group_id, sent_message.message_id)] = (chat_id, message.message_id)
                            same_group_message_di_map[(chat_id, message.message_id)] = (chat_id, message.message_id)
                        
        except TelegramError as e:
            logger.error(
            f"An error occurred while forwarding a message to group {group_id}: {e.message}")
        except Exception as e:
            tb_str = traceback.format_exc()
            logger.error(
            f"An error occurred during text translation: {type(e).__name__}, {str(e)}\nTraceback:\n{tb_str}")


async def sendphoto(update: Update, context: ContextTypes.DEFAULT_TYPE, sender_usr) -> None:
    # Translate and forward the message for each group according to its specified language
    message = update.effective_message
    chat_id = update.effective_chat.id
    tag = False
    is_admin, custom_title, spam, user_displayed_name = await adminandspam(update, context)
    if not spam:
        try:
            # Remove the hashtag for translation
            if custom_title != "" and custom_title is not None:
                usrandgroup = getflag(chat_id) + " <b>" + user_displayed_name + '('+sender_usr+')' + ' | '+custom_title+'</b>'+"\n"
            elif sender_usr is not None:
                usrandgroup = getflag(chat_id) + " <b>" + user_displayed_name + '('+sender_usr+')' + '</b>'+"\n"
            else:
                usrandgroup = getflag(chat_id) + " <b>" + user_displayed_name + '('+"hidden"+')' + '</b>'+"\n"
            await rate_limit()
        
            if message.caption is not None:
                text_to_translate = message.caption
                # Send photo with translated caption
                # Highest resolution photo
            else :
                text_to_send = usrandgroup
                
            photo_file_id = message.photo[-1].file_id
            await rate_limit()  
            
            if message.chat_id != HUDIHEART:
                group_id = HUDIHEART
                if update.message.reply_to_message is not None :
                    reply_to_message = update.message.reply_to_message
                    # For a reply in the destination group, find the original message and reply there
                    if reply_to_message and ((reply_to_message.chat_id, reply_to_message.message_id) in destination_to_source_msg_id_map or (reply_to_message.chat_id, reply_to_message.message_id) in same_group_message_di_map):

                        if (reply_to_message.chat_id, reply_to_message.message_id) in destination_to_source_msg_id_map:

                            original_chat_id, original_message_id = destination_to_source_msg_id_map[(reply_to_message.chat_id, reply_to_message.message_id)]
                            if message.caption is not None:
                                text_to_send = translate_text(text_to_translate, 'en', sender_usr, tag, usrandgroup)
                                    
                            sent_message = await context.bot.send_photo(
                                                chat_id=original_chat_id,
                                                photo=photo_file_id,
                                                caption=text_to_send,
                                                parse_mode=ParseMode.HTML,
                                                reply_to_message_id=original_message_id,
                                            )
                        else:
                            original_chat_id, original_message_id = same_group_message_di_map[(
                            reply_to_message.chat_id, reply_to_message.message_id)]
                            dest_message_id = source_to_destination_msg_id_map[(
                                original_chat_id, original_message_id, HUDIHEART)][1]
                            if message.caption is not None:
                                text_to_send = translate_text(text_to_translate, 'en', sender_usr, tag, usrandgroup)
                            else:
                                text_to_send = usrandgroup
                                
                            sent_message = await context.bot.send_photo(
                                            chat_id=HUDIHEART,
                                            photo=photo_file_id,
                                            caption=text_to_send,
                                            parse_mode=ParseMode.HTML,
                                            reply_to_message_id=dest_message_id,
                                        )
                            
                else:
                    if message.caption is not None:
                        text_to_send = translate_text(text_to_translate, 'en', sender_usr, tag, usrandgroup)                                        
                        sent_message = await context.bot.send_photo(
                                            chat_id=HUDIHEART,
                                            photo=photo_file_id,
                                            caption=text_to_send,
                                            parse_mode=ParseMode.HTML,
                                        )
                        # Use a tuple of (chat_id, message_id, destination_group_id) to uniquely identify each forward event
                        source_to_destination_msg_id_map[(chat_id, message.message_id, HUDIHEART)] = (
                            HUDIHEART, sent_message.message_id)

                        # For the reverse mapping, since sent_message.message_id is already unique within the group, you can use it as it is
                        destination_to_source_msg_id_map[(HUDIHEART, sent_message.message_id)] = (
                                chat_id, message.message_id)
                        same_group_message_di_map[(chat_id, message.message_id)] = (
                                chat_id, message.message_id)

            else: 
                if update.message.reply_to_message is not None :
                    reply_to_message = update.message.reply_to_message
                    # For a reply in the destination group, find the original message and reply there
                    if reply_to_message and ((reply_to_message.chat_id, reply_to_message.message_id) in destination_to_source_msg_id_map or (reply_to_message.chat_id, reply_to_message.message_id) in same_group_message_di_map):
                        if (reply_to_message.chat_id, reply_to_message.message_id) in destination_to_source_msg_id_map:

                            original_chat_id, original_message_id = destination_to_source_msg_id_map[(reply_to_message.chat_id, reply_to_message.message_id)]
                            if message.caption is not None:
                                text_to_send = translate_text(text_to_translate, 'en', sender_usr, tag, usrandgroup)
                                    
                            sent_message = await context.bot.send_photo(
                                                chat_id=original_chat_id,
                                                photo=photo_file_id,
                                                caption=text_to_send,
                                                parse_mode=ParseMode.HTML,
                                                reply_to_message_id=original_message_id,
                                            )
                        else:
                            original_chat_id, original_message_id = same_group_message_di_map[(
                            reply_to_message.chat_id, reply_to_message.message_id)]
                            for dest_group_id, lang2 in MULTIGROUP_TRANSLATION_TARGETS.items():
                            # Exclude the group where the reply was made
                                if dest_group_id != chat_id and dest_group_id != original_chat_id:
                                    # Find the corresponding forwarded message ID in the other destination groups
                                    dest_message_id = source_to_destination_msg_id_map[(
                                        original_chat_id, original_message_id, dest_group_id)][1]
                                    if message.caption is not None:
                                        text_to_send = translate_text(text_to_translate, lang2, sender_usr, tag, usrandgroup)
                                    else:
                                        text_to_send = usrandgroup
                                        
                                    sent_message = await context.bot.send_photo(
                                                    chat_id=dest_group_id,
                                                    photo=photo_file_id,
                                                    caption=text_to_send,
                                                    parse_mode=ParseMode.HTML,
                                                    reply_to_message_id=dest_message_id,
                                                )
                            
                else:
                    for group_id, lang in MULTIGROUP_TRANSLATION_TARGETS.items():

                        if update.effective_chat.id != group_id:

                            if message.caption is not None:
                                text_to_send = translate_text(text_to_translate, lang, sender_usr, tag, usrandgroup)
                            else:
                                text_to_send = usrandgroup
                                            
                            sent_message = await context.bot.send_photo(
                                            chat_id=group_id,
                                            photo=photo_file_id,
                                            caption=text_to_send,
                                            parse_mode=ParseMode.HTML,
                                        )
                            # Use a tuple of (chat_id, message_id, destination_group_id) to uniquely identify each forward event
                            source_to_destination_msg_id_map[(chat_id, message.message_id, group_id)] = (
                                group_id, sent_message.message_id)

                            # For the reverse mapping, since sent_message.message_id is already unique within the group, you can use it as it is
                            destination_to_source_msg_id_map[(group_id, sent_message.message_id)] = (
                                chat_id, message.message_id)
                            same_group_message_di_map[(chat_id, message.message_id)] = (
                                chat_id, message.message_id)

        except TelegramError as e:
            logger.error(
            f"An error occurred while forwarding a photo to group {group_id}: {e.message}")
        except Exception as e:
            tb_str = traceback.format_exc()
            logger.error(
            f"An error occurred during text translation: {type(e).__name__}, {str(e)}\nTraceback:\n{tb_str}")
           
            
async def sendsticker(update: Update, context: ContextTypes.DEFAULT_TYPE, sender_usr) -> None:
    message = update.effective_message
    chat_id = update.effective_chat.id
    tag = False
    is_admin, custom_title, spam, user_displayed_name = await adminandspam(update, context)

    try:
        # Remove the hashtag for translation
        if custom_title != "" and custom_title is not None:
            usrandgroup = getflag(chat_id) + " <b>" + user_displayed_name + '('+sender_usr+')' + ' | '+custom_title+'</b>'+"\n"
        elif sender_usr is not None:
            usrandgroup = getflag(chat_id) + " <b>" + user_displayed_name + '('+sender_usr+')' + '</b>'+"\n"
        else:
            usrandgroup = getflag(chat_id) + " <b>" + user_displayed_name + '('+"hidden"+')' + '</b>'+"\n"
        await rate_limit()
    
        sticker_file_id = message.sticker.file_id    
        await rate_limit()
        await rate_limit()
        
        if message.chat_id != HUDIHEART:
            group_id = HUDIHEART
            if update.message.reply_to_message is not None :
                reply_to_message = update.message.reply_to_message
                # For a reply in the destination group, find the original message and reply there
                if reply_to_message and ((reply_to_message.chat_id, reply_to_message.message_id) in destination_to_source_msg_id_map or (reply_to_message.chat_id, reply_to_message.message_id) in same_group_message_di_map):
                    
                    if (reply_to_message.chat_id, reply_to_message.message_id) in destination_to_source_msg_id_map:

                        original_chat_id, original_message_id = destination_to_source_msg_id_map[(reply_to_message.chat_id, reply_to_message.message_id)]
                        
                        await context.bot.send_message(chat_id=original_chat_id, text=usrandgroup, parse_mode=ParseMode.HTML, reply_to_message_id=original_message_id)
                        sent_message = await context.bot.send_sticker(chat_id=original_chat_id, sticker=sticker_file_id, reply_to_message_id=original_message_id)
                        # Store the (chat_id, message_id) tuple mapping from source to destination
                        source_to_destination_msg_id_map[(chat_id, message.message_id, original_chat_id)] = (original_chat_id, sent_message.message_id)

                        # Store the reverse mapping as well
                        destination_to_source_msg_id_map[(original_chat_id, sent_message.message_id)] = (
                        chat_id, message.message_id)
                    else:
                        original_chat_id, original_message_id = same_group_message_di_map[(
                        reply_to_message.chat_id, reply_to_message.message_id)]
                        dest_message_id = source_to_destination_msg_id_map[(
                            original_chat_id, original_message_id, HUDIHEART)][1]
                        await context.bot.send_message(chat_id=HUDIHEART, text=usrandgroup, parse_mode=ParseMode.HTML, reply_to_message_id=dest_message_id)
                        sent_message = await context.bot.send_sticker(chat_id=HUDIHEART, sticker=sticker_file_id, reply_to_message_id=dest_message_id,)

                        # Store the (chat_id, message_id) tuple mapping from source to destination
                        source_to_destination_msg_id_map[(chat_id, message.message_id, HUDIHEART)] = (
                        HUDIHEART, sent_message.message_id)
                        # Store the reverse mapping as well
                        destination_to_source_msg_id_map[(HUDIHEART, sent_message.message_id)] = (
                        chat_id, message.message_id)
                        
            else :
                await context.bot.send_message(chat_id=HUDIHEART, text=usrandgroup, parse_mode=ParseMode.HTML)
                sent_message = await context.bot.send_sticker(chat_id=HUDIHEART, sticker=sticker_file_id)
                # Use a tuple of (chat_id, message_id, destination_group_id) to uniquely identify each forward event
                source_to_destination_msg_id_map[(chat_id, message.message_id, HUDIHEART)] = (HUDIHEART, sent_message.message_id)

                # For the reverse mapping, since sent_message.message_id is already unique within the group, you can use it as it is
                destination_to_source_msg_id_map[(HUDIHEART, sent_message.message_id)] = (chat_id, message.message_id)
                same_group_message_di_map[(chat_id, message.message_id)] = (chat_id, message.message_id)
        else: 
            if update.message.reply_to_message is not None :
                reply_to_message = update.message.reply_to_message
                # For a reply in the destination group, find the original message and reply there
                if reply_to_message and ((reply_to_message.chat_id, reply_to_message.message_id) in destination_to_source_msg_id_map or (reply_to_message.chat_id, reply_to_message.message_id) in same_group_message_di_map):
                    
                    if (reply_to_message.chat_id, reply_to_message.message_id) in destination_to_source_msg_id_map:

                        original_chat_id, original_message_id = destination_to_source_msg_id_map[(reply_to_message.chat_id, reply_to_message.message_id)]
                        
                        await context.bot.send_message(chat_id=original_chat_id, text=usrandgroup, parse_mode=ParseMode.HTML, reply_to_message_id=original_message_id)
                        sent_message = await context.bot.send_sticker(chat_id=original_chat_id, sticker=sticker_file_id, reply_to_message_id=original_message_id)
                        # Store the (chat_id, message_id) tuple mapping from source to destination
                        source_to_destination_msg_id_map[(chat_id, message.message_id, original_chat_id)] = (original_chat_id, sent_message.message_id)

                        # Store the reverse mapping as well
                        destination_to_source_msg_id_map[(original_chat_id, sent_message.message_id)] = (
                        chat_id, message.message_id)
                        
                    else:
                        original_chat_id, original_message_id = same_group_message_di_map[(
                        reply_to_message.chat_id, reply_to_message.message_id)]
                        for dest_group_id, lang2 in MULTIGROUP_TRANSLATION_TARGETS.items():
                            # Exclude the group where the reply was made
                            if dest_group_id != chat_id and dest_group_id != original_chat_id:
                                # Find the corresponding forwarded message ID in the other destination groups
                                dest_message_id = source_to_destination_msg_id_map[(
                                    original_chat_id, original_message_id, dest_group_id)][1]
                                await context.bot.send_message(chat_id=dest_group_id, text=usrandgroup, parse_mode=ParseMode.HTML, reply_to_message_id=dest_message_id)
                                sent_message = await context.bot.send_sticker(chat_id=dest_group_id, sticker=sticker_file_id, parse_mode=ParseMode.HTML, reply_to_message_id=dest_message_id,)

                                # Store the (chat_id, message_id) tuple mapping from source to destination
                                source_to_destination_msg_id_map[(chat_id, message.message_id, dest_group_id)] = (
                                dest_group_id, sent_message.message_id)
                                # Store the reverse mapping as well
                                destination_to_source_msg_id_map[(dest_group_id, sent_message.message_id)] = (
                                chat_id, message.message_id)
                            
                        
            else:
                for group_id, lang in MULTIGROUP_TRANSLATION_TARGETS.items():
                    if update.effective_chat.id != group_id:                    
                        await context.bot.send_message(chat_id=group_id, text=usrandgroup, parse_mode=ParseMode.HTML)
                        sent_message = await context.bot.send_sticker(chat_id=group_id, sticker=sticker_file_id)
                        # Use a tuple of (chat_id, message_id, destination_group_id) to uniquely identify each forward event
                        source_to_destination_msg_id_map[(chat_id, message.message_id, group_id)] = (group_id, sent_message.message_id)

                        # For the reverse mapping, since sent_message.message_id is already unique within the group, you can use it as it is
                        destination_to_source_msg_id_map[(group_id, sent_message.message_id)] = (chat_id, message.message_id)
                        same_group_message_di_map[(chat_id, message.message_id)] = (chat_id, message.message_id)

    except TelegramError as e:
        logger.error(
        f"An error occurred while forwarding a message to group {group_id}: {e.message}")
    except Exception as e:
        tb_str = traceback.format_exc()
        logger.error(
        f"An error occurred during text translation: {type(e).__name__}, {str(e)}\nTraceback:\n{tb_str}")
        
        
async def adminandspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tag = False
    if update.message is not None:
        message = update.effective_message
        user = update.message.from_user
        user_displayed_name = user.first_name
        if user.last_name:  # If the user has a last name, append it.
            user_displayed_name += " " + user.last_name

        # Placeholder variable for admin status
        is_admin = False
        custom_title = ""
        spam = False
        try:
            # Retrieve a list of all administrators in the chat
            chat_administrators = await context.bot.get_chat_administrators(update.message.chat_id)
            # Find the admin that matches the message sender and get their custom title
            for admin in chat_administrators:
                if admin.user.id == user.id:
                    custom_title = admin.custom_title
                    is_admin = True
                    break
        except Exception as e:
            logger.error(
                f"Failed to get chat administrators or custom title: {e}")
        
        if update.message.forward_origin:
            print("forwarded")
            spam = True

        if message.entities:
            for entity in message.entities:
                if not is_admin:
                    if entity.type in ['url', 'text_link']:
                        spam = True
                    if any(SPAMWORD in message.text.lower() for SPAMWORD in SPAMWORDS):
                        spam = True
                    if entity.type == 'mention':
                        mentioned_username = message.text[entity.offset:entity.offset + entity.length]
                        if mentioned_username.lower().endswith('bot'):
                            spam = True
                        try:
                            chat = await context.bot.get_chat(mentioned_username)
                            if chat.type in ['group', 'supergroup']:
                                spam = True
                            if chat.type == 'channel':
                                spam = True

                        except Exception as e:
                            print(
                                f"Could not retrieve chat for username @{mentioned_username}: {e}")
        return is_admin, custom_title, spam, user_displayed_name


def getflag(group_id):
    return MULTIGROUP_TRANSLATION_TARGETS_FLAGS[group_id]


def getlang(group_id):
    return MULTIGROUP_TRANSLATION_TARGETS[group_id]


def translate_text(text_to_translate, target_language, usr, tag, usrandgroup):
    translator = GoogleTranslator(source='auto', target=target_language)
    if tag:
        text_to_translate += "\nMessage From "
    clean_text, emojis = extract_emojis_positions(text_to_translate)
    translated_text = translator.translate(clean_text)
    translated_text_with_emojis = insert_emojis(translated_text, emojis)
    if usr != '' and tag:
        translated_text_with_emojis += "@"+usr
    if usrandgroup != "":
        translated_text_with_emojis = usrandgroup + translated_text_with_emojis
    return translated_text_with_emojis


async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message with the current chat ID."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(f'The chat ID is {chat_id}')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text('Hi! Use the /get_chat_id command to get the ID of this chat.')


async def memetech(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    chat_id = update.effective_chat.id
    if chat_id == -1001989702999:
        await update.message.reply_text('🎨 Make MEME with DINGBOARD\nAI image editing IN YOUR BROWSER!\nhttps://dingboard.com/\n\n🎶 Make MEME SONGS with UDIO\nAI Text 2 Music\nhttps://www.udio.com/')


def extract_emojis_positions(text):
    # Find all emojis and replace every single one of them with a placeholder while saving their order
    emoji_list = emoji_pattern.findall(text)
    text_with_placeholders = emoji_pattern.sub("_42069_", text)
    return text_with_placeholders, emoji_list


def insert_emojis(translated_text, emoji_list):
    # Iterator for emojis
    emoji_iter = iter(emoji_list)

    # Helper function for replacement that raises error if no more emojis
    def replace_with_emoji(match):
        try:
            return next(emoji_iter)
        except StopIteration:
            raise ValueError("Not enough emojis to replace all placeholders")

    # Replace each placeholder with the next emoji in the list
    translated_text_with_emojis = re.sub(
        "_42069_", replace_with_emoji, translated_text)

    return translated_text_with_emojis


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(msg="Exception while handling an update:",
                 exc_info=context.error)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    user = update.message.from_user
    is_admin, custom_title, spam, user_displayed_name = await adminandspam(update, context)
    sender_usr = update.effective_user.username
    
        # Remove the hashtag for translation
    if custom_title != "" and custom_title is not None:
        usrandgroup = getflag(update.message.chat_id) + " <b>" + user_displayed_name + '('+sender_usr+')' + ' | '+custom_title+'</b>'+"\n"
    elif sender_usr is not None:
        usrandgroup = getflag(update.message.chat_id) + " <b>" + user_displayed_name + '('+sender_usr+')' + '</b>'+"\n"
    else:
        usrandgroup = getflag(update.message.chat_id) + " <b>" + user_displayed_name + '('+"hidden"+')' + '</b>'+"\n"
        
    if is_admin:
        # Check if the command is a reply to a message
        if update.message.reply_to_message:
            # Message to broadcast
            message_to_broadcast = update.message.reply_to_message.text
            
            for chat_id, lang in TRANSLATION_TARGETS.items():
                if update.message.chat_id != chat_id:
                    await context.bot.send_message(chat_id=chat_id, text=translate_text(message_to_broadcast, lang, '', False, usrandgroup), parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text('Please reply to a message you want to broadcast.')
    else: 
         await update.message.reply_text(
            "Only admins can use this command")

async def rate_limit():
    global message_timestamps
    while len(message_timestamps) >= 30 and time.time() - message_timestamps[0] < 1:
        # If there are 30 or more messages in the last second, wait
        time.sleep(time.time() - message_timestamps[0])
    # Record the timestamp of a new message being sent and prune old timestamps
    message_timestamps.append(time.time())
    while message_timestamps and time.time() - message_timestamps[0] >= 1:
        message_timestamps.popleft()

async def delete_across_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    user = update.message.from_user
    is_admin = False
    try:
        # Retrieve a list of all administrators in the chat
        chat_administrators = await context.bot.get_chat_administrators(update.message.chat_id)
        # Find the admin that matches the message sender and get their custom title
        for admin in chat_administrators:
            if admin.user.id == user.id:
                is_admin = True
                break
    except Exception as e:
        update.message.reply_text(
            "Only admins can use this command")
        return
    
    try:
        if admin:
            chat_id = update.effective_chat.id
            message = update.message.reply_to_message

            if (message.chat_id, message.message_id) in same_group_message_di_map:
                # This is the original message, delete it
                await context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)

            
            if message and ((message.chat_id, message.message_id) in destination_to_source_msg_id_map or (message.chat_id, message.message_id) in same_group_message_di_map):

                if (message.chat_id, message.message_id) in destination_to_source_msg_id_map:
                    # Get the original message to delete
                    original_chat_id, original_message_id = destination_to_source_msg_id_map[(message.chat_id, message.message_id)]
                    
                    #await context.bot.delete_message(chat_id=message.chat_id, message_id=message.message_id)
                    # Delete the original message
                    await context.bot.delete_message(chat_id=original_chat_id, message_id=original_message_id)

                else:
                # Handling messages within the same group (implementation will depend on your logic)
                    original_chat_id, original_message_id = same_group_message_di_map[(message.chat_id, message.message_id)]

                # Delete the corresponding messages in other groups
                for dest_group_id, _ in MULTIGROUP_TRANSLATION_TARGETS.items():
                    # Exclude the group where the reply was made
                    if dest_group_id != chat_id and dest_group_id != original_chat_id:
                        _, dest_message_id = source_to_destination_msg_id_map.get((original_chat_id, original_message_id, dest_group_id), (None, None))
                        if dest_message_id:
                            await context.bot.delete_message(chat_id=dest_group_id, message_id=dest_message_id)

            elif message:
                for group_id, _ in MULTIGROUP_TRANSLATION_TARGETS.items():
                    if chat_id != group_id:
                        # Delete the message in the group
                        _, dest_message_id = source_to_destination_msg_id_map.get((chat_id, message.message_id, group_id), (None, None))
                        if dest_message_id:
                            await context.bot.delete_message(chat_id=group_id, message_id=dest_message_id)

                        # If the message exists in the same_group_message_di_map, delete it as well
                        same_group_msg = same_group_message_di_map.get((chat_id, message.message_id), (None, None))
                        if same_group_msg:
                            await context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
        else:
             update.message.reply_text(
            "Only admins can use this command")
    except TelegramError as e:
        logger.error(
        f"An error occurred while deleting a message: {e.message}")
    except Exception as e:
        tb_str = traceback.format_exc()
        logger.error(
        f"An error occurred during message deletion: {type(e).__name__}, {str(e)}\nTraceback:\n{tb_str}")



def main() -> None:
    """Start the bot with improved error handling."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # On different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("memetech", memetech))
    application.add_handler(CommandHandler("get_chat_id", get_chat_id))
    application.add_handler(CommandHandler('delete', delete_across_groups, filters.REPLY))
    application.add_handler(CommandHandler('broadcast', broadcast))

    # On non-command message
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.ChatType.CHANNEL | filters.PHOTO | filters.UpdateType.EDITED_MESSAGE |
                            filters.Entity('URL') | filters.Entity('TEXT_LINK') | filters.Entity('MENTION') | filters.REPLY | filters.Sticker.ALL, message_handler))
    # Log all errors
    application.add_error_handler(error_handler)

    while True:
        try:
            # Run the bot until the user presses Ctrl-C
            application.run_polling()
        except Exception as e:
            logger.error(f"An unhandled error occurred: {e}", exc_info=True)
            # Optional: Sleep for a while before restarting to avoid excessive retries
            time.sleep(5)


if __name__ == '__main__':
    main()
