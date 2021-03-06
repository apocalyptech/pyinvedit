PyInvEdit is an alternative to the venerable InvEdit for Minecraft

This is a work in progress, but it's basically feature-complete right
now.  Use at your own risk, though I haven't personally experienced
any data loss with it.

A pre-emptive I-assume-to-be FAQ:

    "Why should I use this over InvEdit?"

Well, probably there's little reason to, unless you're on Linux and want
something more nativey than running a .NET app through Mono (which is what
InvEdit does).  I started working on this back when InvEdit would destroy
Enchantment data, and I had wanted an inventory editor which kept that
data intact (or even allowed me to edit it).  At the time, official InvEdit
development appeared to be dead (the forum post said that it was unlikely
to be updated) and nobody on GitHub had addressed that issue yet.  Not
wanting to learn .NET, I figured I'd just write a replacement in Python.
Cue one weekend-with-not-much-better-to-do-than-program later, and I come
back home to discover that InvEdit's been updated with a test version
which not only keeps Enchantments intact but lets you edit them.

So, a bit of work for not a whole lot of gain!  Still, the app was
functional enough by that point that it seemed like a waste to just abandon
it, and I always have fun tinkering around with Python, so I'm still
intending to finish it up and push out an official release eventually.

Differences between PyInvEdit and InvEdit
-----------------------------------------

New/different features:

    1) Blocks/Items are defined in a YAML file, rather than a flat text
       file.  IMO this provides for much better flexibility.

    2) The app is careful not to lose any unknown NBT data.  If there is
       ever another addition like Enchantments, the goal is to write the
       app in such a way that no data is lost, even if we don't understand
       the extra data explicitly.

    3) Right-click to repair or fill-to-max-quantity

    4) "Repair All" / "Fill All" / "Enchant All" functions

    5) Alteration of health, food, XP, game mode, time-of-day, etc.

    6) "Import" of inventory from another savefile

Features from InvEdit that are not present in PyInvEdit:

    1) Multiple inventories open at once

    2) No "new inventory" function

    3) No auto-updating
