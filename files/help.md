**OSM Federation Bot - Help**

`/help` or `/start`
  - View this help
  - all levels
  - private chat only
`/mydata`
  - Returns the data we have about you saved in our database
  - all levels
  - private chat only
`/testme`
  - Returns a text
  - all levels
  - all chats
`/privacypolicy`
  - Returns a notice about how we collect data.
  - all levels
  - all chats
`/changecomment <username or id> <comment>`
  - Changes the comment about a user we have in our database
  - level __fedadmin__ or higher required
  - all chats
`/changelevel <username or id> <level>`
  - Set the user's level to __level__
  - level __superadmin__ or higher required
  - all levels
`/demoteme`
  - Demote yourself to a user (level __user__). You loose your federation rights.
  - level __fedadmin__ or higher required
  - private chat only
`/funban <username or id>`
  - Unban a previously banned user
  - level __fedadmin__ or higher required
  - all chats
  - to substitute `<username or id>`, just reply a message written by a user you want to unban with that command
`/fban <username or id> <comment>`
  - Ban a user with a reason (=comment)
  - level __fedadmin__ or higher required
  - all chats
  - to substitute `<username or id>`, just reply a message written by a user you want to unban with that command
`/newowner <username or id>`
  - Transfer Ownership to another user. The new user then can do everything the previous owner could do. The previous owner gets demoted to the level __owner__
  - level __owner__ required
  - all chats
  - **NOT POSSIBLE:** to substitute `<username or id>`, just reply a message written by a user you want to unban with that command
`/addgroup`
  - Add the group this command has been sent from to the federation "osmallgroups"
  - level __superadmin__ or higher required
  - only groups
`/removegroup`
  - Remove the group this command has been sent from from the federation "osmallgroups"
  - level __superadmin__ or higher required
  - only groups
`/search <display name>`
  - Prints out all users (telegram id inclusive) this Bot knows and having the specified display name
  - level __fedadmin__ or higher required
  - private chat only
`/owners`
  - Returns a list of users being owners (ideally only one because the current implementation does not allow having multiple owners)
  - level __user__ or higher required. The level __user__ is the default level each user known to the federation gets.
  - private chat only
`/fedadmins`
  - Returns a list of users being fedadmins
  - level __user__ or higher required. The level __user__ is the default level each user known to the federation gets.
  - private chat only
`/superadmins`
  - Returns a list of users being fedadmins
  - level __user__ or higher required. The level __user__ is the default level each user known to the federation gets.
  - private chat only
`/fbanlist`
  - Returns a csv document containing all banned users.
  - level __fedadmin__ or higher required
  - all chats
`/userstat <username or id>`
  - Returns data about a known user (from all levels)
  - level __fedadmin__ or higher required
  - all chats
`/mystat`
  - Returns data about yourself
  - all levels
  - private chat only
`/mylevel`
  - Returns your access level
  - all levels
  - private chat only
`/groupid`
  - Returns the group's internal telegram id
  - all levels
  - useful only in (super)groups and channels
`/myid`
  - Returns your internal telegram id
  - all levels
  - private chat only
`/viewgroups`
  - Returns a list of participating groups
  - level __fedadmin__ or higher required.
  - private chat only
`/groupauthorized`
  - Returns if a group is authorized. If it does not return anything, then the bot isn't active in the group you typed that command in.
  - all levels
  - all chats but useful in groups only
`/removeuser <username or id>`
  - Removes the data of a particular user
  - level __owner__ required
  - **NOT POSSIBLE:** to substitute `<username or id>`, just reply a message written by a user you want to unban with that command
  - private chat only
`/viewbanreason`
  - View the reason why you were banned inclusive another data we have about you
  - makes only sense when you has been banned
  - private chat only
