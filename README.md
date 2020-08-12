# fosmbot

**This Bot manages the [federation](https://wiki.openstreetmap.org/wiki/List_of_OSM_centric_Telegram_accounts/anti-spam_initiative) of the OpenStreetMap Community on Telegram.**

## Quick start for those who don't read the docs

add the bot to your group, make it admin, start a chat with the bot.

Type `/start` or `/help` in the [chat with the bot](https.//t.me/fosmbot) to view a list of available commands

## Motivation

Some OSM groups started experimenting with the Rose bot, to keep scamming under control.  Unfortunately, Rose had a **very** sexist avatar, per default that automatic person intervenes in all first contacts, and that was reason for various groups to refuse Rose.  Other reasons were that Rose, however well programmed, seemed to be attracting even more scammers.  Finally, Rose is closed-source, and some admins were uncomfortable with that, too.  But all things considered, Rose was being helpful, so people thought why not an OSM-compliant scammer/spammer control?

## How does it compare to Rose?

* The "OSM Federation Bot" (this bot) does only focus on the federation and not the other features Rose has.
* A Rose federation is associated to a single user, this bot does not give any user so much special rights.
* Welcome and good bye messages are missing here. 
* This bot makes it obvious that it is a machine. 
* It does not distract group conversations. It is more silent and prefers to work in the background rather then in the foreground.
* It allows also the fbanlist to be viewed by fedadmins and above.

Along with other features:

* Banned users can chat with the bot in private and request the reason behind their ban.
* Users can view the data the bot stores about them with the /mydata command in private.
* It allows to view the groups using this bot and which are also authorized to use it.
* It provides a simpler interface than Rose and behaves more than we would expect.
* It allows us to add more fedadmins then Rose does.
* It allows me to elect a new federation owner if I don't want to manage it anymore.
* It allows us to search users by display name if we don't manage to get their username or telegram id which allows us to get rid of userinfobot (works only if our bot knows the user in question already)
* More fine tweaks of command execution rights

## Further information

Ping [@valornaram](https://t.me/valornaram) for questions or to ask him to unlock the Bot for your group. The Bot only works for explicityl unlocked groups.
