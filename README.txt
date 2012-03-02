PyInvEdit is an alternative to the venerable InvEdit for Minecraft

This is still a work in progress.

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
