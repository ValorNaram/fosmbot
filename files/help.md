**OSM Federation Bot - Help**

**General**
`/help` or `/start`
  - View this help
  - private chat only
`/mydata`
  - Returns the data we have about you saved in our database
  - private chat only
`/testme`
  - Returns a text
`/privacypolicy`
  - Returns a notice about how we collect data.

**Me -  private chat only commands**
`/demoteme`
  - Demote yourself to a user (level __user__). You loose your federation rights.
  - at least level __fedadmin__ required. Users with level __owner__ cannot execute that command
`/mydata`
  - Returns data about yourself
`/mylevel`
  - Returns your access level
`/myid`
  - Returns your internal telegram id
`/viewbanreason`
  - View the reason why you were banned inclusive another data we have about you

**Groups**
`/addgroup`
  - Add the group this command has been sent from to the federation "osmallgroups"
  - level __superadmin__ or higher required
`/removegroup`
  - Remove the group this command has been sent from from the federation "osmallgroups"
  - level __superadmin__ or higher required
`/groupid`
  - Returns the group's internal telegram id
`/viewgroups`
  - Returns a list of participating groups
  - at least level __fedadmin__ required
  - private chat only
`/groupauthorized`
  - Returns if a group is authorized. If it does not return anything, then the bot isn't active in the group you typed that command in.

**Users**
`/changecomment <username or id> <comment>`
  - Changes the comment about a user we have in our database
  - at least level __fedadmin__ required
  - to substitute `<username or id>`, just reply a message written by a user you want to unban with that command
`/changelevel <username or id> <level>`
  - Set the user's level to `<level>`
  - at least __superadmin__ required
  - to substitute `<username or id>`, just reply a message written by a user you want to unban with that command
`/search <display name>`
  - Prints out all users (telegram id inclusive) this Bot knows and having the specified display name
  - at least level __fedadmin__ required
  - private chat only
`/userid`
  - Prints the id of the user of the replied to message and or the id from the original sender in case the replied to is a forwarded one.
  - at least level __fedadmin__ required
`/owners`
  - Returns a list of users being owners (ideally only one because the current implementation does not allow having multiple owners)
  - at least level __user__ required
  - private chat only
`/fedadmins`
  - Returns a list of users being fedadmins
  - at least level __user__ required
  - private chat only
`/superadmins`
  - Returns a list of users being fedadmins
  - at least level __user__ required
  - private chat only
`/userstat <username or id>`
  - Returns data about a known user (from all levels)
  - at least level __fedadmin__ required
  - all chats
`/mystat`
  - Same as `/userstat` but returns data about the user who issued that command
`/removerecord <username or id>`
  - Removes the record of a particular user
  - level __owner__ required
  - **not possible:** to substitute `<username or id>`
  - private chat only
`/addrecord <username or id> <user id>`
  - Same as `/removerecord` but let's the owner create a user record by hand
`/userid`
  - Prints the id from the original sender of a message (forwarded messages only) and or the id of the actual sender
  - reply to the message you want the (original) sender's id for

**Federation**
`/funban <username or id>`
  - Unban a previously banned user
  - at least level __fedadmin__ required
  - to substitute `<username or id>`, just reply a message written by a user you want to unban with that command
`/fban <username or id> <comment>`
  - Ban a user with a reason (=comment)
  - at least level __fedadmin__ required
  - to substitute `<username or id>`, just reply a message written by a user you want to unban with that command
`/newowner <username or id>`
  - Transfer Ownership to another user. The previous owner gets demoted to the level __user__
  - level __owner__ required
  - **not possible** to substitute `<username or id>`
`/fbanlist`
  - Returns a csv document containing all banned users.
  - at least level __fedadmin__


It's all FOSS --> https://github.com/valornaram/fosmbot
