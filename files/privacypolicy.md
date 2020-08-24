**OSM Federation Bot - Privacy Policy**

`/help`
  - view the help text (not this one)
`/privacypolicy`
  - view this text

**Definitions**
Bot
  - a program you can chat with (in Telegram) which executes a pre-defined set of commands as the user wants. A bot usually automates some things and helps human to concentrate on other buisness.
Our group(s)
  - The ones prefixed/suffixed with "OSM" or "OpenStreetMap", "HOT" and "Humanitarian OpenStreetMap" in their name. But exceptions exists.
We
  - The OpenStreetMap Community developing and utilizing the Bot
Interactions (with our groups):
  - Interactions are joins, sending messages, leaves and sending media. In this case you are a member of one or more of our groups.
Authorized groups:
  - Groups which are allowed to use that Bot. A group having the Bot does not necessary mean that that group is an authorized one. To check if a group is authorized, just issue `/authorizegroup` in a group the Bot is in.
in private
  - chat with this bot or more general "a chat with a single account/bot"


**General**
Bot owner: @valornaram

This Bot exists to keep spammers away from our groups. For that the bot collects some data about each member in our group:
  - Your telegram internal id
  - Your username
  - Your first- & last name
  - Your access level (will mostly be 'user')
  - A comment about you issued by one of the admins (should be empty usually)
  - The telegram internal id of the issuer of the comment (should be 'NULL' usually). You cannot view that information
  - a list of groups you and the bot are in
  - Timestamp (When was your record added to the database)

To view the data the Bot has saved about you, just issue `/mydata` in a private chat with the bot.

**When will this data be collected?**
The bot creates a record in our database (see "General" section) if you join one of our groups. If you chat with the bot in private and aren't in any of our groups, then the bot won't save anything about you but creates as pseudo profile which is deleted immediately after command execution.

If you are in the bot records, then the bot will create also a record for users from which you forwarded messages (if the user's profile is not hidden)

**When will this data be updated?**
Only if you are in the records already: The bot updates the record everytime you interact with the groups this bot is in or interact with the bot in private. If you chat with the bot in private and the bot already created a record for you because you were/are in one of our groups, then it also updates your record.

**When will this data be deleted? (Deletion rules)**
In order to protect our groups you cannot force us to delete your data because we need that data we collect in order to be able to ban you just in case you are spamming. But you can message @valornaram so he can look if your data is still needed or not and can safely deleted. However we keep records for
- 12 months for banned users (you can find out if you were banned by executing `/mylevel` in the private chat with this bot)
- 2 months for (regular) users (you can find out if you are a (regular) user by executing `/mylevel` in the private chat with this bot)
and then delete them as they would have never existed. But the bot will always recreate it when you start to interact with our groups again.

If you were promoted to one of our admin levels your record won't get deleted. We keep data from promoted ones because otherwise they couldn't execute their power. However if promoted users get demoted and become __user__ again, then the deletion rule applies again.

**How can I view the data being collected about me?**
Just start a private chat with our bot and issue `/mydata` to view them.
